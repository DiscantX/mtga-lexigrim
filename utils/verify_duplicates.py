import sys
from collections import defaultdict
from qdrant_client.http import models
from config.settings import settings
from core.streaming import JsonlStreamReader
from vectorstores.qdrant import QdrantVectorStore

def run_sanity_check(target_names=None):
    if target_names is None:
        target_names = {"Lightning Bolt", "Counterspell", "Negate", "Opt", "Sovereign Okinec Ahau"}

    corpus_path = settings.data_corpus_path
    print(f"Loading corpus from: {corpus_path}")
    print(f"Target cards to inspect: {target_names}\n")

    # Pass 1: Scan corpus to gather stats for target cards
    corpus_stats = defaultdict(lambda: {"printings": []})
    
    stream_reader = JsonlStreamReader(corpus_path)
    total_cards = 0

    for card_obj, _ in stream_reader.stream():
        total_cards += 1
        name = card_obj.get("name")
        if name in target_names:
            card_id = card_obj.get("id")
            set_code = card_obj.get("set")
            collector_num = card_obj.get("collector_number")
            
            corpus_stats[name]["printings"].append({
                "id": card_id,
                "set": set_code,
                "collector_number": collector_num
            })

    print(f"Scanned {total_cards} total records in JSONL corpus.\n")

    # Initialize Qdrant vector store
    vector_store = QdrantVectorStore()
    
    print("--- Sanity Check Results ---")
    for name, data in corpus_stats.items():
        corpus_count = len(data["printings"])
        
        # Query Qdrant for points with this name
        db_points = []
        try:
            offset = None
            f = models.Filter(
                must=[
                    models.FieldCondition(
                        key="name",
                        match=models.MatchValue(value=name)
                    )
                ]
            )
            while True:
                records, offset = vector_store.client.scroll(
                    collection_name=vector_store.collection_name,
                    scroll_filter=f,
                    with_payload=True,
                    with_vectors=False,
                    limit=10000,
                    offset=offset
                )
                db_points.extend(records)
                if offset is None:
                    break
        except Exception as e:
            print(f"Error querying Qdrant for {name}: {e}")

        db_count = len(db_points)
        match_status = "MATCH" if corpus_count == db_count else "MISMATCH"

        print(f"Card: '{name}'")
        print(f"  Corpus Printing Count : {corpus_count}")
        print(f"  Qdrant Stored Count   : {db_count} [{match_status}]")
        print(f"  Sample Printings (Corpus): {[str(p['set']) + '#' + str(p['collector_number']) for p in data['printings'][:5]]}")
        print(f"  Sample Printings (Qdrant): {[str(r.payload.get('set')) + '#' + str(r.payload.get('collector_number')) for r in db_points[:5]]}")
        print("-" * 60)

if __name__ == "__main__":
    run_sanity_check()
