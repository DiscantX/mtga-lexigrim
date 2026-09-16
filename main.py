from card_model import Card
from ingest import ingest_cards_to_qdrant
import json

JSONL_PATH = 'corpus/default-cards-20260915210531.jsonl'

def main():
    ingest_cards_to_qdrant(JSONL_PATH)

# Usage Example
if __name__ == "__main__":
    main()