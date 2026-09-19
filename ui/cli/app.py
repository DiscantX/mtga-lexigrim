import queue
from typing import List, Tuple, Any
from prompt_toolkit.application import Application
from prompt_toolkit.layout import Layout, HSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.widgets import TextArea
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.styles import Style
from ui.controller import LexiGrimSession
from ui.cli.widgets.card_view import CardDetailWidget
from ui.cli.widgets.deck_view import DeckListWidget

class InteractiveCLIShell:
    """Interactive prompt_toolkit shell implementing Split-Viewport Layout, ANSI styling, pluggable widgets, and AI chat."""
    
    def __init__(self, session: LexiGrimSession):
        self.session = session
        self.card_widget = CardDetailWidget()
        self.deck_widget = DeckListWidget()
        self.last_results: List[dict] = []
        
        # UI Components
        self.header_panel = Window(content=FormattedTextControl(self.render_header), height=2)
        self.scroll_output = TextArea(
            text=self.get_welcome_banner(),
            read_only=True,
            scrollbar=True,
            wrap_lines=True
        )
        self.input_field = TextArea(
            multiline=False,
            prompt="LexiGrim> ",
            accept_handler=self.handle_user_input
        )
        
        # Setup Layout (Split-viewport)
        self.layout = Layout(
            HSplit([
                self.header_panel,
                Window(char='-', height=1, style="class:border"),
                self.scroll_output,
                Window(char='-', height=1, style="class:border"),
                self.input_field
            ]),
            focused_element=self.input_field
        )
        
        # Theme & ANSI Style definitions (prompt_toolkit format)
        self.style = Style([
            ("header", "bg:#1e1e2e #89b4fa bold"),
            ("header_sub", "bg:#1e1e2e #9399b2 italic"),
            ("border", "#6c7086"),
            ("card_border", "#89b4fa"),
            ("card_name", "#f9e2af bold"),
            ("card_mana", "#a6e3a1"),
            ("card_type", "#fab387"),
            ("card_text", "#cdd6f4"),
            ("card_flavor", "#7f849c italic"),
            ("card_muted", "#6c7086"),
            ("deck_header", "#cba6f7 bold"),
            ("deck_subheader", "#89b4fa underline"),
            ("deck_item", "#a6e3a1"),
            ("deck_muted", "#6c7086"),
            ("ai_response", "#94e2d5"),
            ("prompt", "#89b4fa bold"),
        ])
        
        # Key bindings for quitting or convenience
        kb = KeyBindings()
        @kb.add('c-c')
        @kb.add('c-d')
        def _(event):
            event.app.exit()
            
        self.app = Application(
            layout=self.layout,
            key_bindings=kb,
            style=self.style,
            full_screen=True,
            mouse_support=True
        )

    def get_welcome_banner(self) -> str:
        return (
            "🔮 LexiGrim: Interactive MTG Expert & Pluggable Shell (Milestone 3)\n"
            "--------------------------------------------------------------------------------\n"
            "Commands:\n"
            "  - Search: Type any search query (e.g. 'lightning bolt', 'counterspell')\n"
            "  - Narrow: '/narrow <query>' or '/n <query>' within previous candidates\n"
            "  - AI Chat: '/ai <prompt>' (Streams AI response middleware)\n"
            "  - Card View: '/card [index]' (Display detailed card widget for search result)\n"
            "  - Deck View: '/deck' (Display deck list and mana curve)\n"
            "  - Dedupe: '/dedupe' (Toggle oracle duplicate filtering ON/OFF)\n"
            "  - Ingest: '/ingest <path>' (Run background corpus ingestion)\n"
            "  - Sync: '/sync [type]' (Sync Scryfall bulk corpora and run ingestion)\n"
            "  - Exit: ':quit', ':q', or 'exit'\n"
            "--------------------------------------------------------------------------------\n"
        )

    def render_header(self) -> FormattedText:
        while not self.session.ingestion_progress_queue.empty():
            try:
                self.session.ingestion_progress_queue.get_nowait()
            except queue.Empty:
                break

        dedupe_status = "ON" if self.session.deduplicate_oracle else "OFF"
        limit = self.session.default_limit
        candidates_count = len(self.session.last_candidates)
        
        if self.session.is_ingesting or self.session.ingestion_progress > 0:
            pct = self.session.ingestion_progress
            filled = int(pct / 10)
            bar = "[" + "=" * filled + "." * (10 - filled) + "]"
            speed = self.session.ingestion_speed
            msg = self.session.ingestion_message
            return [
                ("class:header", f" 🔮 LexiGrim Dashboard | Ingestion: {pct:5.1f}% {bar} | Rate: {speed} \n"),
                ("class:header_sub", f" Status: {msg}")
            ]
        else:
            return [
                ("class:header", f" 🔮 LexiGrim Dashboard | Dedupe: {dedupe_status} | Limit: {limit} | Active Candidates: {candidates_count} \n"),
                ("class:header_sub", " Tip: Use /ai for AI chat, /card <#> for card widget, /deck for deck view.")
            ]

    def handle_user_input(self, buffer) -> None:
        user_text = buffer.text.strip()
        buffer.text = ""  # Clear input box immediately
        
        if not user_text:
            return
            
        lower_text = user_text.lower()
        if lower_text in [":quit", ":q", "exit"]:
            self.app.exit()
            return
            
        if lower_text == "/dedupe":
            self.session.deduplicate_oracle = not self.session.deduplicate_oracle
            status = "ON" if self.session.deduplicate_oracle else "OFF"
            self.append_output(f"\n🔮 Oracle deduplication toggled to: {status}\n")
            return

        if lower_text == "/ingest" or user_text.startswith("/ingest "):
            path = user_text.split(" ", 1)[1].strip() if len(user_text.split(" ", 1)) > 1 else None
            try:
                self.session.trigger_background_ingestion(path)
                target_desc = path if path else "all corpora (auto-discovery)"
                self.append_output(f"\n🚀 Started background ingestion for: {target_desc}\n")
            except Exception as e:
                self.append_output(f"\n⚠️ Failed to start background ingestion: {e}\n")
            return

        if lower_text == "/sync" or user_text.startswith("/sync "):
            corpus_type = user_text.split(" ", 1)[1].strip() if len(user_text.split(" ", 1)) > 1 else None
            try:
                self.session.trigger_background_sync(corpus_type)
                target_desc = corpus_type if corpus_type else "all corpora (oracle_cards, rulings, oracle_tags)"
                self.append_output(f"\n🔄 Started background sync & ingestion for: {target_desc}\n")
            except Exception as e:
                self.append_output(f"\n⚠️ Failed to start background sync: {e}\n")
            return

        if user_text.startswith("/ai "):
            prompt = user_text.split(" ", 1)[1].strip()
            self.append_output(f"\n🤖 [AI Prompt]: {prompt}\n")
            try:
                ai_output = ["\n"]
                for chunk in self.session.stream_ai_chat_response(prompt):
                    ai_output.append(chunk)
                ai_output.append("\n")
                self.append_output("".join(ai_output))
            except Exception as e:
                self.append_output(f"\n⚠️ AI error: {e}\n")
            return

        if user_text.startswith("/card"):
            parts = user_text.split()
            idx = 1
            if len(parts) > 1:
                try:
                    idx = int(parts[1])
                except ValueError:
                    idx = 1
            if not self.last_results:
                self.append_output("\n⚠️ No search results available. Perform a search first.\n")
                return
            if 1 <= idx <= len(self.last_results):
                card = self.last_results[idx - 1]
                self.card_widget.update(card)
                rendered_tokens = self.card_widget.render(80, 20)
                card_str = "".join(text for style, text in rendered_tokens)
                self.append_output(f"\n[Card Detail Widget for #{idx}]" + card_str)
            else:
                self.append_output(f"\n⚠️ Invalid result index {idx}. Range is 1-{len(self.last_results)}.\n")
            return

        if user_text == "/deck":
            sample_deck = {
                "name": "Izzet Control Demo",
                "mainboard": [
                    {"count": 4, "name": "Counterspell", "type": "Instant"},
                    {"count": 4, "name": "Lightning Bolt", "type": "Instant"},
                    {"count": 4, "name": "Brainstorm", "type": "Instant"},
                    {"count": 20, "name": "Island / Mountain", "type": "Land"}
                ],
                "sideboard": [
                    {"count": 3, "name": "Blood Moon", "type": "Enchantment"}
                ]
            }
            self.deck_widget.update(sample_deck)
            rendered_tokens = self.deck_widget.render(80, 20)
            deck_str = "".join(text for style, text in rendered_tokens)
            self.append_output(f"\n[Deck View Widget]" + deck_str)
            return
            
        is_narrow = False
        query_to_run = user_text
        
        if user_text.startswith("/narrow ") or user_text.startswith("/n "):
            is_narrow = True
            parts = user_text.split(" ", 1)
            if len(parts) > 1:
                query_to_run = parts[1].strip()
            else:
                query_to_run = ""
                
            if not self.session.last_candidates:
                self.append_output("\n⚠️ No active result set to narrow. Performing fresh search instead.\n")
                is_narrow = False

        if is_narrow:
            self.append_output(f"\n[Narrowing within {len(self.session.last_candidates)} previous candidates for: '{query_to_run}' (Dedupe: {'ON' if self.session.deduplicate_oracle else 'OFF'})]")
            results = self.session.execute_search(query_to_run, narrow=True)
        else:
            self.append_output(f"\n[Search: '{query_to_run}' (Dedupe: {'ON' if self.session.deduplicate_oracle else 'OFF'})]")
            results = self.session.execute_search(query_to_run, narrow=False)
            
        self.last_results = results
        self.display_results(results, query_to_run, is_narrow)

    def display_results(self, results: List[dict], query_text: str, is_narrow: bool) -> None:
        if not results:
            self.append_output("\nNo cards matched the given search and filter criteria.\n")
            return
            
        output_lines = [f"\n=================================================="]
        output_lines.append(f"Found {len(results)} matches for: '{query_text}'")
        output_lines.append(f"==================================================")
        
        for i, item in enumerate(results, 1):
            name = item.get("name", "Unknown")
            mana_cost = item.get("mana_cost", "N/A")
            type_line = item.get("type_line", "N/A")
            set_code = str(item.get("set", "N/A")).upper()
            rarity = str(item.get("rarity", "N/A")).upper()
            score = item.get("score")
            score_str = f"{score:.4f}" if score is not None else "N/A"
            oracle_text = item.get("oracle_text", "")
            
            output_lines.append(f"\n{i}. {name} ({mana_cost})  [Set: {set_code} | Rarity: {rarity} | Score: {score_str}]")
            output_lines.append(f"   Type: {type_line}")
            output_lines.append(f"   Text: {oracle_text.replace(chr(10), ' ')}")
            
        output_lines.append(f"==================================================\n")
        output_lines.append("Tip: Type '/card <index>' (e.g. '/card 1') to inspect card details widget.")
        self.append_output("\n".join(output_lines))

    def append_output(self, text: str) -> None:
        current_text = self.scroll_output.text
        self.scroll_output.text = current_text + text + "\n"
        self.scroll_output.buffer.cursor_position = len(self.scroll_output.text)

    def run(self) -> None:
        """Launch the full-screen prompt_toolkit application."""
        self.app.run()
