# Phase 4: Search Engine, CLI & Benchmarking Implementation Plan

This implementation plan outlines the precise architecture, class interfaces, method signatures, file paths, and step-by-step migration instructions for **Phase 4: Search Engine, CLI & Benchmarking** of the MTG Expert codebase refactor.

---

## 1. Architectural Overview & Design Philosophy

Phase 4 bridges the core storage/embeddings (Phase 2) and ingestion pipeline (Phase 3) with production-grade search capabilities, an interactive REPL, a clean CLI entry point, and isolated benchmarking.

### Key Objectives
1. **Object-Oriented Search Engine**: Decouple search execution from Qdrant internals via [`CardSearchEngine`](search/engine.py:1) adhering to dependency injection principles (`BaseVectorStore`, `BaseEmbeddingService`). Fix the critical filter mutation bug.
2. **Interactive CLI & REPL**: Extract search display and REPL loop logic into [`InteractiveSearchCLI`](search/cli.py:1) supporting `/narrow` query refinement.
3. **Clean CLI Dispatcher**: Modernize [`main.py`](main.py:1) with `argparse`, eliminating top-level import side-effects and lazy-loading services.
4. **Legacy Bridge**: Provide a backward-compatible entry point in [`search.py`](search.py:1) delegating to `InteractiveSearchCLI`.
5. **Benchmark & Test Fixtures**: Refactor monolithic [`benchmark.py`](benchmark.py:1) into [`benchmark/runner.py`](benchmark/runner.py:1), extract 300-line sample cards into [`tests/fixtures/sample_cards.json`](tests/fixtures/sample_cards.json:1), and import text extraction directly from [`embeddings/text_extractors.py`](embeddings/text_extractors.py:1).

---

## 2. Component Specifications & Interfaces

### 2.1 Object-Oriented Search Engine (`search/engine.py`)

[`CardSearchEngine`](search/engine.py:1) encapsulates semantic vector search and query fusion stubs.

```python
class CardSearchEngine:
    def __init__(self, vector_store: BaseVectorStore, embedding_service: BaseEmbeddingService):
        self.vector_store = vector_store
        self.embedding_service = embedding_service

    def vector_search(
        self,
        query_text: str,
        limit: Optional[int] = None,
        query_filter: Optional[Any] = None,
        candidate_ids: Optional[list[str]] = None
    ) -> list[Any]:
        ...

    def multi_query_fusion(
        self,
        queries: list[str],
        limit: Optional[int] = None,
        query_filter: Optional[Any] = None
    ) -> list[Any]:
        ...
```

#### Critical Bug Fix: Filter Mutation
In the legacy implementation [`search.py`](search.py:1), appending `candidate_ids` mutated `query_filter.must` in-place, causing state leakage across concurrent/sequential searches. The new implementation constructs a fresh filter instance:
```python
from qdrant_client.http import models

# Construct new filter safely without in-place mutation
effective_filter = query_filter
if candidate_ids:
    has_id_condition = models.HasIdCondition(has_id=candidate_ids)
    if query_filter and hasattr(query_filter, "must") and query_filter.must:
        effective_filter = models.Filter(
            must=list(query_filter.must) + [has_id_condition]
        )
    elif query_filter:
        effective_filter = models.Filter(
            must=[query_filter, has_id_condition]
        )
    else:
        effective_filter = models.Filter(must=[has_id_condition])
```

---

### 2.2 Interactive CLI & REPL (`search/cli.py`)

[`InteractiveSearchCLI`](search/cli.py:1) handles console input/output and session state (such as active `candidate_ids` for narrowing searches).

```python
class InteractiveSearchCLI:
    def __init__(self, search_engine: CardSearchEngine, default_limit: int = 10):
        self.search_engine = search_engine
        self.default_limit = default_limit
        self.last_candidate_ids: Optional[list[str]] = None

    def run(self) -> None:
        ...

    def print_results(self, results: list[Any]) -> None:
        ...
```

- **Formatting Rules**: [`print_results()`](search/cli.py:1) displays Card Name, Mana Cost, Type Line, Similarity Score, and Oracle Text (handling single/double-faced cards cleanly).
- **Commands**:
  - Regular text: Fresh vector search.
  - `/narrow <query>` or `/n <query>`: Refines previous search results using `candidate_ids` derived from the last search.
  - `:quit`, `:q`, `exit`: Terminates REPL loop.

---

### 2.3 Clean CLI Dispatcher (`main.py`)

