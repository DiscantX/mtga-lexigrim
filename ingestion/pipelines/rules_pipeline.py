import logging
import uuid
from typing import Any, Dict, List, Optional
from qdrant_client.http import models
from tqdm import tqdm

from config.settings import Settings, settings as default_settings
from core.timer import IngestionTimer
from embeddings.base import BaseEmbeddingService
from ingestion.readers.rule_reader import TextRuleReader
from vectorstores.base import BaseVectorStore
from vectorstores.service_manager import QdrantServiceManager

logger = logging.getLogger(__name__)

class RulesIngestionPipeline:
    """Pipeline for parsing, embedding, and ingesting MTG Comprehensive Rules into Qdrant."""

    def __init__(
        self,
        vector_store: BaseVectorStore,
        embedding_service: BaseEmbeddingService,
        timer: IngestionTimer,
        settings: Optional[Settings] = None,
        rule_reader: Optional[TextRuleReader] = None,
    ) -> None:
        self.vector_store = vector_store
        self.embedding_service = embedding_service
        self.timer = timer
        self.settings = settings or default_settings
        self.rule_reader = rule_reader or TextRuleReader()

    def run(self, batch_size: int = 128, force_recreate: bool = False) -> None:
        """Execute the rules ingestion pipeline flow."""
        collection_name = self.settings.qdrant_collection_rules
        threshold_modified = False

        try:
            # 1. Service check
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
                logger.info(f"Fetching existing rule IDs from '{collection_name}'...")
                with self.timer.measure("Fetch Existing Rule IDs"):
                    existing_ids = self.vector_store.get_existing_ids(collection_name=collection_name)
                logger.info(f"Found {len(existing_ids):,} rules already indexed.")

            # 4. Bulk mode
            logger.info(f"Enabling bulk mode for collection '{collection_name}'...")
            self.vector_store.set_bulk_mode(True, collection_name=collection_name)
            threshold_modified = True

            # 5. Stream and process rules
            batch_records: List[Dict[str, Any]] = []
            batch_texts: List[str] = []
            batch_ids: List[str] = []
            batch_payloads: List[Dict[str, Any]] = []

            processed_count = 0

            with tqdm(desc="Ingesting MTG Rules", unit="rules", dynamic_ncols=True) as pbar:
                for rule in self.rule_reader.stream_records():
                    rule_id = rule.get("rule_id")
                    if not rule_id:
                        continue

                    point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, rule_id))
                    if not force_recreate and point_id in existing_ids:
                        continue

                    batch_records.append(rule)
                    batch_texts.append(rule["text"])
                    batch_ids.append(point_id)
                    batch_payloads.append({
                        "rule_id": rule["rule_id"],
                        "chapter": rule["chapter"],
                        "section": rule["section"],
                        "text": rule["text"],
                        "hierarchy_path": rule["hierarchy_path"],
                    })

                    if len(batch_texts) >= batch_size:
                        self._process_and_upsert_batch(
                            batch_ids, batch_texts, batch_payloads, collection_name
                        )
                        processed_count += len(batch_texts)
                        pbar.update(len(batch_texts))
                        batch_records = []
                        batch_texts = []
                        batch_ids = []
                        batch_payloads = []

                # Final batch
                if batch_texts:
                    self._process_and_upsert_batch(
                        batch_ids, batch_texts, batch_payloads, collection_name
                    )
                    processed_count += len(batch_texts)
                    pbar.update(len(batch_texts))

            logger.info(f"Successfully processed and ingested {processed_count:,} rules into '{collection_name}'.")

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
