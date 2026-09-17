import logging
import uuid
from typing import Any, Dict, List, Optional
from tqdm import tqdm

from config.settings import Settings, settings as default_settings
from core.streaming import JsonlStreamReader
from core.timer import IngestionTimer
from embeddings.base import BaseEmbeddingService
from vectorstores.base import BaseVectorStore
from vectorstores.service_manager import QdrantServiceManager

logger = logging.getLogger(__name__)


class RulingsIngestionPipeline:
    """Pipeline for embedding and ingesting card rulings into the mtg_rulings Qdrant collection."""

    def __init__(
        self,
        vector_store: BaseVectorStore,
        embedding_service: BaseEmbeddingService,
        timer: IngestionTimer,
        settings: Optional[Settings] = None,
    ) -> None:
        self.vector_store = vector_store
        self.embedding_service = embedding_service
        self.timer = timer
        self.settings = settings or default_settings

    def run(self, file_path: str, batch_size: int = 128, force_recreate: bool = False) -> None:
        """Execute standalone rulings ingestion."""
        collection_name = self.settings.qdrant_collection_rulings
        threshold_modified = False

        try:
            logger.info("Verifying Qdrant service availability...")
            service_manager = QdrantServiceManager(
                host=self.settings.qdrant_host, port=self.settings.qdrant_port
            )
            try:
                service_manager.ensure_running()
            except Exception as e:
                logger.warning(f"Could not verify Qdrant service manager startup: {e}")

            logger.info(f"Initializing schema for collection '{collection_name}'...")
            with self.timer.measure("Initialize Schema"):
                self.vector_store.initialize_schema(collection_name=collection_name)

            existing_ids = set()
            if not force_recreate:
                logger.info("Fetching existing ruling IDs...")
                with self.timer.measure("Fetch Existing Ruling IDs"):
                    existing_ids = self.vector_store.get_existing_ids(collection_name=collection_name)

            logger.info(f"Enabling bulk mode for collection '{collection_name}'...")
            self.vector_store.set_bulk_mode(True, collection_name=collection_name)
            threshold_modified = True

            total_rulings = JsonlStreamReader.count_lines(file_path)
            logger.info(f"Total rulings in source: {total_rulings:,} | Already indexed: {len(existing_ids):,}")

            current_texts: List[str] = []
            current_payloads: List[Dict[str, Any]] = []
            current_ids: List[str] = []
            processed_count = 0

            reader = JsonlStreamReader(file_path)
            with tqdm(total=total_rulings, desc="Ingesting MTG Rulings", unit="ruling", dynamic_ncols=True) as pbar:
                for record, _ in reader.stream():
                    if not isinstance(record, dict):
                        pbar.update(1)
                        continue

                    oracle_id = record.get("oracle_id", "")
                    comment = record.get("comment", "")
                    published_at = record.get("published_at", "")
                    source = record.get("source", "wotc")

                    if not comment:
                        pbar.update(1)
                        continue

                    ruling_id_str = f"{oracle_id}_{comment}"
                    ruling_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, ruling_id_str))

                    if not force_recreate and ruling_id in existing_ids:
                        pbar.update(1)
                        continue

                    payload = {
                        "oracle_id": oracle_id,
                        "comment": comment,
                        "published_at": published_at,
                        "source": source,
                    }

                    current_texts.append(comment)
                    current_payloads.append(payload)
                    current_ids.append(ruling_id)

                    if len(current_texts) >= batch_size:
                        self._flush_batch(current_texts, current_payloads, current_ids, collection_name)
                        processed_count += len(current_texts)
                        pbar.update(len(current_texts))
                        current_texts, current_payloads, current_ids = [], [], []

                if current_texts:
                    self._flush_batch(current_texts, current_payloads, current_ids, collection_name)
                    processed_count += len(current_texts)
                    pbar.update(len(current_texts))

            logger.info(f"Successfully ingested {processed_count:,} rulings into '{collection_name}'.")

        finally:
            if threshold_modified:
                logger.info(f"Restoring standard mode for collection '{collection_name}'...")
                try:
                    self.vector_store.set_bulk_mode(False, collection_name=collection_name)
                except Exception as e:
                    logger.warning(f"Failed to restore indexing threshold: {e}")
            self.timer.report(printer=logger.info)

    def _flush_batch(self, texts: List[str], payloads: List[Dict[str, Any]], ids: List[str], collection_name: str) -> None:
        with self.timer.measure("Embedding Generation"):
            vectors = self.embedding_service.embed_documents(texts)
        with self.timer.measure("Vector Store Upsert"):
            self.vector_store.upsert_batch(
                ids=ids,
                vectors=vectors,
                payloads=payloads,
                collection_name=collection_name
            )
