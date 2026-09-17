import unittest
from unittest.mock import patch, MagicMock

from config.settings import Settings
from ingestion.runner import IngestionRunner


class TestIngestionRunner(unittest.TestCase):
    """Unit tests for IngestionRunner."""

    @patch("ingestion.runner.QdrantServiceManager")
    @patch("ingestion.runner.QdrantVectorStore")
    @patch("ingestion.runner.FastEmbedProvider")
    @patch("ingestion.runner.IngestionTimer")
    @patch("ingestion.runner.RulesIngestionPipeline")
    def test_run_rules(
        self,
        mock_pipeline_cls,
        mock_timer_cls,
        mock_embedding_cls,
        mock_vectorstore_cls,
        mock_service_manager_cls,
    ) -> None:
        mock_service_manager = MagicMock()
        mock_service_manager_cls.return_value = mock_service_manager

        mock_pipeline = MagicMock()
        mock_pipeline_cls.return_value = mock_pipeline

        settings = Settings()
        runner = IngestionRunner(settings=settings)
        runner.run_rules(force=True)

        mock_service_manager.ensure_running.assert_called_once()
        mock_vectorstore_cls.assert_called_once_with(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
            collection_name=settings.qdrant_collection_rules,
        )
        mock_embedding_cls.assert_called_once_with(model_name=settings.embedding_model_name)
        mock_pipeline_cls.assert_called_once()
        mock_pipeline.run.assert_called_once_with(force_recreate=True)


if __name__ == "__main__":
    unittest.main()
