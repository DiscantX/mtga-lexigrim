import unittest
from unittest.mock import MagicMock
from config.settings import Settings
from ui.controller import LexiGrimSession

class TestLexiGrimSession(unittest.TestCase):
    def test_session_initialization_and_search(self):
        mock_engine = MagicMock()
        mock_hit = MagicMock()
        mock_hit.id = "card-123"
        mock_hit.score = 0.95
        mock_hit.payload = {
            "name": "Lightning Bolt",
            "mana_cost": "R",
            "type_line": "Instant",
            "set": "lea",
            "rarity": "common",
            "oracle_text": "Lightning Bolt deals 3 damage to any target."
        }
        mock_engine.vector_search.return_value = [mock_hit]

        settings = Settings()
        session = LexiGrimSession(mock_engine, settings)

        self.assertEqual(session.last_candidates, [])
        self.assertFalse(session.deduplicate_oracle)

        results = session.execute_search("lightning bolt")

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "Lightning Bolt")
        self.assertEqual(results[0]["id"], "card-123")
        self.assertEqual(results[0]["score"], 0.95)
        self.assertEqual(session.last_candidates, ["card-123"])

        mock_engine.vector_search.assert_called_once()

if __name__ == "__main__":
    unittest.main()
