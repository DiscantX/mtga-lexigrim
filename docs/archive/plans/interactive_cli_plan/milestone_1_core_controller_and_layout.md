# Milestone 1 Implementation Plan: Core Controller & Prompt-Toolkit Layout

## 1. Overview & Objectives
Milestone 1 establishes the architectural foundation for the unified interactive CLI by creating a presentation-agnostic session controller ([`LexiGrimSession`](ui/controller.py:1)) and a `prompt_toolkit`-based split-viewport terminal shell ([`InteractiveCLIShell`](ui/cli/app.py:1)). This separates underlying core search and ingestion services from the terminal rendering layer, ensuring full CLI/GUI parity.

---

## 2. Directory & File Structure
```
ui/
├── __init__.py
├── controller.py                # LexiGrimSession agnostic session controller
└── cli/
    ├── __init__.py
    └── app.py                   # prompt_toolkit split-viewport application shell
```

---

## 3. Step-by-Step Implementation Instructions

### Step 1: Create [`ui/`](ui/__init__.py) Package Initialization
- **File Path**: [`ui/__init__.py`](ui/__init__.py:1)
- **Action**: Create an empty initialization file or export primary session classes.

### Step 2: Implement Agnostic Session Controller ([`ui/controller.py`](ui/controller.py:1))
- **File Path**: [`ui/controller.py`](ui/controller.py:1)
- **Class**: [`LexiGrimSession`](ui/controller.py:1)
- **Methods**:
  - `__init__(self, search_engine: CardSearchEngine, settings: Settings)`: Initialize state variables (`self.last_candidates`, `self.chat_history`, `self.ingestion_progress_queue`).
  - `execute_search(self, query: str, narrow: bool = False, deduplicate: bool = False) -> List[Dict[str, Any]]`: Execute vector search via [`CardSearchEngine`](search/engine.py:6) in [`search/engine.py`](search/engine.py:1) and return raw payload dictionaries. Update `self.last_candidates`.

### Step 3: Implement Split-Viewport Terminal Shell ([`ui/cli/app.py`](ui/cli/app.py:1))
- **File Path**: [`ui/cli/app.py`](ui/cli/app.py:1)
- **Class**: [`InteractiveCLIShell`](ui/cli/app.py:1)
- **Components**:
  - Header panel (`Window` with `FormattedTextControl`) displaying system status and version info.
  - Scrollable output area (`TextArea` configured with `read_only=True` and `scrollbar=True`).
  - Persistent bottom input box (`TextArea` configured with `multiline=False` and prompt `"LexiGrim> "`).
- **Layout Construction**:
  - Combine components using `HSplit` layout from `prompt_toolkit.layout`.
- **Event Handling**:
  - Implement `handle_user_input(self, buffer)` to capture search queries and pass them to [`LexiGrimSession.execute_search()`](ui/controller.py:1).
  - Print formatted results into the scrollable output area.

### Step 4: Integrate into [`main.py`](main.py:1) Dispatcher
- **File Path**: [`main.py`](main.py:1)
- **Action**: Add an interactive command-line flag `-i` / `--interactive` that instantiates [`CardSearchEngine`](search/engine.py:6), wraps it in [`LexiGrimSession`](ui/controller.py:1), and launches [`InteractiveCLIShell.run()`](ui/cli/app.py:1).

---

## 4. Acceptance Criteria
- [`main.py`](main.py:1) successfully launches the interactive shell when invoked with `--interactive`.
- The terminal layout cleanly separates the header panel, scrolling output, and bottom input box.
- Terminal window resizes automatically redraw the layout without ghosting or text displacement.
- Inputting a search query displays structured card results in the scrollable middle viewport.
