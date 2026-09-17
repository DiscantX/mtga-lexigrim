from typing import Any, Optional, List
from search.engine import CardSearchEngine

class InteractiveSearchCLI:
    """Interactive search CLI and REPL supporting cascading narrowing and oracle deduplication."""

    def __init__(self, search_engine: CardSearchEngine, default_limit: int = 3, deduplicate_oracle: bool = False):
        self.search_engine = search_engine
        self.default_limit = default_limit
        self.deduplicate_oracle = deduplicate_oracle
        self.last_candidate_ids: Optional[List[str]] = None

    def print_results(self, results: List[Any], query_text: str, limit: Optional[int] = None) -> None:
        """Prints structured search results nicely."""
        show_limit = limit if limit is not None else self.default_limit
        display_results = results[:show_limit]
        
        dedupe_status = "ON" if self.deduplicate_oracle else "OFF"
        print(f"\n==================================================")
        print(f"[Search] Top {len(display_results)} (showing {len(display_results)} of {len(results)} matches) for: '{query_text}' [Dedupe: {dedupe_status}]")
        print(f"==================================================")
        
        if not results:
            print("No cards matched the given search and filter criteria.")
            return

        for i, hit in enumerate(display_results, 1):
            payload = hit.payload
            name = payload.get("name", "Unknown")
            mana_cost = payload.get("mana_cost", "N/A")
            type_line = payload.get("type_line", "N/A")
            set_code = payload.get("set", "N/A").upper()
            rarity = payload.get("rarity", "N/A").upper()
            
            oracle_text = payload.get("oracle_text", "")
            if not oracle_text and "card_faces" in payload and payload["card_faces"]:
                oracle_text = " // ".join([face.get("oracle_text", "") for face in payload["card_faces"] if face.get("oracle_text")])

            score_str = f"{hit.score:.4f}" if hasattr(hit, "score") and hit.score is not None else "N/A"
            print(f"\n{i}. {name} ({mana_cost})  [Set: {set_code} | Rarity: {rarity} | Score: {score_str}]")
            print(f"   Type: {type_line}")
            print(f"   Text: {oracle_text.replace('\n', ' ')}")
        print(f"==================================================\n")

    def run(self) -> None:
        """Runs the interactive search REPL loop."""
        print("\n==================================================")
        print("🔮 LexiGrim: Interactive Card Search & Narrowing Mode")
        print("Commands:")
        print("  - Type any query to start a fresh search.")
        print("  - Type '/narrow <query>' or '/n <query>' to search within current results.")
        print("  - Type '/dedupe' to toggle oracle duplicate filtering ON/OFF.")
        print("  - Type ':quit', ':q', or 'exit' to exit.")
        print(f"  [Current Deduplication State: {'ON' if self.deduplicate_oracle else 'OFF'} | Results Limit: {self.default_limit}]")
        print("==================================================\n")

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

            if user_input.lower() == "/dedupe":
                self.deduplicate_oracle = not self.deduplicate_oracle
                print(f"🔮 Oracle deduplication toggled to: {'ON' if self.deduplicate_oracle else 'OFF'}\n")
                continue

            is_narrow = False
            query_to_run = user_input

            if user_input.startswith("/narrow ") or user_input.startswith("/n "):
                is_narrow = True
                parts = user_input.split(" ", 1)
                if len(parts) > 1:
                    query_to_run = parts[1].strip()
                else:
                    query_to_run = ""
                
                if not self.last_candidate_ids:
                    print("⚠️ No active result set to narrow. Performing fresh search instead.")
                    is_narrow = False

            if is_narrow:
                print(f"Narrowing within {len(self.last_candidate_ids)} previous candidate cards (Dedupe: {'ON' if self.deduplicate_oracle else 'OFF'})...")
                results = self.search_engine.vector_search(
                    query_to_run,
                    limit=self.default_limit,
                    candidate_ids=self.last_candidate_ids,
                    deduplicate_oracle=self.deduplicate_oracle
                )
            else:
                results = self.search_engine.vector_search(
                    query_to_run,
                    limit=self.default_limit,
                    deduplicate_oracle=self.deduplicate_oracle
                )
                # Carry full candidate set IDs for subsequent narrowing
                self.last_candidate_ids = [str(hit.id) for hit in results]

            self.print_results(results, query_to_run)
