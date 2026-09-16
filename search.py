import sys
import ollama
from qdrant_client import QdrantClient, models
from qdrant_manager import ensure_qdrant_running

# Automatically handles database initialization/state check
ensure_qdrant_running()

MODEL_NAME = "nomic-embed-text"

# Connect to your local running Qdrant .exe
qclient = QdrantClient(host="localhost", port=6333)

def vector_search(query_text: str, limit: int = 5, query_filter: models.Filter = None):
    """Embeds the query text using Ollama and retrieves the top matches from Qdrant."""
    
    # 1. Nomic requires the 'search_query:' prefix for lookups
    prefixed_query = f"search_query: {query_text}"
    
    try:
        # 2. Generate the embedding vector via local Ollama server
        response = ollama.embeddings(model=MODEL_NAME, prompt=prefixed_query)
        query_vector = response["embedding"]
    except Exception as e:
        print(f"Error generating embedding via Ollama: {e}")
        print("Make sure your Ollama server is running and the model is pulled.")
        return

    # 3. Query Qdrant
    results = qclient.search(
        collection_name="mtg_cards",
        query_vector=query_vector,
        query_filter=query_filter,  # Applies fast index-based pre-filtering if provided
        limit=limit
    )
    
    # 4. Print structured results nicely
    print(f"\n==================================================")
    print(f"🔍 Top {limit} Matches for: '{query_text}'")
    print(f"==================================================")
    
    if not results:
        print("No cards matched the given search and filter criteria.")
        return

    for i, hit in enumerate(results, 1):
        payload = hit.payload
        name = payload.get("name", "Unknown")
        mana_cost = payload.get("mana_cost", "N/A")
        type_line = payload.get("type_line", "N/A")
        
        # Pull text safely (handling double-faced cards gracefully if needed)
        oracle_text = payload.get("oracle_text", "")
        if not oracle_text and "card_faces" in payload:
            oracle_text = " // ".join([face.get("oracle_text", "") for face in payload["card_faces"]])

        print(f"\n{i}. {name} ({mana_cost})  [Score: {hit.score:.4f}]")
        print(f"   Type: {type_line}")
        print(f"   Text: {oracle_text.replace('\n', ' ')}")
    print(f"==================================================\n")


if __name__ == "__main__":
    # Test 1: Pure Semantic Search (Concept matching)
    vector_search("whenever you draw a card put a counter on this creature", limit=3)
    
    # Test 2: Semantic Search + Strict Payload Filter
    # Let's look for "destroy target creature" cards, but force it to look ONLY inside Blue cards
    # (Historically Blue doesn't do this, so it should find weird or color-shifted exceptions)
    blue_only_filter = models.Filter(
        must=[
            models.FieldCondition(
                key="colors",
                match=models.MatchValue(value="U") # "U" is Magic's standard shorthand for Blue
            )
        ]
    )
    
    vector_search("destroy target creature", limit=3, query_filter=blue_only_filter)
