import logging
from typing import Optional

from config.settings import Settings, settings as default_settings
from core.timer import IngestionTimer
from embeddings.fastembed_provider import FastEmbedProvider
from ingestion.pipelines.rules_pipeline import RulesIngestionPipeline
from vectorstores.qdrant import QdrantVectorStore
from vectorstores.service_manager import QdrantServiceManager

logger = logging.getLogger(__name__)


class IngestionRunner:
    """Runner class encapsulating initialization and execution of MTG Rules ingestion."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or default_settings

    def run_rules(self, force: bool = False) -> None:
        """Execute the rules ingestion flow: service check, vector store init, embedding setup, and pipeline run."""
        logger.info("Starting MTG Rules ingestion runner...")

        # 1. Qdrant service check
        service_manager = QdrantServiceManager(
            host=self.settings.qdrant_host, port=self.settings.qdrant_port
        )
        try:
            service_manager.ensure_running()
        except Exception as e:
            logger.warning(f"Could not verify Qdrant service manager startup: {e}")

        # 2. Vector store initialization for mtg_rules
        vector_store = QdrantVectorStore(
            host=self.settings.qdrant_host,
            port=self.settings.qdrant_port,
            collection_name=self.settings.qdrant_collection_rules,
        )

        # 3. Embedding service setup
        embedding_service = FastEmbedProvider(model_name=self.settings.embedding_model_name)

        # 4. Timer setup
        timer = IngestionTimer()

        # 5. Run RulesIngestionPipeline
        pipeline = RulesIngestionPipeline(
            vector_store=vector_store,
            embedding_service=embedding_service,
            timer=timer,
            settings=self.settings,
        )

        pipeline.run(force_recreate=force)
        logger.info("MTG Rules ingestion completed successfully.")
