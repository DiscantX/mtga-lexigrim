# Comprehensive Analysis and Implementation Plan: Single, Unified Interactive CLI for LexiGrim

## 1. Executive Summary & Architectural Alignment

The long-term vision of LexiGrim is to create an advanced AI expert on Magic: The Gathering (MTG), supporting complex interactions like deckbuilding, synergy analysis, and rules interrogation as defined in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md:1). Currently, the system has a stable data ingestion and vector search implementation ([`docs/PLANS.md`](docs/PLANS.md:1)).

To bridge **Phase 1 (Data Ingestion & Vector Search)** with the upcoming **Phase 2 (AI Integration & Chatbot Interface)**, we need a single, unified interactive CLI that can:
1. Orchestrate bulk ingestion pipelines (such as comprehensive rules and card corpora) while maintaining absolute system responsiveness.
2. Provide a real-time, responsive interactive search and AI chatbot interface.
3. Support **concurrency**, allowing bulk ingestion to stream and index in the background while the user performs vector searches or interacts with the AI in the foreground.
4. Adhere strictly to the project's core architectural principle of being **modular, provider-agnostic, and clean** as specified in the [`AGENTS.md`](AGENTS.md:1) and [`docs/DECISIONS.md`](docs/DECISIONS.md:1).

This report outlines the technical research, architectural design, dependency evaluation, and step-by-step implementation plans for building this presentation layer.

---

## 2. Current State & Existing Implementations

To design a modular CLI, we must first understand the existing implementations of the CLI entry point, search engine, and ingestion pipelines.

### 2.1 Existing CLI Entry Point (`main.py`)
Currently, [`main.py`](main.py:1) acts as a static dispatcher using `argparse`. It separates workflows into mutually exclusive paths:
- **Search Mode**: Triggers [`InteractiveSearchCLI.run()`](search/cli.py:45) in [`search/cli.py`](search/cli.py:1).
- **Ingestion Mode**: Triggers either [`IngestionPipeline.run()`](ingestion/pipeline.py:64) in [`ingestion/pipeline.py`](ingestion/pipeline.py:1) or [`IngestionRunner.run_rules()`](ingestion/runner.py:20) in [`ingestion/runner.py`](ingestion/runner.py:1).

```python
# From main.py:41
elif args.search:
    print("Launching interactive search REPL...")
    # Launches a simple, blocking stdin loop...
    cli = InteractiveSearchCLI(engine, default_limit=args.results, deduplicate_oracle=args.deduplicate)
    cli.run()
```

### 2.2 Existing Ingestion Concurrency (`ingestion/pipeline.py`)
The ingestion flow is built around a producer-consumer thread model:
- **Producer (UI/Main Thread)**: Streams cards, formats text, calls [`BaseEmbeddingService.embed_documents()`](embeddings/base.py:14) in [`embeddings/base.py`](embeddings/base.py:1), and pushes points to a `queue.Queue`.
- **Consumer ([`IngestionWorker`](ingestion/worker.py:14) in [`ingestion/worker.py`](ingestion/worker.py:1))**: A background thread that consumes points and performs bulk database upserts via [`BaseVectorStore.upsert_batch()`](vectorstores/base.py:13) in [`vectorstores/base.py`](vectorstores/base.py:1).

This background concurrency pattern provides an excellent template for interactive concurrency, but the current UI thread blocks completely during embedding generation and file scanning, preventing concurrent CLI utilization.

---

## 3. Core Architectural Requirements & Technical Solutions

We require a system that maintains visual consistency, supports window resizing, and decouples UI rendering from heavy background workloads.

```
+-----------------------------------------------------------------------+
|  [STATS] Ingestion: 45.3% [=========>...........] | Qdrant: RUNNING   |
|  [STATS] Memory: 142MB   | Threads: 4           | Mode: Hybrid      |
+-----------------------------------------------------------------------+
| Search> counterspell                                                  |
| 1. Counterspell (UU)  [Score: 0.9234]                                 |
|    Type: Instant                                                      |
|    Text: Counter target spell.                                        |
|                                                                       |
| Search> /narrow blue                                                  |
| Narrowing within 1 previous candidates...                             |
|                                                                       |
| <Text scrolls in this viewport, keeping top and bottom panels locked>  |
|                                                                       |
+-----------------------------------------------------------------------+
| Prompt [Dedupe: ON | Limit: 3]> _                                     |
+-----------------------------------------------------------------------+
```

