from typing import Any, Dict, List
from ui.widget import PluggableWidget, FormattedText

class DeckListWidget(PluggableWidget):
    """Pluggable widget for displaying decklists, card counts, and mana curves."""

    def __init__(self):
        super().__init__(title="Deck View")
        self.deck_data: Dict[str, Any] = {
            "name": "Untitled Deck",
            "mainboard": [],
            "sideboard": []
        }

    def update(self, data: Dict[str, Any]) -> None:
        """Receive deck payload data (e.g., name, mainboard list of {'count': int, 'name': str, 'type': str}, etc.)."""
        if data:
            self.deck_data.update(data)

    def render(self, width: int, height: int) -> FormattedText:
        """Render decklist summary into formatted tokens."""
        name = self.deck_data.get("name", "Untitled Deck")
        mainboard: List[Dict[str, Any]] = self.deck_data.get("mainboard", [])
        sideboard: List[Dict[str, Any]] = self.deck_data.get("sideboard", [])

        total_main = sum(item.get("count", 1) for item in mainboard)
        total_side = sum(item.get("count", 1) for item in sideboard)

        tokens: FormattedText = [
            ("class:deck_header", f"=== Deck: {name} (Main: {total_main} | Side: {total_side}) ===\n")
        ]

        if not mainboard:
            tokens.append(("class:deck_muted", "  [No cards in mainboard. Use update() to load decklist.]\n"))
        else:
            tokens.append(("class:deck_subheader", "  Mainboard:\n"))
            for item in mainboard[:15]: # Show top 15 for compactness
                count = item.get("count", 1)
                card_name = item.get("name", "Unknown")
                card_type = item.get("type", "")
                tokens.append(("class:deck_item", f"    {count}x {card_name}"))
                if card_type:
                    tokens.append(("class:deck_item_type", f" [{card_type}]"))
                tokens.append(("class:default", "\n"))
            if len(mainboard) > 15:
                tokens.append(("class:deck_muted", f"    ... and {len(mainboard) - 15} more entries.\n"))

        if sideboard:
            tokens.append(("class:deck_subheader", "  Sideboard:\n"))
            for item in sideboard[:10]:
                count = item.get("count", 1)
                card_name = item.get("name", "Unknown")
                tokens.append(("class:deck_item", f"    {count}x {card_name}\n"))

        return tokens
