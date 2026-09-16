import threading
from collections import OrderedDict
from typing import List
from fastembed import TextEmbedding
from config.settings import settings
from embeddings.base import BaseEmbeddingService

class FastEmbedProvider(BaseEmbeddingService):
    """FastEmbed-backed embedding service with thread-safe LRU caching and lazy initialization."""

    def __init__(self, model_name: str = settings.embedding_model_name, max_cache_size: int = getattr(settings, "embedding_cache_size", 5000)):
        self.model_name = model_name
        self.max_cache_size = max_cache_size
        self._model = None
        self._lock = threading.Lock()
        self._cache_lock = threading.Lock()
        self._cache: OrderedDict[str, List[float]] = OrderedDict()

    @property
    def _lazy_model(self) -> TextEmbedding:
        if self._model is None:
            with self._lock:
                if self._model is None:
                    self._model = TextEmbedding(
                        model_name=self.model_name,
                        threads=settings.fe_threads
                    )
        return self._model

    @property
    def dimension(self) -> int:
        # Determine dimension by embedding a test string or inspecting model metadata
        sample_vector = self.embed_query("test")
        return len(sample_vector)

    def embed_query(self, query: str) -> List[float]:
        with self._cache_lock:
            if query in self._cache:
                self._cache.move_to_end(query)
                return self._cache[query]

        results = list(self._lazy_model.embed([query]))
        vector = results[0].tolist() if hasattr(results[0], "tolist") else list(results[0])

        with self._cache_lock:
            if query in self._cache:
                self._cache.move_to_end(query)
            else:
                self._cache[query] = vector
                if len(self._cache) > self.max_cache_size:
                    self._cache.popitem(last=False)
        return vector

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        uncached_texts = []
        uncached_indices = []
        vectors: List[List[float]] = [[] for _ in texts]

        with self._cache_lock:
            for i, text in enumerate(texts):
                if text in self._cache:
                    self._cache.move_to_end(text)
                    vectors[i] = self._cache[text]
                else:
                    uncached_texts.append(text)
                    uncached_indices.append(i)

        if uncached_texts:
            raw_embeddings = self._lazy_model.embed(uncached_texts)
            computed_vectors = [
                emb.tolist() if hasattr(emb, "tolist") else list(emb)
                for emb in raw_embeddings
            ]

            with self._cache_lock:
                for text, vector in zip(uncached_texts, computed_vectors):
                    if text in self._cache:
                        self._cache.move_to_end(text)
                    else:
                        self._cache[text] = vector
                        if len(self._cache) > self.max_cache_size:
                            self._cache.popitem(last=False)

            for idx, vector in zip(uncached_indices, computed_vectors):
                vectors[idx] = vector

        return vectors
