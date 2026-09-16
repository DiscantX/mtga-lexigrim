print("Initializing ingest.py...")

import os
import sys
import json
import functools
import time
import threading
import queue
from contextlib import contextmanager
from collections import defaultdict
from qdrant_client import QdrantClient, models
from fastembed import TextEmbedding
from tqdm import tqdm
from qdrant_manager import ensure_qdrant_running

# Automatically ensure database pathing is correct
ensure_qdrant_running()

JSONL_PATH = 'corpus/default-cards-20260915210531.jsonl'
MODEL_NAME = "nomic-ai/nomic-embed-text-v1.5"
EMBEDDING_BATCH_SIZE = 2
UPSERT_BATCH_SIZE = 128
FE_THREADS = 2
QUEUE_MAXSIZE = 1000
REPORT_INTERVAL = 50

qclient = QdrantClient(host="localhost", port=6333)

# Initialize FastEmbed TextEmbedding model with 4 threads
embedding_model = TextEmbedding(model_name=MODEL_NAME, threads=FE_THREADS)

class IngestionTimer:
    def __init__(self):
        self.timings = defaultdict(float)
        self.counts = defaultdict(int)
        self.lock = threading.Lock()

    @contextmanager
    def measure(self, name: str):
        start = time.perf_counter()
        try:
            yield
        finally:
            elapsed = time.perf_counter() - start
            with self.lock:
                self.timings[name] += elapsed
                self.counts[name] += 1

    def get_avg(self, name: str) -> float:
        with self.lock:
            count = self.counts[name]
            return self.timings[name] / count if count > 0 else 0.0

    def report(self):
        tqdm.write("\n=== Ingestion Pipeline Performance Report ===")
        with self.lock:
            total_time = sum(self.timings.values())
            timings_snapshot = dict(self.timings)
            counts_snapshot = dict(self.counts)
        for name, duration in sorted(timings_snapshot.items(), key=lambda x: x[1], reverse=True):
            count = counts_snapshot[name]
            avg = duration / count if count > 0 else 0
            pct = (duration / total_time * 100) if total_time > 0 else 0
            tqdm.write(f"  - {name}: {duration:.3f}s total ({count} calls, avg {avg:.4f}s, {pct:.1f}%)")
        tqdm.write(f"Total time measured: {total_time:.3f}s\n")

def stream_objects_with_pos(file_path: str, chunk_size: int = 65536):
    """Your memory-safe streaming generator."""
    decoder = json.JSONDecoder()
    buffer = ""
    with open(file_path, "r", encoding="utf-8") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            bytes_read = f.tell()
            buffer += chunk
            while buffer:
                buffer = buffer.strip()
                try:
                    card_obj, index = decoder.raw_decode(buffer)
                    yield card_obj, bytes_read
                    buffer = buffer[index:]
                except json.JSONDecodeError:
                    break

def extract_embedding_text(card: dict) -> str:
    """Formats single or double-faced cards for the Nomic model."""
    if "card_faces" in card and isinstance(card["card_faces"], list):
        faces = []
        for face in card["card_faces"]:
            faces.append(
                f"Face: {face.get('name','')} | Cost: {face.get('mana_cost','')} | "
                f"Type: {face.get('type_line','')} | Text: {face.get('oracle_text','')}"
            )
        return f"search_document: {' // '.join(faces)}"
    
    return (
        f"search_document: Name: {card.get('name','')} | Cost: {card.get('mana_cost','')} | "
        f"Type: {card.get('type_line','')} | Text: {card.get('oracle_text','')}"
    )

ESSENTIAL_PAYLOAD_FIELDS = {
    # Core Identity & Rules
    "id", "oracle_id", "name", "lang", "mana_cost", "cmc", "type_line",
    "oracle_text", "colors", "color_identity", "keywords", "power",
    "toughness", "loyalty", "defense", "card_faces",

    # Set & Edition Info
    "set", "set_id", "set_name", "set_type", "collector_number", "rarity", "released_at",

    # Images (CDN URLs)
    "image_uris",

    # Format Legalities (used by Qdrant filters in search.py)
    "legalities"
}

def extract_clean_payload(card: dict) -> dict:
    """Filters out heavy/non-essential Scryfall payload fields to save ~80% Qdrant disk/RAM space."""
    return {k: v for k, v in card.items() if k in ESSENTIAL_PAYLOAD_FIELDS and v is not None}

embedding_cache: dict[str, list[float]] = {}
MAX_CACHE_SIZE = 5000