### 3.1 Split-Viewport Terminal Layout
To keep stats, messages, and progress bars fixed at the top, and the interactive prompt at the bottom, we must divide the terminal screen into three virtual zones:
1. **Header Panel (Rows $1$ to $H$)**: Contains static or slow-changing dashboard components (e.g., ingestion speed, overall progress, system health status).
2. **Scroll Area (Rows $H+1$ to $N-1$)**: Scrollable console output displaying card search hits, oracle text, conversational chat histories, or debug logs. Standard scrolling inside this region must not push the Header or Input Box out of position.
3. **Bottom Input Box (Row $N$)**: A persistent, pinned text-entry field allowing hotkey triggers and standard prompt interactions.

### 3.2 Handling Window Resizes (Anti-Ghosting)
When a terminal window is resized, the shell shifts the buffer columns and lines. In naive CLIs, this results in "ghost" texts and misplaced cursor lines. 
To resolve this, the CLI must:
- Listen to terminal resize signals (`SIGWINCH` on UNIX, or win32 resize event polling on Windows).
- Fetch the updated console size via `shutil.get_terminal_size()`.
- Trigger a structural recalculation of layouts (re-computing $H$ and $N$).
- Force a terminal clear (`\033[2J` or programmatic canvas redraws) and fully re-render all fixed sections based on the new dimensions.

