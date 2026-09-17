# Phase 3: Ingestion Pipeline Refactoring - Implementation Plan

This document outlines the complete, step-by-step implementation plan for **Phase 3: Ingestion Pipeline Refactoring**, ensuring full cohesion with [`docs/plans/phase_1_foundation_and_core.md`](docs/plans/phase_1_foundation_and_core.md:1) and [`docs/plans/phase_2_storage_and_embeddings.md`](docs/plans/phase_2_storage_and_embeddings.md:1), as guided by [`docs/MTG Expert Codebase Comprehensive Code Review.md`](docs/MTG%20Expert%20Codebase%20Comprehensive%20Code%20Review.md:1).

---

## Overview & Architecture Goals

Phase 3 transitions the procedural data ingestion script into a modular, object-oriented pipeline featuring:
1. **[`IngestionWorker`](ingestion/worker.py:1)** (`[`ingestion/worker.py`](ingestion/worker.py:1)`): A background thread consumer worker that batches points up to `UPSERT_BATCH_SIZE` (128) and performs bulk upserts via `[`BaseVectorStore.upsert_batch()`](vectorstores/base.py:1)`, handling thread synchronization, sentinel shutdown, and `[`queue.task_done()`](https://docs.python.org/3/library/queue.html#queue.Queue.task_done)` signaling.
2. **[`IngestionPipeline`](ingestion/pipeline.py:1)** (`[`ingestion/pipeline.py`](ingestion/pipeline.py:1)`): An orchestrator class accepting dependency injection (`[`BaseVectorStore`](vectorstores/base.py:1)`, `[`BaseEmbeddingService`](embeddings/base.py:1)`, `[`IngestionTimer`](utils/timer.py:1)`, `[`Settings`](config/settings.py:1)`), executing service validation, resume checking (paginated scroll up to 10,000 limit), bulk indexing toggling, inline streaming/embedding generation, worker queue dispatch, and memory-safe post-ingestion verification (`[`jsonl_cards = []`](ingest.py:1)` bug fix).
3. **Legacy Script Bridge (`[`ingest.py`](ingest.py:1)`)**: Refactored to act purely as a CLI launcher invoking `[`IngestionPipeline`](ingestion/pipeline.py:1)` inside `[`if __name__ == "__main__":`](ingest.py:1)` with zero top-level code execution on import.

---

## Step-by-Step Implementation Steps

### Step 1: Create Background Consumer Worker (`[`ingestion/worker.py`](ingestion/worker.py:1)`)

Create [`ingestion/worker.py`](ingestion/worker.py:1) to manage background thread processing of points.

- **Class [`IngestionWorker`](ingestion/worker.py:1)**:
  - `[`__init__(self, queue: Queue, vector_store: BaseVectorStore, batch_size: int = 128)`](ingestion/worker.py:1)`: Initializes queue reference, vector store dependency, batch size (default 128), and threading primitives (`[`threading.Thread`](https://docs.python.org/3/library/threading.html#threading.Thread)`).
  - `[`run(self)`](ingestion/worker.py:1)`: Continuously pulls items from the queue with a timeout (e.g., `2.0`s). Accumulates points into a local batch buffer until `batch_size` is reached, then calls `[`vector_store.upsert_batch(batch)`](vectorstores/base.py:1)`. For each processed item, invokes `[`self.queue.task_done()`](https://docs.python.org/3/library/queue.html#queue.Queue.task_done)`.
  - When a sentinel value (`[`None`](https://docs.python.org/3/library/constants.html#None)`) is encountered:
    - Flushes any remaining buffered points.
    - Calls `[`self.queue.task_done()`](https://docs.python.org/3/library/queue.html#queue.Queue.task_done)` for the sentinel.
    - Exits the consumer loop gracefully.
  - `[`start(self)`](ingestion/worker.py:1)` and `[`join(self)`](ingestion/worker.py:1)` wrapper methods to manage thread lifecycle.

---

### Step 2: Create Object-Oriented Ingestion Pipeline (`[`ingestion/pipeline.py`](ingestion/pipeline.py:1)`)

