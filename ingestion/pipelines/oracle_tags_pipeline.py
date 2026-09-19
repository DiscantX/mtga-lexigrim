import logging
from typing import Optional
from config.settings import Settings, settings as default_settings
from core.timer import IngestionTimer
from embeddings.base import BaseEmbeddingService
from vectorstores.base import BaseVectorStore

logger = logging.getLogger(__name__)


class OracleTagsIngestionPipeline:
    """Pipeline stub for ingesting and associating Scryfall Oracle Tags.

    NOTE: Full semantic tag ingestion is deferred. This stub provides an interface no-op.
    """

    def __init__(
        self,
        vector_store: Optional[BaseVectorStore] = None,
        embedding_service: Optional[BaseEmbeddingService] = None,
        timer: Optional[IngestionTimer] = None,
        settings: Optional[Settings] = None,
    ) -> None:
        self.vector_store = vector_store
        self.embedding_service = embedding_service
        self.timer = timer or IngestionTimer()
        self.settings = settings or default_settings

    def run(self, file_path: str, force_recreate: bool = False) -> None:
        """No-op execution for Oracle Tags ingestion stub."""
        logger.info(f"OracleTagsIngestionPipeline: Oracle Tags ingestion is currently deferred. Skipping file: {file_path}")
        # TODO: Implement Oracle Tags parsing and Qdrant payload enrichment
        pass
