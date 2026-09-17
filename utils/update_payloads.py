import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from config.settings import settings
from core.streaming import JsonlStreamReader
from embeddings.text_extractors import extract_clean_payload
from vectorstores.qdrant import QdrantVectorStore

# logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

def update_payloads(max_workers: int = 32):
    corpus_path = settings.data_corpus_path
    logger.info(f"Starting memory-safe streaming payload synchronization from: {corpus_path}")

    vector_store = QdrantVectorStore()
    total_lines = JsonlStreamReader.count_lines(corpus_path)
    logger.info(f"Corpus total records: {total_lines:,}")

    stream_reader = JsonlStreamReader(corpus_path)

    def update_single(card_id: str, payload: dict):
        try:
            vector_store.client.set_payload(
                collection_name=vector_store.collection_name,
                payload=payload,
                points=[card_id]
            )
            return True
        except Exception:
            return False

    updated_count = 0
    failed_count = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        with tqdm(total=total_lines, unit="cards", desc="Streaming & Syncing Payloads") as pbar:
            futures = []
            for card_obj, _ in stream_reader.stream():
                if isinstance(card_obj, dict) and "id" in card_obj:
                    card_id = str(card_obj["id"])
                    clean_payload = extract_clean_payload(card_obj)
                    futures.append(executor.submit(update_single, card_id, clean_payload))

                # Submit in chunks to avoid unbounded memory queue
                if len(futures) >= 1000:
                    for future in as_completed(futures):
                        if future.result():
                            updated_count += 1
                        else:
                            failed_count += 1
                        pbar.update(1)
                    futures = []

            # Drain remaining
            if futures:
                for future in as_completed(futures):
                    if future.result():
                        updated_count += 1
                    else:
                        failed_count += 1
                    pbar.update(1)

    logger.info(f"Payload synchronization finished! Updated: {updated_count:,} | Failed: {failed_count:,}")

if __name__ == "__main__":
    update_payloads()
