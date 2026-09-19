# LexiGrim System Architecture

## 1. Overview & Long-Term Vision

The long-term goal of the **LexiGrim** (MTG Lexigrim) project is to create an advanced AI expert on **Magic: The Gathering (MTG)**. The system leverages a local Qdrant vector database containing vector embeddings for all MTG cards (ingested from Scryfall data corpora), official game rules, and representative meta-game decklists. Once fully realized, the AI will be capable of building new decks, analyzing synergies, answering rules queries, and performing expert-level MTG tasks.

The project is structured into two main phases:
- **Phase 1 -- Data Ingestion and Vector Database Search** ([`docs/plans/phase_1_foundation_and_core.md`](archive/plans/phase_1_foundation_and_core.md:1)): Building the foundational storage, streaming, embedding, ingestion pipeline, and similarity search engine.
- **Phase 2 -- AI Integration** ([`docs/plans/phase_2_storage_and_embeddings.md`](archive/plans/phase_2_storage_and_embeddings.md:1)): Implementing a chatbot-like interface with provider/model agnostic middleware (starting with Google Gemini).

---

## 2. Architectural Principles

1. **Object-Oriented, Agnostic, & Modular**: Code is structured into decoupled thematic packages with abstract base classes (`BaseVectorStore`, `BaseEmbeddingService`) ensuring future extensibility (e.g., swapping Qdrant for another vector database or FastEmbed for OpenAI/Ollama).
2. **Zero Premature Truncation (The "Rounding" Principle)**: As stated in ([`docs/plans/interactive_search_and_narrowing.md`](archive/plans/interactive_search_and_narrowing.md:4)): *"Carry the full value until the final display operation (do rounding/truncation last)."* Data and candidate IDs are carried through processing and cascading filters without arbitrary top-$x$ truncation until final display rendering.
3. **No Mega Scripts & Human Readability**: Codebases are partitioned into clean, single-responsibility modules.

---

## 3. Directory & Package Layout

```
mtga-expert/
│
├── config/
│   ├── __init__.py
│   └── settings.py              # Centralized strongly-typed configuration settings
│
├── core/
│   ├── __init__.py
│   ├── streaming.py             # Memory-safe incremental JSONL stream reader
│   └── timer.py                 # Thread-safe performance telemetry timer
│
├── vectorstores/
│   ├── __init__.py
│   ├── base.py                  # Abstract BaseVectorStore interface
│   ├── qdrant.py                # QdrantVectorStore concrete implementation
│   └── service_manager.py       # Cross-platform Qdrant daemon lifecycle manager
│
├── embeddings/
│   ├── __init__.py
│   ├── base.py                  # Abstract BaseEmbeddingService interface
│   ├── fastembed_provider.py    # FastEmbed provider with bounded thread-safe LRU cache
│   └── text_extractors.py       # Card payload cleaner and multi-face oracle text formatter
│
├── ingestion/
│   ├── __init__.py
│   ├── pipeline.py              # Object-oriented IngestionPipeline (producer-consumer)
│   └── worker.py                # Dedicated background upsert worker thread
│
├── search/
│   ├── __init__.py
│   ├── engine.py                # CardSearchEngine (vector search, non-mutating filters, narrowing)
│   └── cli.py                   # Interactive REPL session & formatted terminal rendering
│
├── ai/                          # Prepared module for Phase 2 LLM / agent integration
│   └── __init__.py
│
├── benchmark/
│   ├── __init__.py
│   └── runner.py                # FastEmbed thread tuning & batch size grid search benchmark
│
├── utils/
│   └── jsonl_inspector.py       # Schema inspection utility
│
├── tests/                       # Unit & integration test suite
│   ├── fixtures/
│   │   └── sample_cards.json    # Extracted mock card fixtures
│   ├── test_pipeline.py
│   └── test_worker.py
│
├── main.py                      # Clean CLI dispatcher entry point
└── search.py                    # Backward-compatible search launcher bridge
```

### Directory Usage Rules & Restrictions

- **`data/`**: Reserved exclusively for pure data artifacts (such as Qdrant database storage, corpus files, etc.). **Never** place Python scripts, source code, or application logic modules inside `data/`.
- **`storage/`**: **Reserved Directory / Forbidden for Project Use.** This directory is utilized by a 3rd party application that maintains its own Qdrant database instance. It must **not** be used by our project for any purpose whatsoever. Critically, do *not* configure or allow our Qdrant database or data artifacts to be stored in `storage/`, as doing so will cause catastrophic database conflicts between the two applications.

---

## 4. Component Architecture Details

