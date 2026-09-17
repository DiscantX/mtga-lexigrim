import unittest
from unittest.mock import MagicMock, patch
from vectorstores.qdrant import QdrantVectorStore
from config.settings import settings

class TestQdrantMultiCollection(unittest.TestCase):
    @patch("vectorstores.qdrant.QdrantClient")
    def test_default_collection_init(self, mock_client_cls):
        store = QdrantVectorStore()
        self.assertEqual(store.collection_name, settings.qdrant_collection_cards)

    @patch("vectorstores.qdrant.QdrantClient")
    def test_explicit_collection_init(self, mock_client_cls):
        store = QdrantVectorStore(collection_name="mtg_rules")
        self.assertEqual(store.collection_name, "mtg_rules")

    @patch("vectorstores.qdrant.QdrantClient")
    def test_initialize_schema_override(self, mock_client_cls):
        mock_client = mock_client_cls.return_value
        mock_collections = MagicMock()
        mock_collections.collections = []
        mock_client.get_collections.return_value = mock_collections

        store = QdrantVectorStore(collection_name="mtg_cards")
        store.initialize_schema(collection_name="mtg_rulings")

        mock_client.create_collection.assert_called_once()
        args, kwargs = mock_client.create_collection.call_args
        self.assertEqual(kwargs.get("collection_name"), "mtg_rulings")

    @patch("vectorstores.qdrant.QdrantClient")
    def test_set_bulk_mode_override(self, mock_client_cls):
        mock_client = mock_client_cls.return_value
        store = QdrantVectorStore(collection_name="mtg_cards")
        store.set_bulk_mode(True, collection_name="mtg_decks")

        mock_client.update_collection.assert_called_once()
        args, kwargs = mock_client.update_collection.call_args
        self.assertEqual(kwargs.get("collection_name"), "mtg_decks")

    @patch("vectorstores.qdrant.QdrantClient")
    def test_upsert_batch_override(self, mock_client_cls):
        mock_client = mock_client_cls.return_value
        store = QdrantVectorStore(collection_name="mtg_cards")
        store.upsert_batch(["id1"], [[0.1]*768], [{"name": "Card"}], collection_name="mtg_strategy")

        mock_client.upsert.assert_called_once()
        args, kwargs = mock_client.upsert.call_args
        self.assertEqual(kwargs.get("collection_name"), "mtg_strategy")

    @patch("vectorstores.qdrant.QdrantClient")
    def test_get_existing_ids_override(self, mock_client_cls):
        mock_client = mock_client_cls.return_value
        mock_client.scroll.return_value = ([], None)
        store = QdrantVectorStore(collection_name="mtg_cards")
        store.get_existing_ids(collection_name="mtg_rules")

        mock_client.scroll.assert_called_once()
        args, kwargs = mock_client.scroll.call_args
        self.assertEqual(kwargs.get("collection_name"), "mtg_rules")

    @patch("vectorstores.qdrant.QdrantClient")
    def test_search_override(self, mock_client_cls):
        mock_client = mock_client_cls.return_value
        mock_response = MagicMock()
        mock_response.points = []
        mock_client.query_points.return_value = mock_response

        store = QdrantVectorStore(collection_name="mtg_cards")
        store.search([0.1]*768, limit=5, collection_name="mtg_rulings")

        mock_client.query_points.assert_called_once()
        args, kwargs = mock_client.query_points.call_args
        self.assertEqual(kwargs.get("collection_name"), "mtg_rulings")

if __name__ == "__main__":
    unittest.main()
