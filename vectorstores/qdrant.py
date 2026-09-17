import time
import logging
from typing import Any, Dict, List, Optional, Set
from qdrant_client import QdrantClient
from qdrant_client.http import models
from config.settings import settings
from vectorstores.base import BaseVectorStore

logger = logging.getLogger(__name__)

class QdrantVectorStore(BaseVectorStore):
    """Qdrant-backed vector store implementing BaseVectorStore."""

    def __init__(self, host: str = settings.qdrant_host, port: int = settings.qdrant_port, collection_name: str = settings.qdrant_collection_name, vector_size: int = 768, timeout: float = 60.0):
        self.host = host
        self.port = port
        self.collection_name = collection_name
        self.vector_size = vector_size
        self.client = QdrantClient(host=self.host, port=self.port, timeout=timeout)

    def initialize_schema(self) -> None:
        collections = self.client.get_collections().collections
        exists = any(c.name == self.collection_name for c in collections)

        if not exists:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(
                    size=self.vector_size,
                    distance=models.Distance.COSINE
                ),
                optimizers_config=models.OptimizersConfigDiff(
                    indexing_threshold=settings.qdrant_indexing_threshold
                )
            )
            logger.info(f"Created Qdrant collection '{self.collection_name}' with vector size {self.vector_size}.")
        else:
            logger.info(f"Qdrant collection '{self.collection_name}' already exists.")

    def set_bulk_mode(self, enabled: bool) -> None:
        threshold = settings.qdrant_bulk_indexing_threshold if enabled else settings.qdrant_indexing_threshold
        try:
            self.client.update_collection(
                collection_name=self.collection_name,
                optimizers_config=models.OptimizersConfigDiff(
                    indexing_threshold=threshold
                )
            )
            logger.info(f"Qdrant bulk mode {'enabled' if enabled else 'disabled'} (indexing_threshold={threshold}).")
        except Exception as e:
            logger.warning(f"Failed to update Qdrant indexing threshold: {e}")

    def upsert_batch(self, ids: List[str], vectors: List[List[float]], payloads: List[Dict[str, Any]]) -> None:
        points = [
            models.PointStruct(id=card_id, vector=vector, payload=payload)
            for card_id, vector, payload in zip(ids, vectors, payloads)
        ]

        attempts = settings.db_retry_attempts
        backoff = settings.retry_backoff

        for attempt in range(1, attempts + 1):
            try:
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=points
                )
                return
            except Exception as e:
                if attempt == attempts:
                    raise RuntimeError(f"Failed to upsert batch after {attempts} attempts: {e}")
                sleep_time = backoff * (2 ** (attempt - 1))
                time.sleep(sleep_time)

    def get_existing_ids(self) -> Set[str]:
        existing_ids = set()
        offset = None

        try:
            while True:
                records, offset = self.client.scroll(
                    collection_name=self.collection_name,
                    with_payload=False,
                    with_vectors=False,
                    limit=10000,
                    offset=offset
                )
                for record in records:
                    existing_ids.add(str(record.id))
                if offset is None:
                    break
        except Exception as e:
            logger.warning(f"Collection '{self.collection_name}' does not exist or error fetching existing IDs: {e}")

        return existing_ids

    def search(
        self,
        query_vector: List[float],
        limit: int = 10,
        filters: Optional[Any] = None,
        candidate_ids: Optional[List[str]] = None
    ) -> List[Any]:
        query_filter = filters

        if candidate_ids is not None:
            id_condition = models.HasIdCondition(has_id=candidate_ids)
            if query_filter is not None:
                must_clauses = query_filter.must if query_filter.must else []
                if not isinstance(must_clauses, list):
                    must_clauses = [must_clauses]
                query_filter = models.Filter(must=must_clauses + [id_condition])
            else:
                query_filter = models.Filter(must=[id_condition])

        attempts = settings.db_retry_attempts
        backoff = settings.retry_backoff

        for attempt in range(1, attempts + 1):
            start_time = time.time()
            logger.info(f"Executing Qdrant query_points on collection '{self.collection_name}' (attempt {attempt}/{attempts}) with limit={limit}...")
            try:
                response = self.client.query_points(
                    collection_name=self.collection_name,
                    query=query_vector,
                    query_filter=query_filter,
                    limit=limit
                )
                elapsed = time.time() - start_time
                logger.info(f"Qdrant query_points completed successfully in {elapsed:.3f}s, returned {len(response.points)} points.")
                return response.points
            except Exception as e:
                elapsed = time.time() - start_time
                logger.warning(f"Qdrant query_points attempt {attempt} failed after {elapsed:.3f}s: {e}")
                if attempt == attempts:
                    raise RuntimeError(f"Failed to execute search after {attempts} attempts: {e}")
                sleep_time = backoff * (2 ** (attempt - 1))
                time.sleep(sleep_time)