### 4.1 Centralized Configuration ([`config/settings.py`](../config/settings.py:1))
Managed via the [`Settings`](../config/settings.py:54) class in ([`config/settings.py`](../config/settings.py:1)), centralizing corpus paths, Qdrant host/port/binary paths, FastEmbed threads, batch sizes, indexing thresholds, and retry parameters. Environment variables are supported with sensible defaults.

### 4.2 Core Utilities ([`core/`](../core/))
- [`JsonlStreamReader`](../core/streaming.py:116) ([`core/streaming.py`](../core/streaming.py:1)): Reads large JSONL files incrementally using chunk buffering to maintain a flat memory footprint.
- [`IngestionTimer`](../core/timer.py:186) ([`core/timer.py`](../core/timer.py:1)): Thread-safe telemetry instrument measuring component durations and reporting percentage breakdowns.

### 4.3 Vector Storage & Daemon Management ([`vectorstores/`](../vectorstores/))
- [`BaseVectorStore`](../vectorstores/base.py:230) ([`vectorstores/base.py`](../vectorstores/base.py:1)): Abstract interface defining schema initialization, batch upserts, similarity search, existing ID retrieval, and bulk mode threshold toggling.
- [`QdrantVectorStore`](../vectorstores/qdrant.py:281) ([`vectorstores/qdrant.py`](../vectorstores/qdrant.py:1)): Concrete Qdrant implementation utilizing optimized 10,000-limit scroll pagination for resume capability and non-mutating query filter combination.
- [`QdrantServiceManager`](../vectorstores/service_manager.py:414) ([`vectorstores/service_manager.py`](../vectorstores/service_manager.py:1)): Cross-platform daemon lifecycle manager supporting environment variable overrides, `shutil.which("qdrant")`, and platform-specific Windows process hiding flags (`sys.platform == "win32"`).

### 4.4 Embeddings & Text Extraction ([`embeddings/`](../embeddings/))
- [`BaseEmbeddingService`](../embeddings/base.py:51) ([`embeddings/base.py`](../embeddings/base.py:1)): Abstract embedding interface.
- [`FastEmbedProvider`](../embeddings/fastembed_provider.py:85) ([`embeddings/fastembed_provider.py`](../embeddings/fastembed_provider.py:1)): FastEmbed implementation featuring lazy model initialization, thread-safe LRU caching (`collections.OrderedDict`), and thread tuning.
- [`extract_embedding_text()`](../embeddings/text_extractors.py:193) ([`embeddings/text_extractors.py`](../embeddings/text_extractors.py:1)): Formats card attributes (name, mana cost, type line, oracle text) into rich text representations, correctly handling single-faced and double-faced cards (`"card_faces"`).
- [`extract_clean_payload()`](../embeddings/text_extractors.py:176) ([`embeddings/text_extractors.py`](../embeddings/text_extractors.py:1)): Strips non-essential keys (such as affiliate links, raw prices, and redundant web URIs) to reduce Qdrant payload footprint by ~80% (see ([`docs/payload_schema.md`](payload_schema.md:1))).

### 4.5 Ingestion Pipeline ([`ingestion/`](../ingestion/))
- [`IngestionPipeline`](../ingestion/pipeline.py:1) ([`ingestion/pipeline.py`](../ingestion/pipeline.py:1)): Producer-consumer orchestrator. Streams cards on-the-fly, filters out already-indexed cards, batches local vector generation, and pushes points to a thread-safe queue.
- [`IngestionWorker`](../ingestion/worker.py:1) ([`ingestion/worker.py`](../ingestion/worker.py:1)): Dedicated background thread consumer that accumulates points up to `upsert_batch_size` (128) and executes resilient database upserts with exponential backoff.

### 4.6 Search & REPL ([`search/`](../search/))
- [`CardSearchEngine`](../search/engine.py:1) ([`search/engine.py`](../search/engine.py:1)): Encapsulates vector similarity search with safe query filter construction and cascading candidate ID narrowing.
- [`InteractiveSearchCLI`](../search/cli.py:1) ([`search/cli.py`](../search/cli.py:1)): Interactive terminal session supporting fresh queries, result formatting, and `/narrow` refinement commands.

---

## 5. Environment Details & Execution

- **Python Virtual Environment**: Located at `.venv`. All agent and runtime executions must operate within `.venv`.
- **CLI Dispatcher**: [`main.py`](../main.py:1) provides command-line entry points:
  - Ingestion: `python main.py --corpus corpus/<filename>.jsonl`
  - Interactive Search: `python main.py --search --results 3`
