from card_model import Card
from ingest import ingest_cards_to_qdrant
import json
import sys

JSONL_PATH = 'corpus/default-cards-20260915210531.jsonl'

def main():
    try:
        ingest_cards_to_qdrant(JSONL_PATH)
    except KeyboardInterrupt:
        print("\n[!] Exiting safely...")
        sys.exit(0)

# Usage Example
if __name__ == "__main__":
    main()