def process_batch(batch_cards, timer: IngestionTimer, skipped_cards: list) -> list[models.PointStruct]:
    """Batches text strings together, checks bounded in-memory cache, generates embeddings using FastEmbed for novel texts, and prepares PointStruct objects with robust exception handling."""
    global embedding_cache
    points = []
    valid_cards_and_texts = []

    with timer.measure("Text Formatting & Cache Lookup"):
        for card in batch_cards:
            try:
                if not isinstance(card, dict) or "id" not in card:
                    raise ValueError(f"Invalid card object format or missing 'id': {card}")
                text = extract_embedding_text(card)
                valid_cards_and_texts.append((card, text))
            except Exception as e:
                err_msg = f"[ERROR] Failed to format/extract embedding text for card {card.get('name', 'Unknown')} (ID: {card.get('id', 'N/A')}): {e}"
                print(err_msg)
                skipped_cards.append({"card": card, "error": str(e), "stage": "text_formatting"})

        novel_texts = []
        seen_novel = set()
        for _, text in valid_cards_and_texts:
            if text not in embedding_cache and text not in seen_novel:
                novel_texts.append(text)
                seen_novel.add(text)
            
    if novel_texts:
        with timer.measure("FastEmbed Generation"):
            try:
                new_embeddings = [list(vec) for vec in embedding_model.embed(novel_texts)]
                for text, vec in zip(novel_texts, new_embeddings):
                    if len(embedding_cache) >= MAX_CACHE_SIZE:
                        evicted_key = next(iter(embedding_cache))
                        print(f"[DEBUG] Cache limit reached ({MAX_CACHE_SIZE}). Evicting key: {evicted_key[:50]}...")
                        embedding_cache.pop(evicted_key)
                    embedding_cache[text] = vec
            except Exception as e:
                print(f"[ERROR] FastEmbed generation failed for batch of {len(novel_texts)} texts: {e}. Falling back to item-by-item embedding...")
                for text in novel_texts:
                    try:
                        single_vec = list(embedding_model.embed([text]))[0]
                        if len(embedding_cache) >= MAX_CACHE_SIZE:
                            evicted_key = next(iter(embedding_cache))
                            embedding_cache.pop(evicted_key)
                        embedding_cache[text] = single_vec
                    except Exception as single_e:
                        print(f"[ERROR] Unrecoverable embedding failure for text '{text[:100]}...': {single_e}")
                        for card, t in list(valid_cards_and_texts):
                            if t == text:
                                skipped_cards.append({"card": card, "error": str(single_e), "stage": "embedding"})
                                valid_cards_and_texts.remove((card, t))
    
    with timer.measure("Payload Cleaning & Point Prep"):
        for card, text in valid_cards_and_texts:
            try:
                if text not in embedding_cache:
                    print(f"[RECOVERY] Re-embedding missing text for card {card.get('name')}: {text[:100]}...")
                    embedding_cache[text] = list(embedding_model.embed([text]))[0]
                vector = embedding_cache[text]
                clean_payload = extract_clean_payload(card)
                points.append(models.PointStruct(
                    id=card["id"],
                    vector=vector,
                    payload=clean_payload
                ))
            except Exception as e:
                err_msg = f"[ERROR] Failed to clean payload or prepare PointStruct for card {card.get('name', 'Unknown')} (ID: {card.get('id', 'N/A')}): {e}"
                print(err_msg)
                skipped_cards.append({"card": card, "error": str(e), "stage": "payload_cleaning_or_prep"})

    return points

def qdrant_consumer_worker(q: queue.Queue, timer: IngestionTimer, error_holder: list, skipped_cards: list):
    """Dedicated background worker thread for sequential Qdrant upserts with buffering, timeout flushing, and error recovery."""
    buffer = []
    try:
        while True:
            try:
                item = q.get(timeout=2.0)
            except queue.Empty:
                if buffer:
                    with timer.measure("Qdrant Upsert"):
                        for attempt in range(5):
                            try:
                                qclient.upsert(collection_name="mtg_cards", points=buffer)
                                break
                            except Exception as e:
                                if attempt == 4:
                                    print(f"[ERROR] Unrecoverable Qdrant upsert failure for batch of {len(buffer)} points after 5 attempts: {e}")
                                    for p in buffer:
                                        skipped_cards.append({"point_id": p.id, "error": str(e), "stage": "qdrant_upsert"})
                                else:
                                    time.sleep(0.2)
                    buffer = []
                continue

            if item is None:
                # Sentinel received: flush remaining buffer and exit
                if buffer:
                    with timer.measure("Qdrant Upsert"):
                        for attempt in range(5):
                            try:
                                qclient.upsert(collection_name="mtg_cards", points=buffer)
                                break
                            except Exception as e:
                                if attempt == 4:
                                    print(f"[ERROR] Unrecoverable Qdrant upsert failure for final batch of {len(buffer)} points after 5 attempts: {e}")
                                    for p in buffer:
                                        skipped_cards.append({"point_id": p.id, "error": str(e), "stage": "qdrant_upsert"})
                                else:
                                    time.sleep(0.2)
                    buffer = []
                break

            buffer.extend(item)
            if len(buffer) >= UPSERT_BATCH_SIZE:
                batch_to_upsert = buffer[:UPSERT_BATCH_SIZE]
                buffer = buffer[UPSERT_BATCH_SIZE:]
                with timer.measure("Qdrant Upsert"):
                    for attempt in range(5):
                        try:
                            qclient.upsert(collection_name="mtg_cards", points=batch_to_upsert)
                            break
                        except Exception as e:
                            if attempt == 4:
                                print(f"[ERROR] Unrecoverable Qdrant upsert failure for batch of {len(batch_to_upsert)} points after 5 attempts: {e}")
                                for p in batch_to_upsert:
                                    skipped_cards.append({"point_id": p.id, "error": str(e), "stage": "qdrant_upsert"})
                            else:
                                time.sleep(0.2)
    except Exception as e:
        print(f"[ERROR] Qdrant consumer worker encountered unexpected exception: {e}")
        error_holder.append(e)