### 3.3 Concurrency Model for Concurrent Ingestion and UI Loop
To run ingestion concurrently with the interactive search/chat UI, we must transition the UI thread to an **asynchronous event-driven model** (using Python's `asyncio`) or a multi-threaded architecture with a non-blocking UI rendering loop.

- **Background Workers**: Bulk ingestion tasks (such as corpus file reading, text chunking, and embedding generation) run in dedicated worker threads.
- **Thread-Safe Message Queue (`queue.Queue` or `asyncio.Queue`)**: Workers emit status payloads (e.g., `{"progress": 42.1, "rate": "150 cards/s", "message": "Upserting batch..."}`) onto a thread-safe message queue.
- **UI Event Loop**: The main UI loop polls this queue (either via cooperative async timers or non-blocking intervals) and updates the Header Panel stats in real time without lagging the user's input buffer.

### 3.4 Future Styling & ANSI Coloring
The architecture should consume structured styled tokens rather than raw strings. We can decouple styling from terminal output by using a representation like:
```python
FormattedText = List[Tuple[str, str]]  # List of (style_class/ansi_color, text)
```
This is fully compatible with ANSI color sequences and facilitates a clean transition to GUI canvases later.

---

## 4. Technical Evaluation: Custom ANSI vs. Existing Libraries

We compare the three primary approaches for implementing this terminal interface:

| Criteria | Option A: Custom ANSI Escape Codes | Option B: `prompt_toolkit` | Option C: `Textual` (with `Rich`) |
| :--- | :--- | :--- | :--- |
| **Dependency Weight** | **None** (pure Python standard library) | Low (pure Python, minor dependencies) | High (heavier framework) |
| **Window Resize Resilience** | Extremely difficult (prone to ghosting and platform-specific bugs) | **Excellent** (battle-tested auto-redraw engine) | **Excellent** (declarative resize layout system) |
| **Concurrency Support** | Hard to coordinate multi-threaded polling with raw stdin reads | **Excellent** (native integration with Python `asyncio`) | **Excellent** (async-first reactive design) |
| **Input & Editing Power** | Very primitive (must manually implement backspace, arrows, history) | **Outstanding** (IPython-level input, multiline, history) | Moderate (good inputs, but less REPL-optimized) |
| **Windows 11 Compatibility** | Modest (Windows CMD has quirks with terminal scrolling regions) | **Excellent** (robust cross-platform abstraction) | **Excellent** (highly optimized for modern terminals) |
| **Agnostic Architecture** | Excellent (zero libraries to carry over) | Highly modular (separates layout from data model) | Highly coupled to Textual class structure |

### 4.1 Comparison of Options
- **Option A (Rolling Custom ANSI)**: While highly agnostic and lightweight, rolling custom cursor rendering is notoriously brittle on Windows. Re-implementing a robust text-input engine supporting cursor movement, backspace, and terminal resizing from scratch is highly bug-prone and distracts from LexiGrim's AI focus.
- **Option B (`prompt_toolkit`)**: The standard for advanced terminal REPLs (used in IPython). It provides full layout structures (`HSplit`, `VSplit`), buffer controls, and an event loop that works seamlessly on Windows and Unix. It allows a dedicated bottom-input bar and scrollable viewport widgets out of the box.
- **Option C (`Textual`)**: An exceptional full-blown TUI framework. However, it takes over the entire terminal stdout, creating a "full-screen application" feel rather than a classic scrollable CLI log stream. This can feel slightly heavy for a simple developer utility, but is highly powerful.

### 4.2 Recommendation
**We recommend adopting Option B (`prompt_toolkit`) integrated with `Rich`**.
`prompt_toolkit` manages the input buffer, fixed footer input box, fixed header panel, window resizing, and asynchronous event loops natively. We can use `Rich` inside `prompt_toolkit` windows to provide rich ANSI formatting and beautiful card representation. This approach ensures maximum cross-platform stability (especially for Windows 11 CMD/PowerShell) with minimal maintenance.

---

## 5. Modular, Agnostic, and GUI-Parity Design

To ensure the CLI core is fully reusable elsewhere and can seamlessly transition to a GUI in the future, we must enforce a strict **Model-View-Controller (MVC) or Presentation-Controller-Core separation**.

```
                           +-------------------+
                           |    Core Logic     |
                           | (search, ingest,  |
                           |  vector db, LLM)  |
                           +---------+---------+
                                     |
                                     v
                           +---------+---------+
                           |  Controller API   | (Unified endpoints, returning
                           | (LexiGrimSession) |  serializable DTOs/raw dicts)
                           +----+---------+----+
                                |         |
        +-----------------------+         +-----------------------+
        v                                                         v
+-------+-------+                                         +-------+-------+
|  CLI View     | (prompt_toolkit/rich)                   |  GUI View     | (Future Electron, PySide,
|               |                                         |               |  or Web dashboard)
+---------------+                                         +---------------+
```

### 5.1 Presentation-Controller-Core Interface Structure
We define a highly decoupled architecture:
1. **The Core Services**: [`BaseVectorStore`](vectorstores/base.py:4) and [`BaseEmbeddingService`](embeddings/base.py:4). They have no awareness of terminals, scroll areas, or UI states.
2. **The Session Controller (`LexiGrimSession`)**: Manages the state of the active user session (e.g., search history, active candidate IDs for narrowing, background ingestion queues, LLM chat streams). It exposes pure Python methods that return serializable dicts or structured Data Transfer Objects (DTOs).
3. **The Pluggable UI View (`BaseView`)**: Receives data from the Controller and renders it. The CLI and GUI will simply be alternative implementations of `BaseView`.

### 5.2 Plug-in Architecture for MTG Features (Decks/Cards Panels)
To support pluggable custom displays (such as a decklist panel or a card visualization window), we can use a **Widget Registry**.
A generic widget base class receives raw data dictionaries and handles localized formatting:

```python
class PluggableWidget(ABC):
    """Abstract pluggable view component for interactive displays."""
    
    @abstractmethod
    def update(self, data: Dict[str, Any]) -> None:
        """Receive updated data model and re-cache representation."""
        pass

    @abstractmethod
    def render(self, width: int, height: int) -> FormattedText:
        """Render component to structured styled tokens matching allocated size."""
        pass
```

- **MTG-Specific Plugs**: We implement a `CardDetailWidget` and a `DeckListWidget` inside the `search/` or `ui/` directory, registering them with the layout controller.
- **Agnostic Reuse**: The entire UI shell can be imported into a completely different project. By registering different widgets (e.g., a `WeatherWidget` or `SystemMonitorWidget`), the core terminal engine can be reused globally.

---

## 6. Implementation Architecture

We propose the following directory additions and class definitions to cleanly implement this system.

### 6.1 Proposed Directory Additions
```
ui/                              # New interactive presentation package
│
├── __init__.py
├── controller.py                # LexiGrimSession: Unified agnostic endpoint controller
├── widget.py                    # Base pluggable widget definitions
├── cli/
│   ├── __init__.py
│   ├── app.py                   # Main prompt_toolkit application coordinator
│   ├── layout.py                # Split-viewport terminal layout layout builder
│   └── widgets/
│       ├── header.py            # Fixed stats header widget
│       ├── card_view.py         # Card formatting plug-in widget
│       └── deck_view.py         # Deck list display widget
└── gui/
    └── __init__.py              # Stub placeholder for future GUI controllers
```

### 6.2 Key Interface Definitions

#### A. Unified Agnostic Session Controller ([`ui/controller.py`](ui/controller.py:1))
This acts as the single source of truth for all business logic interactions:

```python
class LexiGrimSession:
    """Agnostic session state controller bridging presentation views to core engines."""
    
    def __init__(self, search_engine: CardSearchEngine, settings: Settings):
        self.search_engine = search_engine
        self.settings = settings
        
        # State management
        self.last_candidates: List[str] = []
        self.chat_history: List[Dict[str, str]] = []
        self.ingestion_progress_queue = queue.Queue()
        self._active_ingestion_thread: Optional[threading.Thread] = None

    def execute_search(self, query: str, narrow: bool = False, deduplicate: bool = False) -> List[Dict[str, Any]]:
        """Perform search and update candidate state, returning raw dictionary payloads."""
        candidates = self.last_candidates if (narrow and self.last_candidates) else None
        
        results = self.search_engine.vector_search(
            query_text=query,
            limit=self.settings.default_display_limit,
            candidate_ids=candidates,
            deduplicate_oracle=deduplicate
        )
        
        self.last_candidates = [str(hit.id) for hit in results]
        return [hit.payload for hit in results]

    def trigger_background_ingestion(self, corpus_path: str) -> None:
        """Launch ingestion on a separate thread, piping progress updates to ui-safe queue."""
        if self._active_ingestion_thread and self._active_ingestion_thread.is_alive():
            raise RuntimeError("Ingestion is already running!")
            
        def run_ingestion_thread():
            # Setup custom callback to feed progress
            def progress_callback(percentage: float, speed: str, msg: str):
                self.ingestion_progress_queue.put({
                    "type": "progress",
                    "percentage": percentage,
                    "speed": speed,
                    "message": msg
                })
                
            # Perform pipeline ingestion via IngestionPipeline
            # ...
            
        self._active_ingestion_thread = threading.Thread(target=run_ingestion_thread, daemon=True)
        self._active_ingestion_thread.start()
```

#### B. The Interactive CLI Shell Coordinator ([`ui/cli/app.py`](ui/cli/app.py:1))
Built on `prompt_toolkit`, this coordinates the split-viewport render loop:

```python
from prompt_toolkit.application import Application
from prompt_toolkit.layout import Layout, HSplit, Window
from prompt_toolkit.widgets import Frame, TextArea

class InteractiveCLIShell:
    """Interactive prompt_toolkit shell implementing Split-Viewport Layout and resize safety."""
    
    def __init__(self, session: LexiGrimSession):
        self.session = session
        
        # UI Components
        self.header_panel = Window(content=FormattedTextControl(self.render_header), height=3)
        self.scroll_output = TextArea(read_only=True, scrollbar=True)
        self.input_field = TextArea(multiline=False, prompt="LexiGrim> ")
        
        # Setup Layout
        self.layout = Layout(
            HSplit([
                self.header_panel,
                Window(char='-', height=1), # Separator row
                self.scroll_output,
                Window(char='-', height=1), # Separator row
                self.input_field
            ])
        )
        
        # Configure event bindings & keypresses
        self.input_field.accept_handler = self.handle_user_input
        self.app = Application(layout=self.layout, full_screen=True)

    def render_header(self) -> FormattedText:
        """Generate formatted tokens representing background ingestion stats or static banner."""
        # Non-blocking poll of progress updates from session queue
        while not self.session.ingestion_progress_queue.empty():
            update = self.session.ingestion_progress_queue.get_nowait()
            self.header_panel_data = update # Update widget state
            
        # Format and return styled tokens
        return [("class:header_title", "🔮 LexiGrim Dashboard | "), ("class:progress", f"Progress: {self.session_progress_data}%")]

    def handle_user_input(self, buffer) -> None:
        """Route user search and commands to unified session controller."""
        user_text = buffer.text.strip()
        if not user_text:
            return
            
        # Parse command or search query
        if user_text.startswith("/ingest "):
            path = user_text.split(" ", 1)[1]
            self.session.trigger_background_ingestion(path)
            self.log_message(f"Started background ingestion for {path}")
        else:
            # Standard search
            payloads = self.session.execute_search(user_text)
            self.display_search_payloads(payloads)

    def log_message(self, text: str) -> None:
        """Safely append formatted log message to the middle scrollable area."""
        self.scroll_output.text += f"\n{text}"

    def run(self) -> None:
        """Launch the full-screen prompt_toolkit application."""
        self.app.run()
```

---

## 7. Concrete Step-by-Step Implementation Plan

To build and deliver this unified, modular, and resilient interactive interface, we outline the execution steps divided into three targeted milestones:

### Milestone A: Core Controller & Prompt-Toolkit Layout (Foundation)
1. **Initialize Directory Layout**: Create the [`ui/`](ui/controller.py:1) package structure with a clean modular separation.
2. **Implement `LexiGrimSession`**: Extract state management and execution hooks from [`search/cli.py`](search/cli.py:1) and [`main.py`](main.py:1) into [`ui/controller.py`](ui/controller.py:1). Ensure it operates entirely on raw serializable dictionaries to guarantee future GUI/CLI compatibility.
3. **Build the CLI Layout**: Implement [`ui/cli/app.py`](ui/cli/app.py:1) using `prompt_toolkit`. Configure the three-zone screen division (Header, Scrolling Output Box, Bottom persistent Input field) and establish native console resize handler triggers to prevent "ghosting".

### Milestone B: Concurrent Pipeline Ingestion (Background Processing)
1. **Piped Ingestion Flow**: Refactor [`IngestionPipeline`](ingestion/pipeline.py:46) in [`ingestion/pipeline.py`](ingestion/pipeline.py:1) to support an optional thread-safe reporting callback that triggers on block completion.
2. **Background Thread Integration**: Update `LexiGrimSession` to spawn the pipeline in a separate background daemon thread, mapping the reporting callback directly to the thread-safe UI message queue.
3. **Active Panel Progress Display**: Update the CLI Header Panel to poll the queue at fixed intervals (e.g., $100\text{ms}$), dynamically rendering progress bars and indexing statistics without locking keyboard inputs in the persistent bottom field.

### Milestone C: Pluggable Widgets, Colors, and AI Support (Refinement)
1. **Styling and Tokens**: Add rich ANSI coloring using `prompt_toolkit` style sheets combined with the `Rich` console representation for beautiful terminal displays.
2. **Pluggable Visualizations**: Create the `CardDetailWidget` and `DeckListWidget` plug-ins to cleanly print multi-column card views, card comparison blocks, or compact mana curves in a side-by-side or dedicated split container.
3. **AI Chat Gateway Integration**: Prepare the session controller and prompt handler to capture conversation contexts, routing prompts to future LLM middlewares (such as Google Gemini) and streaming tokens incrementally into the middle scrolling area.
4. **Final Main Integration**: Re-target [`main.py`](main.py:1) to offer a unified interactive flag (e.g. `main.py -i` or `main.py --interactive`) that boots this rich, concurrent, split-viewport application.