Create [`ingestion/pipeline.py`](ingestion/pipeline.py:1) containing `[`IngestionPipeline`](ingestion/pipeline.py:1)`.

- **Constructor Injection**:
  - `[`__init__(self, vector_store: BaseVectorStore, embedding_service: BaseEmbeddingService, timer: IngestionTimer, settings: Settings)`](ingestion/pipeline.py:1)`

- **Method [`run(self, file_path: str) -> None`](ingestion/pipeline.py:1)** Orchestration Flow:
  1. **Service Check**: Verify Qdrant availability via `[`QdrantServiceManager`](qdrant_manager.py:1)`.
  2. **Resume Check**: Retrieve existing IDs via `[`vector_store.get_existing_ids()`](vectorstores/base.py:1)` (utilizing a 10,000 page scroll limit).
  3. **Bulk Mode Enable**: Call `[`vector_store.set_bulk_mode(True)`](vectorstores/base.py:1)`.
  4. **Pre-scan Dataset**: Count total lines using `[`JsonlStreamReader.count_lines(file_path)`](utils/jsonl_reader.py:1)`.
  5. **Background Worker Initialization**: Instantiate and start `[`IngestionWorker`](ingestion/worker.py:1)`.
  6. **Stream & Process Inline**:
     - Stream records via `[`JsonlStreamReader.stream(file_path)`](utils/jsonl_reader.py:1)`.
     - Filter out cards whose IDs already exist in the resume set.
     - Extract embedding text using `[`extract_embedding_text()`](utils/text_extractor.py:1)`.
     - Generate embeddings in batches via `[`embedding_service.embed_documents()`](embeddings/base.py:1)`.
     - Construct point models and put them into the worker `[`queue.Queue`](https://docs.python.org/3/library/queue.html#queue.Queue)`.
  7. **Queue Shutdown**:
     - Call `[`queue.join()`](https://docs.python.org/3/library/queue.html#queue.Queue.join)` to ensure all queued points are consumed.
     - Send sentinel `[`None`](https://docs.python.org/3/library/constants.html#None)` to the queue and join the worker thread.
  8. **Memory-Safe Verification**:
     - Stream the file line-by-line, checking record IDs against the database set without loading all objects into memory (fixing the previous `[`jsonl_cards = []`](ingest.py:1)` memory exhaustion bug).
     - Re-ingest any missed items if detected.
  9. **Restore Indexing Threshold**: Call `[`vector_store.set_bulk_mode(False)`](vectorstores/base.py:1)`.
  10. **Telemetry Report**: Print skipped cards summary and display timing breakdown via `[`timer.report()`](utils/timer.py:1)`.

---

### Step 3: Refactor Legacy Script Bridge (`[`ingest.py`](ingest.py:1)`)

Refactor [`ingest.py`](ingest.py:1) to remove procedural code execution upon import and convert it into a lightweight CLI runner:
- Parses command line arguments (e.g., input file path).
- Instantiates concrete implementations of `[`BaseVectorStore`](vectorstores/base.py:1)`, `[`BaseEmbeddingService`](embeddings/base.py:1)`, `[`IngestionTimer`](utils/timer.py:1)`, and `[`Settings`](config/settings.py:1)`.
- Instantiates `[`IngestionPipeline`](ingestion/pipeline.py:1)` and executes `[`pipeline.run(file_path)`](ingestion/pipeline.py:1)` inside `[`if __name__ == "__main__":`](ingest.py:1)`.

---

## Verification & Testing

- Run unit tests for `[`IngestionWorker`](ingestion/worker.py:1)` verifying queue consumption, batching, sentinel handling, and `[`task_done()`](https://docs.python.org/3/library/queue.html#queue.Queue.task_done)` synchronization.
- Test `[`IngestionPipeline`](ingestion/pipeline.py:1)` with dry-run and mock vector/embedding services.
- Execute integration testing via `[`python ingest.py`](ingest.py:1)` to validate end-to-end streaming ingestion.
