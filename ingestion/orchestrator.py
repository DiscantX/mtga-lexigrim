import os
import glob
import logging
from typing import Optional, Callable, Dict, Any

from config.settings import Settings, settings as default_settings
from core.timer import IngestionTimer
from embeddings.base import BaseEmbeddingService
from vectorstores.base import BaseVectorStore
from ingestion.pipeline import IngestionPipeline
from ingestion.pipelines.rules_pipeline import RulesIngestionPipeline
from ingestion.pipelines.rulings_pipeline import RulingsIngestionPipeline
from ingestion.pipelines.strategy_pipeline import StrategyIngestionPipeline
from ingestion.pipelines.oracle_tags_pipeline import OracleTagsIngestionPipeline

logger = logging.getLogger(__name__)

class IngestionOrchestrator:
    """Unified ingestion orchestrator responsible for auto-detecting corpus type and executing appropriate pipelines."""

    def __init__(
        self,
        vector_store: BaseVectorStore,
        embedding_service: BaseEmbeddingService,
        timer: Optional[IngestionTimer] = None,
        settings: Optional[Settings] = None,
        progress_callback: Optional[Callable[[float, str, str], None]] = None,
    ) -> None:
        self.vector_store = vector_store
        self.embedding_service = embedding_service
        self.timer = timer or IngestionTimer()
        self.settings = settings or default_settings
        self.progress_callback = progress_callback

    def detect_and_run(self, path: str, force: bool = False) -> None:
        """Inspect given path and route to the correct ingestion pipeline."""
        if not path or not os.path.exists(path):
            raise FileNotFoundError(f"Ingestion path not found: {path}")

        path_lower = path.lower()
        
        if os.path.isdir(path_lower):
            logger.info(f"Detected strategy directory at '{path}'. Running StrategyIngestionPipeline...")
            if self.progress_callback:
                self.progress_callback(10.0, "Running", f"Ingesting strategy articles from {path}")
            pipeline = StrategyIngestionPipeline(
                vector_store=self.vector_store,
                embedding_service=self.embedding_service,
                timer=self.timer,
                settings=self.settings
            )
            pipeline.run(corpus_path=path)
            if self.progress_callback:
                self.progress_callback(100.0, "Idle", "Strategy ingestion complete.")
            return

        if "compruges" in path_lower or "rules" in path_lower or path_lower.endswith(".txt"):
            logger.info(f"Detected comprehensive rules file at '{path}'. Running RulesIngestionPipeline...")
            if self.progress_callback:
                self.progress_callback(10.0, "Running", f"Ingesting rules from {path}")
            pipeline = RulesIngestionPipeline(
                vector_store=self.vector_store,
                embedding_service=self.embedding_service,
                timer=self.timer,
                settings=self.settings
            )
            pipeline.run(force_recreate=force)
            if self.progress_callback:
                self.progress_callback(100.0, "Idle", "Rules ingestion complete.")
            return

        if "rulings" in path_lower:
            logger.info(f"Detected card rulings file at '{path}'. Running RulingsIngestionPipeline...")
            if self.progress_callback:
                self.progress_callback(10.0, "Running", f"Ingesting rulings from {path}")
            pipeline = RulingsIngestionPipeline(
                vector_store=self.vector_store,
                embedding_service=self.embedding_service,
                timer=self.timer,
                settings=self.settings
            )
            pipeline.run(rulings_path=path, force_recreate=force)
            if self.progress_callback:
                self.progress_callback(100.0, "Idle", "Rulings ingestion complete.")
            return

        if "oracle-tags" in path_lower or "oracle_tags" in path_lower:
            logger.info(f"Detected oracle tags file at '{path}'. Running OracleTagsIngestionPipeline...")
            if self.progress_callback:
                self.progress_callback(10.0, "Running", f"Ingesting oracle tags from {path}")
            pipeline = OracleTagsIngestionPipeline(
                vector_store=self.vector_store,
                embedding_service=self.embedding_service,
                timer=self.timer,
                settings=self.settings
            )
            pipeline.run(file_path=path, force_recreate=force)
            if self.progress_callback:
                self.progress_callback(100.0, "Idle", "Oracle tags ingestion complete.")
            return

        # Default fallback: Card corpus jsonl
        logger.info(f"Detected card corpus file at '{path}'. Running IngestionPipeline...")
        if self.progress_callback:
            self.progress_callback(10.0, "Running", f"Ingesting card corpus from {path}")
        pipeline = IngestionPipeline(
            vector_store=self.vector_store,
            embedding_service=self.embedding_service,
            timer=self.timer,
            settings=self.settings
        )
        pipeline.run(file_path=path)
        if self.progress_callback:
            self.progress_callback(100.0, "Idle", "Card corpus ingestion complete.")

    def run_all(self, corpus_dir: str = "corpus", force: bool = False) -> None:
        """Scan corpus directory and automatically discover and run all available corpora in dependency order."""
        logger.info(f"Starting automatic discovery and ingestion across '{corpus_dir}'...")
        
        if not os.path.exists(corpus_dir):
            raise FileNotFoundError(f"Corpus directory not found: {corpus_dir}")

        # 1. Rules files
        rules_files = glob.glob(os.path.join(corpus_dir, "*CompRules*.txt")) + glob.glob(os.path.join(corpus_dir, "rules", "*.txt"))
        for rf in rules_files:
            logger.info(f"Auto-discovered rules file: {rf}")
            self.detect_and_run(rf, force=force)

        # 2. Card corpus files (.jsonl excluding rulings and oracle-tags)
        jsonl_files = [f for f in glob.glob(os.path.join(corpus_dir, "*.jsonl")) if "rulings" not in f.lower() and "oracle-tags" not in f.lower() and "oracle_tags" not in f.lower()]
        for jf in jsonl_files:
            logger.info(f"Auto-discovered card corpus file: {jf}")
            self.detect_and_run(jf, force=force)

        # 3. Rulings files
        rulings_files = glob.glob(os.path.join(corpus_dir, "*rulings*.jsonl"))
        for rlf in rulings_files:
            logger.info(f"Auto-discovered rulings file: {rlf}")
            self.detect_and_run(rlf, force=force)

        # 4. Oracle tags files
        tag_files = glob.glob(os.path.join(corpus_dir, "*oracle-tags*.jsonl")) + glob.glob(os.path.join(corpus_dir, "*oracle_tags*.jsonl"))
        for tf in tag_files:
            logger.info(f"Auto-discovered oracle tags file: {tf}")
            self.detect_and_run(tf, force=force)

        # 5. Strategy directory
        strategy_dir = os.path.join(corpus_dir, "strategy")
        if os.path.exists(strategy_dir) and os.path.isdir(strategy_dir):
            logger.info(f"Auto-discovered strategy directory: {strategy_dir}")
            self.detect_and_run(strategy_dir, force=force)

        logger.info("Automatic full-corpus ingestion completed successfully.")
