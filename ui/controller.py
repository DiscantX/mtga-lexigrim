import queue
import threading
from typing import Any, Optional, List, Dict
from search.engine import CardSearchEngine
from config.settings import Settings

class LexiGrimSession:
    """Agnostic session state controller bridging presentation views to core engines."""
    
    def __init__(self, search_engine: CardSearchEngine, settings: Settings):
        self.search_engine = search_engine
        self.settings = settings
        
        # State management
        self.last_candidates: List[str] = []
        self.chat_history: List[Dict[str, str]] = []
        self.ingestion_progress_queue: queue.Queue = queue.Queue()
        self._active_ingestion_thread: Optional[threading.Thread] = None
        self.deduplicate_oracle: bool = False
        self.default_limit: int = settings.default_display_limit

    def execute_search(self, query: str, narrow: bool = False, deduplicate: Optional[bool] = None) -> List[Dict[str, Any]]:
        """Perform search and update candidate state, returning raw dictionary payloads with metadata."""
        dedupe = deduplicate if deduplicate is not None else self.deduplicate_oracle
        candidates = self.last_candidates if (narrow and self.last_candidates) else None
        
        results = self.search_engine.vector_search(
            query_text=query,
            limit=self.default_limit,
            candidate_ids=candidates,
            deduplicate_oracle=dedupe
        )
        
        self.last_candidates = [str(hit.id) for hit in results]
        
        formatted_results = []
        for hit in results:
            payload = hit.payload or {}
            item = {
                "id": str(hit.id),
                "score": getattr(hit, "score", None),
                "payload": payload,
                "name": payload.get("name", "Unknown"),
                "mana_cost": payload.get("mana_cost", "N/A"),
                "type_line": payload.get("type_line", "N/A"),
                "set": payload.get("set", "N/A"),
                "rarity": payload.get("rarity", "N/A"),
                "oracle_text": payload.get("oracle_text", "")
            }
            formatted_results.append(item)
            
        return formatted_results
