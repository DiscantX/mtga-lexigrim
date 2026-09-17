from typing import List, Tuple, Any
from prompt_toolkit.application import Application
from prompt_toolkit.layout import Layout, HSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.widgets import TextArea
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.formatted_text import FormattedText
from ui.controller import LexiGrimSession

class InteractiveCLIShell:
    """Interactive prompt_toolkit shell implementing Split-Viewport Layout and REPL commands."""
    
    def __init__(self, session: LexiGrimSession):
        self.session = session
        
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
                Window(char='-', height=1),
                self.scroll_output,
                Window(char='-', height=1),
                self.input_field
            ]),
            focused_element=self.input_field
        )
        
        # Key bindings for quitting or convenience
        kb = KeyBindings()
        @kb.add('c-c')
        @kb.add('c-d')
        def _(event):
            event.app.exit()
            
        self.app = Application(
            layout=self.layout,
            key_bindings=kb,
            full_screen=True,
            mouse_support=True
        )

    def get_welcome_banner(self) -> str:
        return (
            "🔮 LexiGrim: Interactive Card Search & Narrowing Mode (PromptToolkit Shell)\n"
            "--------------------------------------------------------------------------------\n"
            "Commands:\n"
            "  - Type any search query (e.g. 'lightning bolt', 'counter target spell')\n"
            "  - Type '/narrow <query>' or '/n <query>' to search within previous results\n"
            "  - Type '/dedupe' to toggle oracle duplicate filtering ON/OFF\n"
            "  - Type ':quit', ':q', or 'exit' to exit\n"
            "--------------------------------------------------------------------------------\n"
        )

    def render_header(self) -> FormattedText:
        dedupe_status = "ON" if self.session.deduplicate_oracle else "OFF"
        limit = self.session.default_limit
        candidates_count = len(self.session.last_candidates)
        return [
            ("class:header", f" 🔮 LexiGrim Dashboard | Dedupe: {dedupe_status} | Limit: {limit} | Active Candidates: {candidates_count} \n"),
            ("class:header_sub", " Tip: Use /narrow <query> to refine current results, or type a query directly.")
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
        self.append_output("\n".join(output_lines))

    def append_output(self, text: str) -> None:
        # Append text to scroll output buffer
        current_text = self.scroll_output.text
        self.scroll_output.text = current_text + text + "\n"
        # Scroll to bottom
        self.scroll_output.buffer.cursor_position = len(self.scroll_output.text)

    def run(self) -> None:
        """Launch the full-screen prompt_toolkit application."""
        self.app.run()
