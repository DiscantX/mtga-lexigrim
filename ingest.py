import os
import json
from qdrant_client import QdrantClient, models
from fastembed import TextEmbedding
from tqdm import tqdm
from qdrant_manager import ensure_qdrant_running
import time # Ensure time is imported at the top of ingest.py

# Automatically ensure database pathing is correct
ensure_qdrant_running()

JSONL_PATH = 'corpus/default-cards-20260915210531.jsonl'
MODEL_NAME = "nomic-ai/nomic-embed-text-v1.5"
BATCH_SIZE = 512  # Optimized batch size for bulk ingestion throughput

qclient = QdrantClient(host="localhost", port=6333)

# Initialize FastEmbed TextEmbedding model
embedding_model = TextEmbedding(model_name=MODEL_NAME)

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

# Inside ingest.py -> update process_and_upsert_batch:

embedding_cache: dict[str, list[float]] = {}

def process_and_upsert_batch(batch_cards):
    """Batches text strings together, checks in-memory cache, generates embeddings using FastEmbed for novel texts, and upserts with Windows safety retries."""
    global embedding_cache
    card_texts = [(card, extract_embedding_text(card)) for card in batch_cards]
    
    novel_texts = []
    seen_novel = set()
    for _, text in card_texts:
        if text not in embedding_cache and text not in seen_novel:
            novel_texts.append(text)
            seen_novel.add(text)
            
    if novel_texts:
        # FastEmbed Batch Embedding Call for novel texts only
        new_embeddings = [list(vec) for vec in embedding_model.embed(novel_texts)]
        for text, vec in zip(novel_texts, new_embeddings):
            embedding_cache[text] = vec
    
    points = []
    for card, text in card_texts:
        vector = embedding_cache[text]
        points.append(models.PointStruct(
            id=card["id"],
            vector=vector,
            payload=card
        ))
        
    # 🛠️ WINDOWS RESILIENCE BLOCK: Retry writes if Windows locks a file handle temporarily
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
    file_size = os.path.getsize(file_path)
    current_batch = []
    
    print("Checking database for existing cards to enable resume state...")
    # Fetch existing IDs to prevent rewriting (handles future updates/crashes instantly)
    # We scroll through existing points completely using a lightweight payload-free stream
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

    try:
        with tqdm(total=file_size, unit="B", unit_scale=True, unit_divisor=1024, desc="Ingesting MTG Cards") as pbar:
            last_pos = 0

            for card_obj, current_pos in stream_objects_with_pos(file_path):
                pbar.update(current_pos - last_pos)
                last_pos = current_pos

                # Skip digital-only printings
                if card_obj.get("digital", False):
                    continue

                # RESUME CHECK: If card already exists in database, skip embedding math completely!
                if card_obj["id"] in existing_ids:
                    continue

                current_batch.append(card_obj)

                # Process when batch is filled
                if len(current_batch) >= BATCH_SIZE:
                    process_and_upsert_batch(current_batch)
                    current_batch = []

            # Catch remaining stray points
            if current_batch:
                process_and_upsert_batch(current_batch)
    finally:
        print("Restoring Qdrant indexing threshold (20000)...")
        qclient.update_collection(
            collection_name="mtg_cards",
            optimizer_config=models.OptimizersConfigDiff(indexing_threshold=20000)
        )

if __name__ == "__main__":
    ingest_cards_to_qdrant(JSONL_PATH)
