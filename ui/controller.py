import queue
import threading
from typing import Any, Optional, List, Dict
from search.engine import CardSearchEngine
from config.settings import Settings
from ingestion.pipeline import IngestionPipeline
from core.timer import IngestionTimer

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
        self.is_ingesting: bool = False
        self.ingestion_progress: float = 0.0
        self.ingestion_speed: str = "0.0 cards/s"
        self.ingestion_message: str = "Idle"

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

    def trigger_background_ingestion(self, corpus_path: str, rulings_file_path: Optional[str] = None) -> None:
        """Launch ingestion on a separate thread, piping progress updates to ui-safe queue."""
        if self._active_ingestion_thread and self._active_ingestion_thread.is_alive():
            raise RuntimeError("Ingestion is already running!")
            
        self.is_ingesting = True
        self.ingestion_progress = 0.0
        self.ingestion_speed = "0.0 cards/s"
        self.ingestion_message = f"Starting ingestion for {corpus_path}"

        def run_ingestion_thread():
            try:
                def progress_callback(percentage: float, speed: str, msg: str):
                    self.ingestion_progress = percentage
                    self.ingestion_speed = speed
                    self.ingestion_message = msg
                    self.ingestion_progress_queue.put({
                        "type": "progress",
                        "percentage": percentage,
                        "speed": speed,
                        "message": msg
                    })

                pipeline = IngestionPipeline(
                    vector_store=self.search_engine.vector_store,
                    embedding_service=self.search_engine.embedding_service,
                    timer=IngestionTimer(),
                    settings=self.settings,
                    rulings_file_path=rulings_file_path,
                    progress_callback=progress_callback
                )
                pipeline.run(corpus_path)
                self.is_ingesting = False
                self.ingestion_progress = 100.0
                self.ingestion_message = "Ingestion completed successfully."
                self.ingestion_progress_queue.put({
                    "type": "complete",
                    "percentage": 100.0,
                    "speed": "Idle",
                    "message": "Ingestion completed successfully."
                })
            except Exception as e:
                self.is_ingesting = False
                self.ingestion_message = f"Ingestion failed: {e}"
                self.ingestion_progress_queue.put({
                    "type": "error",
                    "percentage": self.ingestion_progress,
                    "speed": "Error",
                    "message": str(e)
                })

        self._active_ingestion_thread = threading.Thread(target=run_ingestion_thread, daemon=True)
        self._active_ingestion_thread.start()

    def stream_ai_chat_response(self, user_prompt: str):
        """Streaming AI chat response generator prepared for Phase 2 Google Gemini integration."""
        self.chat_history.append({"role": "user", "content": user_prompt})
        
        # Simulated intelligent MTG response chunks (ready to be replaced by Gemini client in Phase 2)
        response_simulation = (
            f"🔮 [LexiGrim AI Assistant]: Analyzing query '{user_prompt}' against MTG rules and card database...\n"
            f"Based on current search context and stored embeddings, here is the strategic analysis:\n"
            f"- Relevant cards identified in recent search candidates.\n"
            f"- Consider synergy, mana curve efficiency, and interaction timing.\n"
            f"AI integration middleware ready for Phase 2 LLM provider connection."
        )
        
        # Yield in chunks to simulate token streaming
        chunk_size = 30
        for i in range(0, len(response_simulation), chunk_size):
            chunk = response_simulation[i:i + chunk_size]
            yield chunk
            
        self.chat_history.append({"role": "assistant", "content": response_simulation})
