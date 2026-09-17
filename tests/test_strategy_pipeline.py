import unittest
from typing import Any, Dict, Iterator

from config.settings import Settings
from core.timer import IngestionTimer
from ingestion.chunking import RecursiveTextChunker, format_chunk_for_embedding
from ingestion.pipelines.strategy_pipeline import StrategyIngestionPipeline
from ingestion.readers.markdown_reader import MarkdownArticleReader


class MockEmbeddingService:
    def embed_documents(self, texts):
        return [[0.1, 0.2, 0.3] for _ in texts]


class MockVectorStore:
    def __init__(self):
        self.initialized = False
        self.bulk_modes = []
        self.upserted_batches = []

    def initialize_schema(self, collection_name=None):
        self.initialized = True

    def get_existing_ids(self, collection_name=None):
        return set()

    def set_bulk_mode(self, enabled: bool, collection_name=None):
        self.bulk_modes.append(enabled)

    def upsert_batch(self, ids, vectors, payloads, collection_name=None):
        self.upserted_batches.append((ids, vectors, payloads))


class MockMarkdownReader(MarkdownArticleReader):
    def __init__(self):
        super().__init__("dummy_path")

    def stream_records(self) -> Iterator[Dict[str, Any]]:
        yield {
            "article_id": "strategy_01",
            "title": "Advanced Mana Curve Theory",
            "author": "Frank Karsten",
            "source": "ChannelFireball",
            "published_at": "2020-05-12",
            "evergreen": True,
            "tags": ["mana", "theory"],
            "content": "Paragraph one discussing land counts.\n\nParagraph two discussing curve probabilities.",
        }


class TestStrategyPipelineAndChunking(unittest.TestCase):
    """Unit and integration tests for chunking, provenance formatting, and StrategyIngestionPipeline."""

    def test_recursive_chunker(self) -> None:
        chunker = RecursiveTextChunker(target_chunk_size=50, overlap=10)
        text = "This is paragraph one of the strategy guide.\n\nThis is paragraph two which is somewhat longer and discusses advanced probabilities."
        chunks = chunker.chunk_text(text)
        self.assertGreater(len(chunks), 0)
        for c in chunks:
            self.assertTrue(isinstance(c, str))
            self.assertGreater(len(c), 0)

    def test_format_chunk_for_embedding(self) -> None:
        article = {
            "source": "ChannelFireball",
            "title": "Mana Curve",
            "author": "Frank Karsten",
            "evergreen": True,
        }
        formatted = format_chunk_for_embedding(article, "Chunk text here.", 0)
        self.assertIn("Source: ChannelFireball", formatted)
        self.assertIn("Title: Mana Curve", formatted)
        self.assertIn("Author: Frank Karsten", formatted)
        self.assertIn("Evergreen: True", formatted)
        self.assertIn("Section Part 1", formatted)
        self.assertIn("Chunk text here.", formatted)

    def test_strategy_ingestion_pipeline(self) -> None:
        vector_store = MockVectorStore()
        embedding_service = MockEmbeddingService()
        timer = IngestionTimer()
        settings = Settings()
        reader = MockMarkdownReader()
        chunker = RecursiveTextChunker(target_chunk_size=100, overlap=10)

        pipeline = StrategyIngestionPipeline(
            vector_store=vector_store,
            embedding_service=embedding_service,
            timer=timer,
            settings=settings,
            markdown_reader=reader,
            chunker=chunker,
        )

        pipeline.run(batch_size=10, force_recreate=False)

        self.assertTrue(vector_store.initialized)
        self.assertIn(True, vector_store.bulk_modes)
        self.assertIn(False, vector_store.bulk_modes)
        self.assertGreater(len(vector_store.upserted_batches), 0)

        ids, vectors, payloads = vector_store.upserted_batches[0]
        self.assertGreater(len(ids), 0)
        self.assertEqual(payloads[0]["article_id"], "strategy_01")
        self.assertEqual(payloads[0]["title"], "Advanced Mana Curve Theory")
        self.assertEqual(len(vectors[0]), 3)


if __name__ == "__main__":
    unittest.main()
