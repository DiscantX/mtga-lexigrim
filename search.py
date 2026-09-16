print("Initializing search.py...")

import sys
from fastembed import TextEmbedding
from qdrant_client import QdrantClient, models
from qdrant_manager import ensure_qdrant_running

# Automatically handles database initialization/state check
ensure_qdrant_running()

MODEL_NAME = "nomic-ai/nomic-embed-text-v1.5"

# Connect to your local running Qdrant .exe
qclient = QdrantClient(host="localhost", port=6333)

# Initialize FastEmbed TextEmbedding model
embedding_model = TextEmbedding(model_name=MODEL_NAME)

def vector_search(query_text: str, limit: int = None, query_filter: models.Filter = None, candidate_ids: list[str] = None):
    """Embeds the query text using FastEmbed and retrieves matches from Qdrant.
    Supports cascading candidate_ids filtering for search narrowing without premature truncation.
    """
    
    # 1. Nomic requires the 'search_query:' prefix for lookups
    prefixed_query = f"search_query: {query_text}"
    
    try:
        # 2. Generate the embedding vector via FastEmbed
        query_vector = list(embedding_model.embed([prefixed_query]))[0]
        if hasattr(query_vector, "tolist"):
            query_vector = query_vector.tolist()
        else:
            query_vector = list(query_vector)
    except Exception as e:
        print(f"Error generating embedding via FastEmbed: {e}")
        return []

    # Build filter, incorporating candidate_ids if provided for cascading search narrowing
    active_filter = query_filter
    if candidate_ids is not None:
        id_condition = models.HasIdCondition(has_id=candidate_ids)
        if active_filter is not None:
            if active_filter.must:
                active_filter.must.append(id_condition)
            else:
                active_filter.must = [id_condition]
        else:
            active_filter = models.Filter(must=[id_condition])

    # 3. Query Qdrant (If limit is None, request a large enough or default limit)
    query_limit = limit if limit is not None else 10000
    response = qclient.query_points(
        collection_name="mtg_cards",
        query=query_vector,
        query_filter=active_filter,
        limit=query_limit
    )
    return response.points

def multi_query_fusion(queries: list[str], limit: int = 5):
    """NO-OP / STUB METHOD FOR FUTURE ARCHITECTURE.
    
    Architectural Rationale:
    - Multi-query fusion is designed for simultaneous multi-intent searches (e.g. searching for 
      'creature that draws cards' and 'artifact' at the exact same time and merging results via RRF).
    - For interactive iterative narrowing (searching X, then narrowing to Y), cascading query filtering 
      (sub-search using candidate IDs) is used instead because it strictly preserves all qualifying items 
      ('carrying the decimal') without arbitrary score distortion.
    """
    raise NotImplementedError("Multi-query fusion is stubbed for future architecture.")

def print_results(results, query_text: str, limit: int = 3):
    """Prints structured search results nicely."""
    display_results = results[:limit]
    print(f"\n==================================================")
    print(f"[Search] Top {len(display_results)} (showing {len(display_results)} of {len(results)} matches) for: '{query_text}'")
    print(f"==================================================")
    
    if not results:
        print("No cards matched the given search and filter criteria.")
        return

    for i, hit in enumerate(display_results, 1):
        payload = hit.payload
        name = payload.get("name", "Unknown")
        mana_cost = payload.get("mana_cost", "N/A")
        type_line = payload.get("type_line", "N/A")
        
        oracle_text = payload.get("oracle_text", "")
        if not oracle_text and "card_faces" in payload:
            oracle_text = " // ".join([face.get("oracle_text", "") for face in payload["card_faces"]])

        print(f"\n{i}. {name} ({mana_cost})  [Score: {hit.score:.4f}]")
        print(f"   Type: {type_line}")
        print(f"   Text: {oracle_text.replace('\n', ' ')}")
    print(f"==================================================\n")

def run_interactive_search(display_limit: int = 3):
    """Runs an interactive search session supporting cascading narrowing."""
    print("\n==================================================")
    print("🔮 Interactive MTG Card Search & Narrowing Mode")
    print("Commands:")
    print("  - Type any query to start a fresh search.")
    print("  - Type '/narrow <query>' or '/n <query>' to search within current results.")
    print("  - Type ':quit', ':q', or 'exit' to exit.")
    print("==================================================\n")

    current_candidate_ids = None

    while True:
        try:
            user_input = input("Search> ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting search mode.")
            break

        if not user_input:
            continue

        if user_input.lower() in [":quit", ":q", "exit"]:
            print("Exiting search mode.")
            break

        is_narrow = False
        query_to_run = user_input

        if user_input.startswith("/narrow ") or user_input.startswith("/n "):
            is_narrow = True
            query_to_run = user_input.split(" ", 1)[1].strip()
            if not current_candidate_ids:
                print("⚠️ No active result set to narrow. Performing fresh search instead.")
                is_narrow = False

        if is_narrow:
            print(f"Narrowing within {len(current_candidate_ids)} previous candidate cards...")
            results = vector_search(query_to_run, limit=None, candidate_ids=current_candidate_ids)
        else:
            results = vector_search(query_to_run, limit=None)
            # Carry full candidate set IDs for subsequent narrowing (carrying the decimal)
            current_candidate_ids = [hit.id for hit in results]

        print_results(results, query_to_run, limit=display_limit)


if __name__ == "__main__":
    # Test 1: Pure Semantic Search
    res1 = vector_search("whenever you draw a card put a counter on this creature", limit=3)
    print_results(res1, "whenever you draw a card put a counter on this creature", limit=3)