Refactors [`main.py`](main.py:1) to use `argparse` with lazy initialization and zero top-level import side-effects.

```python
import argparse
from core.settings import Settings
from storage.qdrant_manager import QdrantServiceManager
from storage.vector_store import QdrantVectorStore
from embeddings.fastembed_provider import FastEmbedProvider
from search.engine import CardSearchEngine
from search.cli import InteractiveSearchCLI
from pipeline.ingestion import IngestionPipeline

def main() -> None:
    parser = argparse.ArgumentParser(description="MTG Expert CLI & Search Engine")
    parser.add_argument("-s", "--search", action="store_true", help="Launch interactive search REPL")
    parser.add_argument("-r", "--results", type=int, default=10, help="Default result limit for search")
    parser.add_argument("--corpus", type=str, help="Path to card corpus JSONL for ingestion")
    
    args = parser.parse_args()
    
    settings = Settings()
    
    if args.corpus:
        # Initialize Ingestion Pipeline
        ...
    elif args.search:
        # Initialize Services & Launch CLI
        ...
```

---

### 2.4 Legacy Bridge (`search.py`)

[`search.py`](search.py:1) becomes a thin launcher script:
```python
if __name__ == "__main__":
    from search.cli import InteractiveSearchCLI
    from search.engine import CardSearchEngine
    from storage.vector_store import QdrantVectorStore
    from embeddings.fastembed_provider import FastEmbedProvider
    from storage.qdrant_manager import QdrantServiceManager
    from core.settings import Settings

    settings = Settings()
    service_manager = QdrantServiceManager(settings)
    vector_store = QdrantVectorStore(service_manager)
    embedding_service = FastEmbedProvider(settings)
    
    engine = CardSearchEngine(vector_store, embedding_service)
    cli = InteractiveSearchCLI(engine)
    cli.run()
```

---

### 2.5 Benchmark & Test Fixtures (`benchmark/`)

1. Extract inline sample cards into [`tests/fixtures/sample_cards.json`](tests/fixtures/sample_cards.json:1).
2. Refactor [`benchmark.py`](benchmark.py:1) into [`benchmark/runner.py`](benchmark/runner.py:1).
3. Import `extract_embedding_text` from [`embeddings/text_extractors.py`](embeddings/text_extractors.py:1) instead of [`ingest.py`](ingest.py:1).
4. Clean up duplicate variable declarations (`TH_GRID`, `BATCH_GRID`, `NUM_TEST_CALLS`, `OUTPUT_FILENAME`).

---

## 3. Step-by-Step Implementation Tasks

| Step | Action Item | Target File(s) | Description |
| :--- | :--- | :--- | :--- |
| **1** | Create Test Fixture | [`tests/fixtures/sample_cards.json`](tests/fixtures/sample_cards.json:1) | Extract sample MTG cards JSON array from legacy benchmark. |
| **2** | Implement Search Engine | [`search/engine.py`](search/engine.py:1) | Implement [`CardSearchEngine`](search/engine.py:1) with dependency injection and non-mutating filter logic. |
| **3** | Implement Search CLI & REPL | [`search/cli.py`](search/cli.py:1) | Implement [`InteractiveSearchCLI`](search/cli.py:1) with formatting and `/narrow` command handling. |
| **4** | Refactor [`main.py`](main.py:1) | [`main.py`](main.py:1) | Modernize CLI dispatcher using `argparse` and lazy service instantiation. |
| **5** | Refactor Legacy Bridge | [`search.py`](search.py:1) | Convert legacy [`search.py`](search.py:1) into a clean import-side-effect-free bridge. |
| **6** | Refactor Benchmark Suite | [`benchmark/runner.py`](benchmark/runner.py:1) | Move [`benchmark.py`](benchmark.py:1), remove duplicate variables, use fixture file, and fix extractor imports. |

---

## 4. Acceptance Criteria

- [`CardSearchEngine`](search/engine.py:1) successfully performs vector search without mutating filters in-place.
- [`InteractiveSearchCLI`](search/cli.py:1) correctly executes searches, formats results, and supports `/narrow`.
- [`main.py`](main.py:1) operates cleanly with `argparse` flags (`-s`, `-r`, `--corpus`) without top-level import side effects.
- [`search.py`](search.py:1) launches the interactive REPL successfully when executed directly.
- Benchmark runner executes successfully using [`tests/fixtures/sample_cards.json`](tests/fixtures/sample_cards.json:1) and [`embeddings/text_extractors.py`](embeddings/text_extractors.py:1) without importing ingestion code or launching databases prematurely.
