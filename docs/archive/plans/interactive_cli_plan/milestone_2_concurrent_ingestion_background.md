# Milestone 2 Implementation Plan: Concurrent Pipeline Ingestion (Background Processing)

## 1. Overview & Objectives
Milestone 2 enables simultaneous background ingestion and foreground interactive search/chat. It decouples the [`IngestionPipeline`](ingestion/pipeline.py:46) from blocking the main UI loop by running ingestion in a background daemon thread and piping telemetry progress updates via a thread-safe message queue into the terminal header panel.

---

## 2. Directory & File Structure
```
ui/
├── controller.py                # Updated LexiGrimSession with background ingestion management
└── cli/
    └── app.py                   # Updated InteractiveCLIShell with real-time header polling
```

---

## 3. Step-by-Step Implementation Instructions

### Step 1: Extend [`LexiGrimSession`](ui/controller.py:1) with Background Ingestion
- **File Path**: [`ui/controller.py`](ui/controller.py:1)
- **Action**: Add methods to manage background ingestion threads:
  - `trigger_background_ingestion(self, corpus_path: str)`: Spawn a daemon `threading.Thread` executing [`IngestionPipeline.run()`](ingestion/pipeline.py:64) in [`ingestion/pipeline.py`](ingestion/pipeline.py:1).
  - Initialize `self.ingestion_progress_queue = queue.Queue()` to collect progress dicts (`percentage`, `speed`, `message`).

### Step 2: Add Progress Reporting Callback to [`IngestionPipeline`](ingestion/pipeline.py:46)
- **File Path**: [`ingestion/pipeline.py`](ingestion/pipeline.py:1)
- **Action**: Accept an optional `progress_callback: Optional[Callable[[float, str, str], None]]` parameter in [`IngestionPipeline.__init__()`](ingestion/pipeline.py:49).
- Inside the bulk streaming loop, invoke `progress_callback(percentage, speed, message)` at regular intervals (e.g., every batch or every 100 items).

### Step 3: Integrate Background Queue Polling into [`InteractiveCLIShell`](ui/cli/app.py:1)
- **File Path**: [`ui/cli/app.py`](ui/cli/app.py:1)
- **Action**: Add a non-blocking queue drain loop inside `render_header()` or via an asynchronous `prompt_toolkit` timer callback (`app.invalidate()` or periodic poll).
- Update the header panel render tokens to display active progress bars and real-time processing speeds.

### Step 4: Add Slash Command for Ingestion in CLI
- **File Path**: [`ui/cli/app.py`](ui/cli/app.py:1)
- **Action**: Inside `handle_user_input()`, check for `/ingest <path>`. When entered, invoke [`LexiGrimSession.trigger_background_ingestion()`](ui/controller.py:1) and log a status message to the middle scrollable area.

---

## 4. Acceptance Criteria
- Entering `/ingest <corpus_path>` successfully starts ingestion in a background thread without locking terminal inputs.
- The top header panel updates in real time with progress percentages and processing speeds.
- The user can concurrently execute vector searches (`/narrow` or fresh queries) while ingestion runs in the background.
