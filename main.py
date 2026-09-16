print("Importing modules...")

import argparse
import sys
from ingest import ingest_cards_to_qdrant
from search import run_interactive_search

JSONL_PATH = 'corpus/default-cards-20260915210531.jsonl'

def main():
    print("Parsing args...")
    parser = argparse.ArgumentParser(description="MTG Expert: Ingestion & Interactive Search CLI")
    parser.add_argument("-s", "--search", action="store_true", help="Activate interactive search and narrowing mode")
    parser.add_argument("--results", "--r", type=int, default=3, help="Number of results to display in search mode (default: 3)")
    
    args = parser.parse_args()

    try:
        if args.search:
            print("Opening interactive search...")
            run_interactive_search(display_limit=args.results)
        else:
            print("Starting data ingestion...")
            ingest_cards_to_qdrant(JSONL_PATH)
    except KeyboardInterrupt:
        print("\n[!] Exiting safely...")
        sys.exit(0)

if __name__ == "__main__":
    main()
