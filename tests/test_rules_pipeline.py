import unittest

from config.settings import Settings
from core.timer import IngestionTimer
from ingestion.pipelines.rules_pipeline import RulesIngestionPipeline
from ingestion.readers.rule_reader import TextRuleReader


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


class MockRuleReader(TextRuleReader):
    def __init__(self):
        super().__init__("dummy_path")

    def stream_records(self):
        yield {
            "rule_id": "100.1a",
            "chapter": "1. Game Concepts",
            "section": "100. General",
            "text": "100.1a Two players are required.",
            "hierarchy_path": "1. Game Concepts > 100. General > 100.1a",
        }


class TestRulesIngestionPipeline(unittest.TestCase):
    """Unit tests for RulesIngestionPipeline."""

    def test_pipeline_run(self) -> None:
        vector_store = MockVectorStore()
        embedding_service = MockEmbeddingService()
        timer = IngestionTimer()
        settings = Settings()
        reader = MockRuleReader()

        pipeline = RulesIngestionPipeline(
            vector_store=vector_store,
            embedding_service=embedding_service,
            timer=timer,
            settings=settings,
            rule_reader=reader,
        )

        pipeline.run(batch_size=10, force_recreate=False)

        self.assertTrue(vector_store.initialized)
        self.assertIn(True, vector_store.bulk_modes)
        self.assertIn(False, vector_store.bulk_modes)
        self.assertEqual(len(vector_store.upserted_batches), 1)

        ids, vectors, payloads = vector_store.upserted_batches[0]
        self.assertEqual(len(ids), 1)
        self.assertEqual(payloads[0]["rule_id"], "100.1a")
        self.assertEqual(len(vectors[0]), 3)


if __name__ == "__main__":
    unittest.main()
