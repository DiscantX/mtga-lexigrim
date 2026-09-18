import os
import tempfile
import time
import unittest
from unittest.mock import MagicMock, patch

from config.settings import Settings
from core.timer import IngestionTimer
from embeddings.base import BaseEmbeddingService
from ingestion.pipeline import IngestionPipeline
from vectorstores.base import BaseVectorStore
from ui.controller import LexiGrimSession
from ui.cli.app import InteractiveCLIShell


class MockVectorStore(BaseVectorStore):
    def __init__(self, existing_ids=None):
        self.existing_ids = existing_ids or set()
        self.upserted_points = []
        self.bulk_mode_calls = []

    def initialize_schema(self) -> None:
        pass

    def upsert_batch(self, ids, vectors, payloads) -> None:
        self.upserted_points.append((ids, vectors, payloads))
        for cid in ids:
            self.existing_ids.add(cid)

    def search(self, query_vector, limit=10, filters=None, candidate_ids=None):
        return []

    def get_existing_ids(self):
        return self.existing_ids

    def set_bulk_mode(self, enabled: bool) -> None:
        self.bulk_mode_calls.append(enabled)


class MockEmbeddingService(BaseEmbeddingService):
    @property
    def dimension(self) -> int:
        return 4

    def embed_documents(self, texts):
        return [[0.1, 0.2, 0.3, 0.4] for _ in texts]

    def embed_query(self, query):
        return [0.1, 0.2, 0.3, 0.4]


class TestMilestone2ConcurrentIngestion(unittest.TestCase):
    def setUp(self):
        self.temp_file = tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8")
        self.temp_file.write('{"id": "card_1", "name": "Lightning Bolt", "mana_cost": "{R}", "type_line": "Instant", "oracle_text": "Deal 3 damage."}\n')
        self.temp_file.write('{"id": "card_2", "name": "Ancestral Recall", "mana_cost": "{U}", "type_line": "Instant", "oracle_text": "Draw 3 cards."}\n')
        self.temp_file.close()

    def tearDown(self):
        time.sleep(0.3)
        if os.path.exists(self.temp_file.name):
            try:
                os.unlink(self.temp_file.name)
            except PermissionError:
                pass

    @patch("ingestion.pipeline.QdrantServiceManager")
    def test_pipeline_progress_callback(self, mock_service_manager_cls):
        mock_manager = mock_service_manager_cls.return_value
        mock_manager.ensure_running.return_value = None

        vector_store = MockVectorStore()
        embedding_service = MockEmbeddingService()
        timer = IngestionTimer()
        settings = Settings()
        settings.embedding_batch_size = 1
        settings.upsert_batch_size = 1

        callbacks_received = []
        def progress_cb(pct, speed, msg):
            callbacks_received.append((pct, speed, msg))

        pipeline = IngestionPipeline(
            vector_store=vector_store,
            embedding_service=embedding_service,
            timer=timer,
            settings=settings,
            progress_callback=progress_cb
        )

        pipeline.run(self.temp_file.name)
        self.assertTrue(len(callbacks_received) > 0)
        self.assertEqual(callbacks_received[-1][0], 100.0)

    @patch("ingestion.pipeline.QdrantServiceManager")
    def test_lexigrim_session_background_ingestion(self, mock_service_manager_cls):
        mock_manager = mock_service_manager_cls.return_value
        mock_manager.ensure_running.return_value = None

        mock_engine = MagicMock()
        mock_engine.vector_store = MockVectorStore()
        mock_engine.embedding_service = MockEmbeddingService()

        settings = Settings()
        session = LexiGrimSession(mock_engine, settings)

        self.assertFalse(session.is_ingesting)
        session.trigger_background_ingestion(self.temp_file.name)

        time.sleep(0.5)
        updates = []
        while not session.ingestion_progress_queue.empty():
            updates.append(session.ingestion_progress_queue.get_nowait())

        self.assertTrue(len(updates) > 0)

    @patch("ui.cli.app.Application")
    @patch("ingestion.pipeline.QdrantServiceManager")
    def test_interactive_cli_shell_ingest_command(self, mock_service_manager_cls, mock_app_cls):
        mock_manager = mock_service_manager_cls.return_value
        mock_manager.ensure_running.return_value = None

        mock_engine = MagicMock()
        mock_engine.vector_store = MockVectorStore()
        mock_engine.embedding_service = MockEmbeddingService()

        settings = Settings()
        session = LexiGrimSession(mock_engine, settings)
        shell = InteractiveCLIShell(session)

        mock_buffer = MagicMock()
        mock_buffer.text = f"/ingest {self.temp_file.name}"

        shell.handle_user_input(mock_buffer)
        self.assertTrue(session.is_ingesting or session.ingestion_progress > 0)


if __name__ == "__main__":
    unittest.main()
