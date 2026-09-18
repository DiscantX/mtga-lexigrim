import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from config.settings import Settings
from core.timer import IngestionTimer
from ingestion.orchestrator import IngestionOrchestrator


class TestIngestionOrchestrator(unittest.TestCase):
    def setUp(self):
        self.settings = Settings()
        self.vector_store = MagicMock()
        self.embedding_service = MagicMock()
        self.timer = IngestionTimer()
        self.orchestrator = IngestionOrchestrator(
            vector_store=self.vector_store,
            embedding_service=self.embedding_service,
            timer=self.timer,
            settings=self.settings
        )

    @patch("ingestion.orchestrator.RulesIngestionPipeline")
    def test_detect_rules_corpus(self, mock_rules_pipeline_cls):
        mock_pipeline = mock_rules_pipeline_cls.return_value
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix="CompRules.txt") as tf:
            tf.write("100.1. Test rule.")
            tf_name = tf.name

        try:
            self.orchestrator.detect_and_run(tf_name, force=True)
            mock_rules_pipeline_cls.assert_called_once()
            mock_pipeline.run.assert_called_once_with(force_recreate=True)
        finally:
            os.unlink(tf_name)

    @patch("ingestion.orchestrator.RulingsIngestionPipeline")
    def test_detect_rulings_corpus(self, mock_rulings_pipeline_cls):
        mock_pipeline = mock_rulings_pipeline_cls.return_value
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix="rulings.jsonl") as tf:
            tf.write('{"oracle_id": "123", "comment": "test ruling"}\n')
            tf_name = tf.name

        try:
            self.orchestrator.detect_and_run(tf_name, force=False)
            mock_rulings_pipeline_cls.assert_called_once()
            mock_pipeline.run.assert_called_once_with(rulings_path=tf_name, force_recreate=False)
        finally:
            os.unlink(tf_name)

    @patch("ingestion.orchestrator.IngestionPipeline")
    def test_detect_card_corpus(self, mock_card_pipeline_cls):
        mock_pipeline = mock_card_pipeline_cls.return_value
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".jsonl") as tf:
            tf.write('{"id": "c1", "name": "Lightning Bolt"}\n')
            tf_name = tf.name

        try:
            self.orchestrator.detect_and_run(tf_name)
            mock_card_pipeline_cls.assert_called_once()
            mock_pipeline.run.assert_called_once_with(file_path=tf_name)
        finally:
            os.unlink(tf_name)
