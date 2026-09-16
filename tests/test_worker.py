import queue
import time
import unittest
from typing import Any, Dict, List, Optional, Set
from unittest.mock import MagicMock

from qdrant_client.http import models
from ingestion.worker import IngestionWorker
from vectorstores.base import BaseVectorStore


class MockVectorStore(BaseVectorStore):
    """Mock vector store for testing IngestionWorker."""

    def __init__(self) -> None:
        self.upserted_batches: List[tuple] = []
        self.schema_initialized = False
        self.bulk_mode = False

    def initialize_schema(self) -> None:
        self.schema_initialized = True

    def upsert_batch(self, ids: List[str], vectors: List[List[float]], payloads: List[Dict[str, Any]]) -> None:
        self.upserted_batches.append((ids, vectors, payloads))

    def search(
        self,
        query_vector: List[float],
        limit: int = 10,
        filters: Optional[Any] = None,
        candidate_ids: Optional[List[str]] = None
    ) -> List[Any]:
        return []

    def get_existing_ids(self) -> Set[str]:
        return set()

    def set_bulk_mode(self, enabled: bool) -> None:
        self.bulk_mode = enabled


class TestIngestionWorker(unittest.TestCase):
    """Unit tests for IngestionWorker."""

    def test_worker_batching_and_sentinel(self) -> None:
        q: queue.Queue = queue.Queue()
        mock_store = MockVectorStore()
        batch_size = 3

        worker = IngestionWorker(q=q, vector_store=mock_store, batch_size=batch_size)
        worker.start()

        # Enqueue 5 points (as PointStructs)
        points = [
            models.PointStruct(id=f"id_{i}", vector=[float(i)] * 4, payload={"name": f"Card {i}"})
            for i in range(5)
        ]

        for p in points:
            q.put(p)

        # Enqueue sentinel
        q.put(None)

        # Wait for queue to drain / worker to finish
        q.join()
        worker.join(timeout=5.0)

        self.assertFalse(worker.is_alive())
        # Total 5 points with batch_size=3 should result in 2 batches (3 points and 2 points)
        self.assertEqual(len(mock_store.upserted_batches), 2)
        
        batch1_ids, batch1_vectors, batch1_payloads = mock_store.upserted_batches[0]
        self.assertEqual(len(batch1_ids), 3)
        self.assertEqual(batch1_ids, ["id_0", "id_1", "id_2"])

        batch2_ids, batch2_vectors, batch2_payloads = mock_store.upserted_batches[1]
        self.assertEqual(len(batch2_ids), 2)
        self.assertEqual(batch2_ids, ["id_3", "id_4"])


if __name__ == "__main__":
    unittest.main()
