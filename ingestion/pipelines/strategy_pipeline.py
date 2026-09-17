import logging
import uuid
from typing import Any, Dict, List, Optional
from tqdm import tqdm

from config.settings import Settings, settings as default_settings
from core.timer import IngestionTimer
from embeddings.base import BaseEmbeddingService
from ingestion.readers.markdown_reader import MarkdownArticleReader
from ingestion.chunking import RecursiveTextChunker, format_chunk_for_embedding
from vectorstores.base import BaseVectorStore
from vectorstores.service_manager import QdrantServiceManager

logger = logging.getLogger(__name__)


class StrategyIngestionPipeline:
    """Pipeline for parsing strategy markdown articles, recursively chunking, embedding,

    and ingesting into the mtg_strategy Qdrant collection with rich provenance metadata.
    """

    def __init__(
        self,
        vector_store: BaseVectorStore,
        embedding_service: BaseEmbeddingService,
        timer: IngestionTimer,
        settings: Optional[Settings] = None,
        markdown_reader: Optional[MarkdownArticleReader] = None,
        chunker: Optional[RecursiveTextChunker] = None,
    ) -> None:
        self.vector_store = vector_store
        self.embedding_service = embedding_service
        self.timer = timer
        self.settings = settings or default_settings
        self.markdown_reader = markdown_reader or MarkdownArticleReader()
        self.chunker = chunker or RecursiveTextChunker()

    def run(self, batch_size: int = 128, force_recreate: bool = False) -> None:
        """Execute the strategy article ingestion pipeline flow."""
        collection_name = self.settings.qdrant_collection_strategy
        threshold_modified = False

        try:
            # 1. Service Check
            logger.info("Verifying Qdrant service availability...")
            service_manager = QdrantServiceManager(
                host=self.settings.qdrant_host, port=self.settings.qdrant_port
            )
            try:
                service_manager.ensure_running()
            except Exception as e:
                logger.warning(f"Could not verify Qdrant service manager startup: {e}")

            # 2. Initialize Schema
            logger.info(f"Initializing schema for Qdrant collection '{collection_name}'...")
            with self.timer.measure("Initialize Schema"):
                self.vector_store.initialize_schema(collection_name=collection_name)

            # 3. Resume / Existing IDs
            existing_ids = set()
            if not force_recreate:
                logger.info(f"Fetching existing strategy chunk IDs from '{collection_name}'...")
                with self.timer.measure("Fetch Existing Strategy IDs"):
                    existing_ids = self.vector_store.get_existing_ids(collection_name=collection_name)
                logger.info(f"Found {len(existing_ids):,} chunks already indexed.")

            # 4. Bulk mode
            logger.info(f"Enabling bulk mode for collection '{collection_name}'...")
            self.vector_store.set_bulk_mode(True, collection_name=collection_name)
            threshold_modified = True

            # 5. Stream, chunk, embed, and upsert articles
            batch_texts: List[str] = []
            batch_ids: List[str] = []
            batch_payloads: List[Dict[str, Any]] = []

            processed_chunks_count = 0
            processed_articles_count = 0

            with tqdm(desc="Ingesting Strategy Articles", unit="chunks", dynamic_ncols=True) as pbar:
                for article in self.markdown_reader.stream_records():
                    article_id = article.get("article_id")
                    content = article.get("content")
                    if not article_id or not content:
                        continue

                    processed_articles_count += 1
                    chunks = self.chunker.chunk_text(content)

                    for chunk_idx, chunk_text in enumerate(chunks):
                        # Deterministic point ID from article_id and chunk index
                        point_key = f"{article_id}_chunk_{chunk_idx}"
                        point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, point_key))

                        if not force_recreate and point_id in existing_ids:
                            continue

                        # Format text with provenance header for embedding
                        embedding_text = format_chunk_for_embedding(article, chunk_text, chunk_idx)

                        payload = {
                            "article_id": article_id,
                            "title": article.get("title"),
                            "author": article.get("author"),
                            "source": article.get("source"),
                            "published_at": article.get("published_at"),
                            "evergreen": article.get("evergreen", False),
                            "tags": article.get("tags", []),
                            "chunk_index": chunk_idx,
                            "total_chunks": len(chunks),
                            "text": chunk_text,
                        }

                        batch_texts.append(embedding_text)
                        batch_ids.append(point_id)
                        batch_payloads.append(payload)

                        if len(batch_texts) >= batch_size:
                            self._process_and_upsert_batch(
                                batch_ids, batch_texts, batch_payloads, collection_name
                            )
                            processed_chunks_count += len(batch_texts)
                            pbar.update(len(batch_texts))
                            batch_texts = []
                            batch_ids = []
                            batch_payloads = []

                # Final batch
                if batch_texts:
                    self._process_and_upsert_batch(
                        batch_ids, batch_texts, batch_payloads, collection_name
                    )
                    processed_chunks_count += len(batch_texts)
                    pbar.update(len(batch_texts))

            logger.info(
                f"Successfully processed {processed_articles_count} articles into {processed_chunks_count:,} chunks in '{collection_name}'."
            )

        finally:
            if threshold_modified:
                logger.info(f"Restoring standard Qdrant indexing threshold for '{collection_name}'...")
                try:
                    self.vector_store.set_bulk_mode(False, collection_name=collection_name)
                except Exception as e:
                    logger.warning(f"Failed to restore indexing threshold: {e}")

            self.timer.report(printer=logger.info)

    def _process_and_upsert_batch(
        self,
        ids: List[str],
        texts: List[str],
        payloads: List[Dict[str, Any]],
        collection_name: str,
    ) -> None:
        with self.timer.measure("Embedding Generation"):
            vectors = self.embedding_service.embed_documents(texts)

        with self.timer.measure("Vector Store Upsert"):
            self.vector_store.upsert_batch(
                ids=ids,
                vectors=vectors,
                payloads=payloads,
                collection_name=collection_name,
            )
