from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Set

class BaseVectorStore(ABC):
    """Abstract base class for vector database operations."""

    @abstractmethod
    def initialize_schema(self) -> None:
        """Initialize collection, payload indexes, and vector configurations."""
        pass

    @abstractmethod
    def upsert_batch(self, ids: List[str], vectors: List[List[float]], payloads: List[Dict[str, Any]]) -> None:
        """Upsert a batch of vectors, IDs, and metadata payloads."""
        pass

    @abstractmethod
    def search(
        self,
        query_vector: List[float],
        limit: int = 10,
        filters: Optional[Any] = None,
        candidate_ids: Optional[List[str]] = None
    ) -> List[Any]:
        """Perform similarity search with optional filtering and candidate ID subsetting."""
        pass

    @abstractmethod
    def get_existing_ids(self) -> Set[str]:
        """Retrieve all currently indexed vector IDs for resume capability."""
        pass

    @abstractmethod
    def set_bulk_mode(self, enabled: bool) -> None:
        """Toggle Qdrant indexing thresholds between bulk loading mode and fast real-time mode."""
        pass
