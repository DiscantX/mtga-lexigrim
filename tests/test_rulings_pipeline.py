import os
import tempfile
import unittest
from typing import Any, Dict, List, Optional, Set

from config.settings import Settings
from core.timer import IngestionTimer
from embeddings.text_extractors import extract_clean_payload
from ingestion.pipeline import load_rulings_index, IngestionPipeline
from ingestion.pipelines.rulings_pipeline import RulingsIngestionPipeline
from vectorstores.base import BaseVectorStore


class MockVectorStore(BaseVectorStore):
    def __init__(self, existing_ids: Optional[Set[str]] = None) -> None:
        self.existing_ids = existing_ids or set()
        self.upserted_points: List[tuple] = []
        self.bulk_mode_calls: List[bool] = []
        self.schema_initialized = False

    def initialize_schema(self, collection_name: Optional[str] = None) -> None:
        self.schema_initialized = True

    def upsert_batch(self, ids: List[str], vectors: List[List[float]], payloads: List[Dict[str, Any]], collection_name: Optional[str] = None) -> None:
        self.upserted_points.append((ids, vectors, payloads, collection_name))
        for cid in ids:
            self.existing_ids.add(cid)

    def search(
        self,
        query_vector: List[float],
        limit: int = 10,
        filters: Optional[Any] = None,
        candidate_ids: Optional[List[str]] = None,
        collection_name: Optional[str] = None
    ) -> List[Any]:
        return []

    def get_existing_ids(self, collection_name: Optional[str] = None) -> Set[str]:
        return self.existing_ids

    def set_bulk_mode(self, enabled: bool, collection_name: Optional[str] = None) -> None:
        self.bulk_mode_calls.append(enabled)


class MockEmbeddingService:
    @property
    def dimension(self) -> int:
        return 4

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [[0.1, 0.2, 0.3, 0.4] for _ in texts]

    def embed_query(self, query: str) -> List[float]:
        return [0.1, 0.2, 0.3, 0.4]


class TestRulingsPipelineAndPreJoin(unittest.TestCase):
    """Unit and integration tests for rulings loading, payload pre-join, and RulingsIngestionPipeline."""

    def setUp(self) -> None:
        self.rulings_file = tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8")
        self.rulings_file.write('{"object": "ruling", "oracle_id": "oracle_123", "source": "wotc", "published_at": "2020-01-01", "comment": "Ruling text one."}\n')
        self.rulings_file.write('{"object": "ruling", "oracle_id": "oracle_123", "source": "wotc", "published_at": "2021-01-01", "comment": "Ruling text two."}\n')
        self.rulings_file.write('{"object": "ruling", "oracle_id": "oracle_456", "source": "wotc", "published_at": "2022-01-01", "comment": "Another ruling."}\n')
        self.rulings_file.close()

        self.cards_file = tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8")
        self.cards_file.write('{"id": "card_1", "oracle_id": "oracle_123", "name": "Lightning Bolt", "mana_cost": "{R}", "type_line": "Instant", "oracle_text": "Deal 3 damage."}\n')
        self.cards_file.close()

    def tearDown(self) -> None:
        if os.path.exists(self.rulings_file.name):
            os.unlink(self.rulings_file.name)
        if os.path.exists(self.cards_file.name):
            os.unlink(self.cards_file.name)

    def test_load_rulings_index(self) -> None:
        rulings_index = load_rulings_index(self.rulings_file.name)
        self.assertIn("oracle_123", rulings_index)
        self.assertIn("oracle_456", rulings_index)
        self.assertEqual(len(rulings_index["oracle_123"]), 2)
        self.assertEqual(rulings_index["oracle_123"][0]["comment"], "Ruling text one.")
        self.assertEqual(len(rulings_index["oracle_456"]), 1)

    def test_extract_clean_payload_with_rulings(self) -> None:
        card_obj = {
            "id": "card_1",
            "oracle_id": "oracle_123",
            "name": "Lightning Bolt",
        }
        rulings = [{"comment": "Test ruling", "source": "wotc", "published_at": "2020-01-01"}]
        payload = extract_clean_payload(card_obj, rulings=rulings)
        self.assertEqual(payload["id"], "card_1")
        self.assertEqual(payload["rulings"], rulings)

    def test_ingestion_pipeline_with_rulings_pre_join(self) -> None:
        vector_store = MockVectorStore()
        embedding_service = MockEmbeddingService()
        timer = IngestionTimer()
        settings = Settings()

        pipeline = IngestionPipeline(
            vector_store=vector_store,
            embedding_service=embedding_service,
            timer=timer,
            settings=settings,
            rulings_file_path=self.rulings_file.name,
        )

        pipeline.run(self.cards_file.name)

        self.assertTrue(len(vector_store.upserted_points) > 0)
        _, _, payloads, _ = vector_store.upserted_points[0]
        self.assertEqual(len(payloads), 1)
        self.assertEqual(len(payloads[0]["rulings"]), 2)
        self.assertEqual(payloads[0]["rulings"][0]["comment"], "Ruling text one.")

    def test_rulings_ingestion_pipeline(self) -> None:
        vector_store = MockVectorStore()
        embedding_service = MockEmbeddingService()
        timer = IngestionTimer()
        settings = Settings()

        pipeline = RulingsIngestionPipeline(
            vector_store=vector_store,
            embedding_service=embedding_service,
            timer=timer,
            settings=settings,
        )

        pipeline.run(self.rulings_file.name, batch_size=2, force_recreate=True)

        self.assertTrue(vector_store.schema_initialized)
        self.assertIn(True, vector_store.bulk_mode_calls)
        self.assertIn(False, vector_store.bulk_mode_calls)
        self.assertTrue(len(vector_store.upserted_points) > 0)

        # Check total upserted rulings across batches
        total_upserted_rulings = 0
        for ids, vectors, payloads, col_name in vector_store.upserted_points:
            self.assertEqual(col_name, settings.qdrant_collection_rulings)
            total_upserted_rulings += len(ids)
            self.assertEqual(len(ids), len(vectors))
            self.assertEqual(len(ids), len(payloads))

        self.assertEqual(total_upserted_rulings, 3)


if __name__ == "__main__":
    unittest.main()
