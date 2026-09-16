from typing import Any, Optional, List
from qdrant_client.http import models
from vectorstores.base import BaseVectorStore
from embeddings.base import BaseEmbeddingService

class CardSearchEngine:
    """Object-oriented search engine decoupling search execution from vector store internals."""

    def __init__(self, vector_store: BaseVectorStore, embedding_service: BaseEmbeddingService):
        self.vector_store = vector_store
        self.embedding_service = embedding_service

    def vector_search(
        self,
        query_text: str,
        limit: Optional[int] = None,
        query_filter: Optional[Any] = None,
        candidate_ids: Optional[list[str]] = None
    ) -> list[Any]:
        """Embeds the query text and retrieves matches from vector store with non-mutating filter logic."""
        prefixed_query = f"search_query: {query_text}"

        try:
            query_vector = self.embedding_service.embed_query(prefixed_query)
        except Exception as e:
            print(f"Error generating embedding via embedding service: {e}")
            return []

        # Construct new filter safely without in-place mutation
        effective_filter = query_filter
        if candidate_ids is not None:
            has_id_condition = models.HasIdCondition(has_id=candidate_ids)
            if query_filter and hasattr(query_filter, "must") and query_filter.must:
                effective_filter = models.Filter(
                    must=list(query_filter.must) + [has_id_condition]
                )
            elif query_filter:
                effective_filter = models.Filter(
                    must=[query_filter, has_id_condition]
                )
            else:
                effective_filter = models.Filter(must=[has_id_condition])

        query_limit = limit if limit is not None else 10000
        results = self.vector_store.search(
            query_vector=query_vector,
            limit=query_limit,
            filters=effective_filter,
            candidate_ids=None  # Filtered explicitly via effective_filter to prevent mutation bugs
        )
        return results

    def multi_query_fusion(
        self,
        queries: list[str],
        limit: Optional[int] = None,
        query_filter: Optional[Any] = None
    ) -> list[Any]:
        """NO-OP / STUB METHOD FOR FUTURE ARCHITECTURE."""
        raise NotImplementedError("Multi-query fusion is stubbed for future architecture.")
