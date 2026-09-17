import os
import shutil
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class Settings:
    # Corpus Path
    data_corpus_path: str = field(
        default_factory=lambda: os.getenv("DATA_CORPUS_PATH", "corpus/default-cards-20260915210531.jsonl")
    )
    
    # Qdrant Executable & Connection Settings
    qdrant_bin: Optional[str] = field(
        default_factory=lambda: os.getenv("QDRANT_BIN") or shutil.which("qdrant")
    )
    qdrant_host: str = field(
        default_factory=lambda: os.getenv("QDRANT_HOST", "localhost")
    )
    qdrant_port: int = field(
        default_factory=lambda: int(os.getenv("QDRANT_PORT", "6333"))
    )
    qdrant_collection_cards: str = field(
        default_factory=lambda: os.getenv("QDRANT_COLLECTION_CARDS", "mtg_cards")
    )
    qdrant_collection_rules: str = field(
        default_factory=lambda: os.getenv("QDRANT_COLLECTION_RULES", "mtg_rules")
    )
    qdrant_collection_rulings: str = field(
        default_factory=lambda: os.getenv("QDRANT_COLLECTION_RULINGS", "mtg_rulings")
    )
    qdrant_collection_decks: str = field(
        default_factory=lambda: os.getenv("QDRANT_COLLECTION_DECKS", "mtg_decks")
    )
    qdrant_collection_strategy: str = field(
        default_factory=lambda: os.getenv("QDRANT_COLLECTION_STRATEGY", "mtg_strategy")
    )
    qdrant_collection_name: str = field(
        default_factory=lambda: os.getenv("QDRANT_COLLECTION_NAME") or os.getenv("QDRANT_COLLECTION_CARDS", "mtg_cards")
    )
    
    # FastEmbed Settings
    embedding_model_name: str = field(
        default_factory=lambda: os.getenv("EMBEDDING_MODEL_NAME", "nomic-ai/nomic-embed-text-v1.5")
    )
    fe_threads: int = field(
        default_factory=lambda: int(os.getenv("FE_THREADS", "2"))
    )
    
    # Batch & Queue Sizes
    embedding_batch_size: int = 2
    upsert_batch_size: int = 128
    queue_maxsize: int = 1000
    
    # Indexing Thresholds
    qdrant_indexing_threshold: int = 20000
    qdrant_bulk_indexing_threshold: int = 1000000
    
    # Retry & Backoff
    db_retry_attempts: int = 5
    retry_backoff: float = 0.2
    
    # Stream Chunk Size
    stream_chunk_size: int = 65536
    
    # Search Limits
    search_candidate_pool_limit: int = 10000
    default_display_limit: int = 3

# Global settings singleton instance
settings = Settings()
