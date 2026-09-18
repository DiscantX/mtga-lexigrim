from typing import Any, Dict
from ui.widget import PluggableWidget, FormattedText

class CardDetailWidget(PluggableWidget):
    """Pluggable widget for displaying detailed card information with rich styling tokens."""

    def __init__(self):
        super().__init__(title="Card Details")
        self.card_data: Dict[str, Any] = {}

    def update(self, data: Dict[str, Any]) -> None:
        """Receive card payload data."""
        self.card_data = data or {}

    def render(self, width: int, height: int) -> FormattedText:
        """Render card details into formatted styled tokens."""
        if not self.card_data:
            return [("class:card_muted", "[No card selected for detailed view]")]

        name = self.card_data.get("name", "Unknown Card")
        mana_cost = self.card_data.get("mana_cost", "")
        type_line = self.card_data.get("type_line", "")
        set_code = str(self.card_data.get("set", "")).upper()
        rarity = str(self.card_data.get("rarity", "")).capitalize()
        oracle_text = self.card_data.get("oracle_text", "")
        flavor_text = self.card_data.get("flavor_text", "")
        power = self.card_data.get("power")
        toughness = self.card_data.get("toughness")

        tokens: FormattedText = [
            ("class:card_border", "┌" + "─" * min(width - 2, 76) + "┐\n"),
            ("class:card_header", f" │ "),
            ("class:card_name", f"{name}"),
            ("class:card_mana", f"  {mana_cost}"),
            ("class:card_header", f" | Set: {set_code} ({rarity})\n"),
            ("class:card_border", "├" + "─" * min(width - 2, 76) + "┤\n"),
            ("class:card_type", f" │ Type: {type_line}\n"),
        ]

        if power is not None and toughness is not None:
            tokens.append(("class:card_stats", f" │ P/T: {power}/{toughness}\n"))

        if oracle_text:
            tokens.append(("class:card_divider", " ├" + "─" * (min(width - 4, 74)) + "┤\n"))
            for line in oracle_text.split("\n"):
                tokens.append(("class:card_text", f" │ {line}\n"))

        if flavor_text:
            tokens.append(("class:card_flavor", f" │ <i>\"{flavor_text}\"</i>\n"))

        tokens.append(("class:card_border", "└" + "─" * min(width - 2, 76) + "┘\n"))
        return tokens
