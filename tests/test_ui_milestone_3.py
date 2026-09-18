import unittest
from unittest.mock import MagicMock, patch
from config.settings import Settings
from ui.controller import LexiGrimSession
from ui.widget import PluggableWidget
from ui.cli.widgets.card_view import CardDetailWidget
from ui.cli.widgets.deck_view import DeckListWidget
from ui.cli.app import InteractiveCLIShell

class TestMilestone3PluggableWidgetsAndAI(unittest.TestCase):
    def test_pluggable_widget_abc(self):
        # Verify ABC behavior
        with self.assertRaises(TypeError):
            PluggableWidget()

    def test_card_detail_widget(self):
        widget = CardDetailWidget()
        card_data = {
            "name": "Counterspell",
            "mana_cost": "U U",
            "type_line": "Instant",
            "set": "lea",
            "rarity": "uncommon",
            "oracle_text": "Counter target spell.",
            "flavor_text": "Let's fizzle.",
            "power": None,
            "toughness": None
        }
        widget.update(card_data)
        tokens = widget.render(80, 20)
        self.assertTrue(len(tokens) > 0)
        text_content = "".join(t[1] for t in tokens)
        self.assertIn("Counterspell", text_content)
        self.assertIn("U U", text_content)
        self.assertIn("Counter target spell.", text_content)
        self.assertIn("Let's fizzle.", text_content)

    def test_deck_list_widget(self):
        widget = DeckListWidget()
        deck_data = {
            "name": "Blue Tempo",
            "mainboard": [
                {"count": 4, "name": "Counterspell", "type": "Instant"},
                {"count": 20, "name": "Island", "type": "Land"}
            ],
            "sideboard": [
                {"count": 2, "name": "Negate", "type": "Instant"}
            ]
        }
        widget.update(deck_data)
        tokens = widget.render(80, 20)
        text_content = "".join(t[1] for t in tokens)
        self.assertIn("Blue Tempo", text_content)
        self.assertIn("4x Counterspell", text_content)
        self.assertIn("20x Island", text_content)
        self.assertIn("2x Negate", text_content)

    def test_ai_chat_streaming_middleware(self):
        mock_engine = MagicMock()
        settings = Settings()
        session = LexiGrimSession(mock_engine, settings)

        prompt = "How do layers work in MTG?"
        chunks = list(session.stream_ai_chat_response(prompt))
        self.assertTrue(len(chunks) > 0)
        full_response = "".join(chunks)
        self.assertIn("LexiGrim AI Assistant", full_response)
        self.assertEqual(len(session.chat_history), 2)
        self.assertEqual(session.chat_history[0]["role"], "user")
        self.assertEqual(session.chat_history[0]["content"], prompt)
        self.assertEqual(session.chat_history[1]["role"], "assistant")

    @patch("ui.cli.app.Application")
    def test_cli_shell_commands_ai_card_deck(self, mock_app_cls):
        mock_engine = MagicMock()
        mock_hit = MagicMock()
        mock_hit.id = "card-1"
        mock_hit.score = 0.99
        mock_hit.payload = {
            "name": "Lightning Bolt",
            "mana_cost": "R",
            "type_line": "Instant",
            "set": "lea",
            "rarity": "common",
            "oracle_text": "Deals 3 damage."
        }
        mock_engine.vector_search.return_value = [mock_hit]

        settings = Settings()
        session = LexiGrimSession(mock_engine, settings)
        shell = InteractiveCLIShell(session)

        # Populate search results
        results = session.execute_search("lightning bolt")
        shell.last_results = results

        # Test /card command simulation via buffer / handling
        mock_buffer = MagicMock()
        mock_buffer.text = "/card 1"
        shell.handle_user_input(mock_buffer)
        self.assertIn("Card Detail Widget", shell.scroll_output.text)

        # Test /deck command simulation
        mock_buffer.text = "/deck"
        shell.handle_user_input(mock_buffer)
        self.assertIn("Deck View Widget", shell.scroll_output.text)

        # Test /ai command simulation
        mock_buffer.text = "/ai Explain rules"
        shell.handle_user_input(mock_buffer)
        self.assertIn("LexiGrim AI Assistant", shell.scroll_output.text)

if __name__ == "__main__":
    unittest.main()
