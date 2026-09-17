import logging
import queue
import threading
from typing import Any, Dict, List, Optional, Set

from qdrant_client.http import models
from tqdm import tqdm

from config.settings import Settings, settings as default_settings
from core.streaming import JsonlStreamReader
from core.timer import IngestionTimer
from embeddings.base import BaseEmbeddingService
from embeddings.text_extractors import extract_clean_payload, extract_embedding_text
from ingestion.worker import IngestionWorker
from vectorstores.base import BaseVectorStore
from vectorstores.service_manager import QdrantServiceManager

logger = logging.getLogger(__name__)


def load_rulings_index(rulings_file_path: str) -> Dict[str, List[Dict[str, Any]]]:
    """Stream card rulings from a JSONL file and group them by oracle_id."""
    rulings_index: Dict[str, List[Dict[str, Any]]] = {}
    if not rulings_file_path:
        return rulings_index
    try:
        reader = JsonlStreamReader(rulings_file_path)
        for record, _ in reader.stream():
            if not isinstance(record, dict):
                continue
            oracle_id = record.get("oracle_id")
            if not oracle_id:
                continue
            ruling_entry = {
                "source": record.get("source"),
                "published_at": record.get("published_at"),
                "comment": record.get("comment"),
            }
            rulings_index.setdefault(oracle_id, []).append(ruling_entry)
        logger.info(f"Loaded rulings index for {len(rulings_index):,} oracle IDs from {rulings_file_path}")
    except Exception as e:
        logger.error(f"Failed to load rulings index from {rulings_file_path}: {e}")
    return rulings_index


