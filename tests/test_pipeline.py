import os
import tempfile
import unittest
from typing import Any, Dict, List, Optional, Set
from unittest.mock import MagicMock, patch

from config.settings import Settings
from core.timer import IngestionTimer
from embeddings.base import BaseEmbeddingService
from ingestion.pipeline import IngestionPipeline
from vectorstores.base import BaseVectorStore


class MockVectorStore(BaseVectorStore):
    def __init__(self, existing_ids: Optional[Set[str]] = None) -> None:
        self.existing_ids = existing_ids or set()
        self.upserted_points: List[tuple] = []
        self.bulk_mode_calls: List[bool] = []
        self.schema_initialized = False

    def initialize_schema(self) -> None:
        self.schema_initialized = True

    def upsert_batch(self, ids: List[str], vectors: List[List[float]], payloads: List[Dict[str, Any]]) -> None:
        self.upserted_points.append((ids, vectors, payloads))
        for cid in ids:
            self.existing_ids.add(cid)

    def search(
        self,
        query_vector: List[float],
        limit: int = 10,
        filters: Optional[Any] = None,
        candidate_ids: Optional[List[str]] = None
    ) -> List[Any]:
        return []

    def get_existing_ids(self) -> Set[str]:
        return self.existing_ids

    def set_bulk_mode(self, enabled: bool) -> None:
        self.bulk_mode_calls.append(enabled)


class MockEmbeddingService(BaseEmbeddingService):
    @property
    def dimension(self) -> int:
        return 4

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [[0.1, 0.2, 0.3, 0.4] for _ in texts]

    def embed_query(self, query: str) -> List[float]:
        return [0.1, 0.2, 0.3, 0.4]


class TestIngestionPipeline(unittest.TestCase):
    """Unit and integration tests for IngestionPipeline."""

    def setUp(self) -> None:
        self.temp_file = tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8")
        self.temp_file.write('{"id": "card_1", "name": "Lightning Bolt", "mana_cost": "{R}", "type_line": "Instant", "oracle_text": "Deal 3 damage."}\n')
        self.temp_file.write('{"id": "card_2", "name": "Ancestral Recall", "mana_cost": "{U}", "type_line": "Instant", "oracle_text": "Draw 3 cards."}\n')
        self.temp_file.close()

    def tearDown(self) -> None:
        if os.path.exists(self.temp_file.name):
            os.unlink(self.temp_file.name)

    @patch("ingestion.pipeline.QdrantServiceManager")
    def test_pipeline_run_success(self, mock_service_manager_cls: MagicMock) -> None:
        mock_manager = mock_service_manager_cls.return_value
        mock_manager.ensure_running.return_value = None

        vector_store = MockVectorStore(existing_ids=set())
        embedding_service = MockEmbeddingService()
        timer = IngestionTimer()
        settings = Settings()
        settings.embedding_batch_size = 2
        settings.upsert_batch_size = 2

        pipeline = IngestionPipeline(
            vector_store=vector_store,
            embedding_service=embedding_service,
            timer=timer,
            settings=settings,
        )

        pipeline.run(self.temp_file.name)

        self.assertEqual(vector_store.bulk_mode_calls, [True, False])
        self.assertTrue(len(vector_store.upserted_points) > 0)
        self.assertIn("card_1", vector_store.existing_ids)
        self.assertIn("card_2", vector_store.existing_ids)

    @patch("ingestion.pipeline.QdrantServiceManager")
    def test_pipeline_resume_skips_existing(self, mock_service_manager_cls: MagicMock) -> None:
        mock_manager = mock_service_manager_cls.return_value
        mock_manager.ensure_running.return_value = None

        vector_store = MockVectorStore(existing_ids={"card_1"})
        embedding_service = MockEmbeddingService()
        timer = IngestionTimer()
        settings = Settings()

        pipeline = IngestionPipeline(
            vector_store=vector_store,
            embedding_service=embedding_service,
            timer=timer,
            settings=settings,
        )

        pipeline.run(self.temp_file.name)

        all_upserted_ids = []
        for batch_ids, _, _ in vector_store.upserted_points:
            all_upserted_ids.extend(batch_ids)

        self.assertNotIn("card_1", all_upserted_ids)
        self.assertIn("card_2", all_upserted_ids)


if __name__ == "__main__":
    unittest.main()
