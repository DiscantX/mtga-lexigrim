import os
import json
import functools
import time
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
BATCH_SIZE = 32  # Safe memory-friendly batch size for low-end laptops
FE_THREADS = 4

qclient = QdrantClient(host="localhost", port=6333)

# Initialize FastEmbed TextEmbedding model with restricted thread count (2 threads) to prevent CPU/memory freezing
embedding_model = TextEmbedding(model_name=MODEL_NAME, threads=FE_THREADS)

class IngestionTimer:
    def __init__(self):
        self.timings = defaultdict(float)
        self.counts = defaultdict(int)

    @contextmanager
    def measure(self, name: str):
        start = time.perf_counter()
        try:
            yield
        finally:
            elapsed = time.perf_counter() - start
            self.timings[name] += elapsed
            self.counts[name] += 1

    def report(self):
        print("\n=== Ingestion Pipeline Performance Report ===")
        total_time = sum(self.timings.values())
        for name, duration in sorted(self.timings.items(), key=lambda x: x[1], reverse=True):
            count = self.counts[name]
            avg = duration / count if count > 0 else 0
            pct = (duration / total_time * 100) if total_time > 0 else 0
            print(f"  - {name}: {duration:.3f}s total ({count} calls, avg {avg:.4f}s, {pct:.1f}%)")
        print(f"Total time measured: {total_time:.3f}s\n")

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

def process_and_upsert_batch(batch_cards, timer: IngestionTimer):
    """Batches text strings together, checks bounded in-memory cache, generates embeddings using FastEmbed for novel texts, and upserts with Windows safety retries."""
    global embedding_cache
    with timer.measure("Text Formatting & Cache Lookup"):
        card_texts = [(card, extract_embedding_text(card)) for card in batch_cards]
        
        novel_texts = []
        seen_novel = set()
        for _, text in card_texts:
            if text not in embedding_cache and text not in seen_novel:
                novel_texts.append(text)
                seen_novel.add(text)
            
    if novel_texts:
        with timer.measure("FastEmbed Generation"):
            # FastEmbed Batch Embedding Call for novel texts only
            new_embeddings = [list(vec) for vec in embedding_model.embed(novel_texts)]
        for text, vec in zip(novel_texts, new_embeddings):
            if len(embedding_cache) >= MAX_CACHE_SIZE:
                # Evict oldest entry if cache is full
                embedding_cache.pop(next(iter(embedding_cache)))
            embedding_cache[text] = vec
    
    with timer.measure("Payload Cleaning & Point Prep"):
        points = []
        for card, text in card_texts:
            vector = embedding_cache[text]
            points.append(models.PointStruct(
                id=card["id"],
                vector=vector,
                payload=extract_clean_payload(card)
            ))
        
    # 🛠️ WINDOWS RESILIENCE BLOCK: Retry writes if Windows locks a file handle temporarily
    with timer.measure("Qdrant Upsert"):
        for attempt in range(5):
            try:
                qclient.upsert(collection_name="mtg_cards", points=points)
                break # Success! Exit the retry block
            except Exception as e:
                if attempt == 4: # If it fails 5 times, raise the error
                    raise e
                # Pause briefly to allow the Windows file system thread to release the lock
                time.sleep(0.2) 

def ingest_cards_to_qdrant(file_path: str):
    timer = IngestionTimer()
    current_batch = []
    
    print("Checking database for existing cards to enable resume state...")
    # Fetch existing IDs to prevent rewriting (handles future updates/crashes instantly)
    # We scroll through existing points completely using a lightweight payload-free stream
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
        except Exception:
            print("No prior collection records found. Starting fresh ingestion.")

    print("Disabling Qdrant indexing threshold for fast bulk ingestion...")
    qclient.update_collection(
        collection_name="mtg_cards",
        optimizer_config=models.OptimizersConfigDiff(indexing_threshold=1000000)
    )

    print("Pre-scanning dataset to determine total cards...")
    with timer.measure("Pre-scan Line Count"):
        with open(file_path, "r", encoding="utf-8") as f:
            total_cards = sum(1 for _ in f)

    print("Filtering dataset for pending cards...")
    with timer.measure("Streaming & Filtering"):
        pending_cards = []
        skipped_existing = 0

        for card_obj, _ in stream_objects_with_pos(file_path):
            if card_obj["id"] in existing_ids:
                skipped_existing += 1
                continue
            pending_cards.append(card_obj)

    total_pending = len(pending_cards)
    print(f"Dataset stats: {total_cards:,} total cards | {skipped_existing:,} already in DB | {total_pending:,} to process.")

    try:
        processed_this_run = 0
        with tqdm(total=total_pending, unit="cards", desc="Ingesting MTG Cards") as pbar:
            for card_obj in pending_cards:
                current_batch.append(card_obj)

                # Process when batch is filled
                if len(current_batch) >= BATCH_SIZE:
                    process_and_upsert_batch(current_batch, timer)
                    processed_this_run += len(current_batch)
                    current_batch = []

                pbar.set_postfix({
                    "Total DB": len(existing_ids) + processed_this_run,
                    "Cache Size": len(embedding_cache)
                })
                pbar.update(1)

            # Catch remaining stray points
            if current_batch:
                process_and_upsert_batch(current_batch, timer)
                processed_this_run += len(current_batch)
                pbar.update(len(current_batch))
                pbar.set_postfix({"Total DB": len(existing_ids) + processed_this_run})
    finally:
        print("Restoring Qdrant indexing threshold (20000)...")
        qclient.update_collection(
            collection_name="mtg_cards",
            optimizer_config=models.OptimizersConfigDiff(indexing_threshold=20000)
        )
        timer.report()

if __name__ == "__main__":
    ingest_cards_to_qdrant(JSONL_PATH)