class IngestionPipeline:
    """Object-oriented data ingestion pipeline orchestrating streaming, embedding generation, worker buffering, and Qdrant persistence."""

    def __init__(
        self,
        vector_store: BaseVectorStore,
        embedding_service: BaseEmbeddingService,
        timer: IngestionTimer,
        settings: Optional[Settings] = None,
        rulings_file_path: Optional[str] = None,
    ) -> None:
        self.vector_store = vector_store
        self.embedding_service = embedding_service
        self.timer = timer
        self.settings = settings or default_settings
        self.rulings_file_path = rulings_file_path
        self.rulings_index: Dict[str, List[Dict[str, Any]]] = {}

    def run(self, file_path: str) -> None:
        """Execute the complete ingestion pipeline flow."""
        skipped_cards: List[Dict[str, Any]] = []
        threshold_modified = False
        card_queue: Optional[queue.Queue] = None
        consumer_thread: Optional[IngestionWorker] = None

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

            # 1.5. Load Rulings Index if specified
            if self.rulings_file_path:
                logger.info("Loading rulings index...")
                with self.timer.measure("Load Rulings Index"):
                    self.rulings_index = load_rulings_index(self.rulings_file_path)

            # 2. Resume Check
            logger.info("Fetching existing card IDs for resume capability...")
            with self.timer.measure("Fetch Existing Card IDs"):
                existing_ids = self.vector_store.get_existing_ids()
            logger.info(f"Found {len(existing_ids):,} cards already indexed.")

            # 3. Bulk Mode Enable
            logger.info("Enabling Qdrant bulk indexing mode...")
            self.vector_store.set_bulk_mode(True)
            threshold_modified = True

            # 4. Pre-scan Dataset
            logger.info("Pre-scanning dataset for total card count...")
            with self.timer.measure("Pre-scan Line Count"):
                total_cards = JsonlStreamReader.count_lines(file_path)
            estimated_pending = max(0, total_cards - len(existing_ids))
            logger.info(
                f"Dataset stats: {total_cards:,} total lines | {len(existing_ids):,} already in DB | ~{estimated_pending:,} to process."
            )

            # 5. Background Worker Initialization
            card_queue = queue.Queue(maxsize=self.settings.queue_maxsize)
            consumer_thread = IngestionWorker(
                q=card_queue,
                vector_store=self.vector_store,
                batch_size=self.settings.upsert_batch_size,
            )
            consumer_thread.start()

            # 6. Stream & Process Inline
            processed_this_run = 0
            current_batch_cards: List[Dict[str, Any]] = []

            with tqdm(
                total=estimated_pending,
                unit="cards",
                desc="Ingesting MTG Cards",
                dynamic_ncols=True,
            ) as pbar:
                for card_obj, _ in JsonlStreamReader(file_path).stream():
                    try:
                        if not isinstance(card_obj, dict) or "id" not in card_obj:
                            raise ValueError("Invalid card object format or missing 'id'")

                        card_id = str(card_obj["id"])
                        if card_id in existing_ids:
                            continue

                        current_batch_cards.append(card_obj)

                        if len(current_batch_cards) >= self.settings.embedding_batch_size:
                            self._process_and_queue_batch(
                                current_batch_cards, card_queue, skipped_cards
                            )
                            processed_this_run += len(current_batch_cards)
                            pbar.update(len(current_batch_cards))
                            current_batch_cards = []

                    except Exception as e:
                        err_msg = f"Failed to process card item: {e}"
                        logger.error(err_msg)
                        skipped_cards.append({
                            "card": card_obj if isinstance(card_obj, dict) else {},
                            "error": str(e),
                            "stage": "stream_processing",
                        })

                # Process final remaining batch
                if current_batch_cards:
                    try:
                        self._process_and_queue_batch(
                            current_batch_cards, card_queue, skipped_cards
                        )
                        processed_this_run += len(current_batch_cards)
                        pbar.update(len(current_batch_cards))
                    except Exception as e:
                        logger.error(f"Failed to process final embedding batch: {e}")

            # 7. Queue Shutdown
            logger.info("Waiting for queue to drain...")
            card_queue.join()
            logger.info("Sending sentinel to background worker...")
            card_queue.put(None)
            if consumer_thread and consumer_thread.is_alive():
                consumer_thread.join()

            # 8. Memory-Safe Verification
            logger.info("Performing post-ingestion memory-safe verification...")
            with self.timer.measure("Post-Ingestion Verification"):
                db_ids = self.vector_store.get_existing_ids()
                missed_cards = []
                for card_obj, _ in JsonlStreamReader(file_path).stream():
                    if isinstance(card_obj, dict) and "id" in card_obj:
                        if str(card_obj["id"]) not in db_ids:
                            missed_cards.append(card_obj)

            if missed_cards:
                logger.warning(
                    f"Found {len(missed_cards)} missed cards during verification. Re-ingesting..."
                )
                card_queue = queue.Queue(maxsize=self.settings.queue_maxsize)
                consumer_thread = IngestionWorker(
                    q=card_queue,
                    vector_store=self.vector_store,
                    batch_size=self.settings.upsert_batch_size,
                )
                consumer_thread.start()

                reingest_batch: List[Dict[str, Any]] = []
                with tqdm(
                    total=len(missed_cards),
                    unit="cards",
                    desc="Re-ingesting Missed Cards",
                    dynamic_ncols=True,
                ) as pbar:
                    for card_obj in missed_cards:
                        try:
                            reingest_batch.append(card_obj)
                            if len(reingest_batch) >= self.settings.embedding_batch_size:
                                self._process_and_queue_batch(
                                    reingest_batch, card_queue, skipped_cards
                                )
                                pbar.update(len(reingest_batch))
                                reingest_batch = []
                        except Exception as e:
                            logger.error(
                                f"Failed during re-ingestion of card {card_obj.get('name', 'Unknown')}: {e}"
                            )
                            skipped_cards.append({
                                "card": card_obj,
                                "error": str(e),
                                "stage": "reingestion",
                            })

                    if reingest_batch:
                        try:
                            self._process_and_queue_batch(
                                reingest_batch, card_queue, skipped_cards
                            )
                            pbar.update(len(reingest_batch))
                        except Exception as e:
                            logger.error(f"Failed during final re-ingestion batch: {e}")

                card_queue.join()
                card_queue.put(None)
                if consumer_thread and consumer_thread.is_alive():
                    consumer_thread.join()
                logger.info("Re-ingestion of missed cards completed.")
            else:
                logger.info("Zero missed cards detected. Ingestion verified 100% complete!")

        except KeyboardInterrupt:
            logger.warning("Safe exit requested (Ctrl+C). Cleaning up...")
            if card_queue:
                try:
                    card_queue.put(None)
                except Exception:
                    pass
            if consumer_thread and consumer_thread.is_alive():
                consumer_thread.join(timeout=5.0)
            raise

        finally:
            # 9. Restore Indexing Threshold
            if threshold_modified:
                logger.info("Restoring standard Qdrant indexing threshold...")
                try:
                    self.vector_store.set_bulk_mode(False)
                except Exception as e:
                    logger.warning(f"Failed to restore indexing threshold: {e}")

            # 10. Telemetry Report
            if skipped_cards:
                logger.warning(f"\n=== Skipped Cards Summary ({len(skipped_cards)} total) ===")
                for item in skipped_cards[:20]:
                    card_info = item.get("card", {})
                    card_name = card_info.get("name", "Unknown")
                    stage = item.get("stage", "unknown")
                    error = item.get("error", "Unknown error")
                    logger.warning(f"  - Card: '{card_name}' | Stage: {stage} | Error: {error}")
                if len(skipped_cards) > 20:
                    logger.warning(f"  ... and {len(skipped_cards) - 20} more skipped items.")
            else:
                logger.info("\n=== Skipped Cards Summary: 0 cards skipped (100% success rate!) ===")

            self.timer.report(printer=logger.info)

    def _process_and_queue_batch(
        self,
        batch_cards: List[Dict[str, Any]],
        card_queue: queue.Queue,
        skipped_cards: List[Dict[str, Any]],
    ) -> None:
        valid_texts: List[str] = []
        valid_cards: List[Dict[str, Any]] = []

        with self.timer.measure("Text Formatting & Cache Lookup"):
            for card in batch_cards:
                try:
                    if not isinstance(card, dict) or "id" not in card:
                        raise ValueError(f"Invalid card format or missing 'id': {card}")
                    text = extract_embedding_text(card)
                    valid_texts.append(text)
                    valid_cards.append(card)
                except Exception as e:
                    err_msg = f"Failed to format embedding text for card: {e}"
                    logger.error(err_msg)
                    skipped_cards.append({
                        "card": card,
                        "error": str(e),
                        "stage": "text_formatting",
                    })

        if not valid_texts:
            return

        with self.timer.measure("FastEmbed Generation"):
            try:
                embeddings = self.embedding_service.embed_documents(valid_texts)
            except Exception as e:
                logger.error(f"Embedding generation failed for batch: {e}")
                embeddings = []
                for card, text in zip(valid_cards, valid_texts):
                    try:
                        single_emb = self.embedding_service.embed_documents([text])[0]
                        embeddings.append(single_emb)
                    except Exception as single_e:
                        logger.error(f"Unrecoverable embedding failure for card {card.get('name')}: {single_e}")
                        skipped_cards.append({
                            "card": card,
                            "error": str(single_e),
                            "stage": "embedding",
                        })
                return

        with self.timer.measure("Payload Cleaning & Point Prep"):
            points = []
            for card, vector in zip(valid_cards, embeddings):
                try:
                    oracle_id = card.get("oracle_id")
                    card_rulings = self.rulings_index.get(oracle_id, []) if oracle_id else []
                    clean_payload = extract_clean_payload(card, rulings=card_rulings)
                    points.append(
                        models.PointStruct(
                            id=str(card["id"]),
                            vector=vector,
                            payload=clean_payload,
                        )
                    )
                except Exception as e:
                    err_msg = f"Failed to prepare PointStruct for card {card.get('name', 'Unknown')}: {e}"
                    logger.error(err_msg)
                    skipped_cards.append({
                        "card": card,
                        "error": str(e),
                        "stage": "payload_cleaning_or_prep",
                    })

            if points:
                card_queue.put(points)