def ingest_cards_to_qdrant(file_path: str):
    timer = IngestionTimer()
    consumer_thread = None
    card_queue = None
    threshold_modified = False
    skipped_cards = []

    try:
        print("Checking database for existing cards to enable resume state...")
        with timer.measure("Fetch Existing Card IDs"):
            existing_ids = set()
            try:
                offset = None
                while True:
                    scroll_res, offset = qclient.scroll(
                        collection_name="mtg_cards",
                        with_payload=False,
                        with_vectors=False,
                        limit=1000,
                        offset=offset
                    )
                    for point in scroll_res:
                        existing_ids.add(point.id)
                    if not offset:
                        break
                print(f"Found {len(existing_ids):,} cards already indexed. Skipping these automatically.")
            except Exception as e:
                print(f"[WARNING] Could not fetch existing collection records: {e}. Starting fresh ingestion.")

        print("Disabling Qdrant indexing threshold for fast bulk ingestion...")
        qclient.update_collection(
            collection_name="mtg_cards",
            optimizer_config=models.OptimizersConfigDiff(indexing_threshold=1000000)
        )
        threshold_modified = True

        print("Pre-scanning dataset to determine total cards...")
        with timer.measure("Pre-scan Line Count"):
            with open(file_path, "r", encoding="utf-8") as f:
                total_cards = sum(1 for _ in f)

        # Initialize Queue and Background Consumer Worker Thread
        card_queue = queue.Queue(maxsize=QUEUE_MAXSIZE)
        error_holder = []
        consumer_thread = threading.Thread(
            target=qdrant_consumer_worker,
            args=(card_queue, timer, error_holder, skipped_cards),
            daemon=True
        )
        consumer_thread.start()

        processed_this_run = 0
        current_embedding_batch = []
        
        estimated_pending = total_cards - len(existing_ids)
        print(f"Dataset stats: {total_cards:,} total cards | {len(existing_ids):,} already in DB | ~{estimated_pending:,} to process.")

        print("Streaming cards directly to FastEmbed...")
        with tqdm(total=estimated_pending, unit="cards", desc="Ingesting MTG Cards", dynamic_ncols=True) as pbar:
            for card_obj, _ in stream_objects_with_pos(file_path):
                try:
                    if not isinstance(card_obj, dict) or "id" not in card_obj:
                        raise ValueError(f"Invalid card object format or missing 'id'")
                    
                    if card_obj["id"] in existing_ids:
                        continue
                    
                    current_embedding_batch.append(card_obj)

                    if len(current_embedding_batch) >= EMBEDDING_BATCH_SIZE:
                        points = process_batch(current_embedding_batch, timer, skipped_cards)
                        card_queue.put(points)
                        
                        processed_this_run += len(current_embedding_batch)
                        pbar.update(len(current_embedding_batch))
                        current_embedding_batch = []

                    if error_holder:
                        raise error_holder[0]

                    if processed_this_run % REPORT_INTERVAL == 0:
                        pbar.set_postfix({
                            "Total DB": len(existing_ids) + processed_this_run,
                            "Cache Size": len(embedding_cache),
                            "Embed/b": f"{timer.get_avg('FastEmbed Generation'):.2f}s",
                            "Upsert/b": f"{timer.get_avg('Qdrant Upsert'):.2f}s"
                        })
                except Exception as e:
                    err_msg = f"[ERROR] Failed to process card item: {e}"
                    print(err_msg)
                    skipped_cards.append({"card": card_obj if isinstance(card_obj, dict) else {}, "error": str(e), "stage": "stream_processing"})

            # Catch remaining stray cards
            if current_embedding_batch:
                try:
                    points = process_batch(current_embedding_batch, timer, skipped_cards)
                    card_queue.put(points)
                    processed_this_run += len(current_embedding_batch)
                    pbar.update(len(current_embedding_batch))
                except Exception as e:
                    print(f"[ERROR] Failed to process final embedding batch: {e}")

        # Signal completion to consumer worker
        if card_queue:
            card_queue.put(None)
        if consumer_thread and consumer_thread.is_alive():
            consumer_thread.join()

        if error_holder:
            raise error_holder[0]

        print("\nVerifying ingestion completeness...")
        with timer.measure("Post-Ingestion Verification"):
            db_ids = set()
            try:
                offset = None
                while True:
                    scroll_res, offset = qclient.scroll(
                        collection_name="mtg_cards",
                        with_payload=False,
                        with_vectors=False,
                        limit=1000,
                        offset=offset
                    )
                    for point in scroll_res:
                        db_ids.add(point.id)
                    if not offset:
                        break
            except Exception as e:
                print(f"[WARNING] Could not fetch DB IDs for verification: {e}")

            jsonl_cards = []
            for card_obj, _ in stream_objects_with_pos(file_path):
                if isinstance(card_obj, dict) and "id" in card_obj:
                    jsonl_cards.append(card_obj)
            
            missed_cards = [card for card in jsonl_cards if card["id"] not in db_ids]

        if missed_cards:
            print(f"[VERIFICATION] Found {len(missed_cards)} missed cards. Automatically re-ingesting...")
            card_queue = queue.Queue(maxsize=QUEUE_MAXSIZE)
            error_holder = []
            consumer_thread = threading.Thread(
                target=qdrant_consumer_worker,
                args=(card_queue, timer, error_holder, skipped_cards),
                daemon=True
            )
            consumer_thread.start()

            current_embedding_batch = []
            with tqdm(total=len(missed_cards), unit="cards", desc="Re-ingesting Missed Cards", dynamic_ncols=True) as pbar:
                for card_obj in missed_cards:
                    try:
                        current_embedding_batch.append(card_obj)
                        if len(current_embedding_batch) >= EMBEDDING_BATCH_SIZE:
                            points = process_batch(current_embedding_batch, timer, skipped_cards)
                            card_queue.put(points)
                            pbar.update(len(current_embedding_batch))
                            current_embedding_batch = []
                        if error_holder:
                            raise error_holder[0]
                    except Exception as e:
                        print(f"[ERROR] Failed during re-ingestion of card {card_obj.get('name', 'Unknown')}: {e}")
                        skipped_cards.append({"card": card_obj, "error": str(e), "stage": "reingestion"})

                if current_embedding_batch:
                    try:
                        points = process_batch(current_embedding_batch, timer, skipped_cards)
                        card_queue.put(points)
                        pbar.update(len(current_embedding_batch))
                    except Exception as e:
                        print(f"[ERROR] Failed during final re-ingestion batch: {e}")

            card_queue.put(None)
            if consumer_thread and consumer_thread.is_alive():
                consumer_thread.join()
            if error_holder:
                raise error_holder[0]
            print("[VERIFICATION] Re-ingestion of missed cards completed successfully.")
        else:
            print("[VERIFICATION] Zero missed cards detected. Ingestion is 100% complete!")

    except KeyboardInterrupt:
        print("\n[!] Safe exit requested (Ctrl+C). Cleaning up and shutting down...")
        if card_queue:
            try:
                card_queue.put(None)
            except Exception:
                pass
        if consumer_thread and consumer_thread.is_alive():
            print("Waiting for background upsert worker to finish pending batch...")
            consumer_thread.join(timeout=5.0)
        sys.exit(0)

    finally:
        if threshold_modified:
            print("Restoring Qdrant indexing threshold (20000)...")
            try:
                qclient.update_collection(
                    collection_name="mtg_cards",
                    optimizer_config=models.OptimizersConfigDiff(indexing_threshold=20000)
                )
            except Exception:
                pass
        
        # Display skipped cards summary
        if skipped_cards:
            print(f"\n=== Skipped Cards Summary ({len(skipped_cards)} total) ===")
            for item in skipped_cards[:20]:
                card_info = item.get("card", {})
                card_name = card_info.get("name", item.get("point_id", "Unknown"))
                stage = item.get("stage", "unknown")
                error = item.get("error", "Unknown error")
                print(f"  - Card/Point: '{card_name}' | Stage: {stage} | Error: {error}")
            if len(skipped_cards) > 20:
                print(f"  ... and {len(skipped_cards) - 20} more skipped items.")
        else:
            print("\n=== Skipped Cards Summary: 0 cards skipped (100% success rate!) ===")

        timer.report()

if __name__ == "__main__":
    ingest_cards_to_qdrant(JSONL_PATH)
