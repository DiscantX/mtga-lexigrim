# MTG Expert Changelog

All notable changes to this project will be documented in this file.

---

## [1.0.0] - 2026-09-17 (Major Architectural Refactor & Phase 1-4 Completion)

### Added
- **Centralized Configuration**: Added [`config/settings.py`](../config/settings.py:1) for strongly-typed configuration and environment variable overrides.
- **Core Utilities**: Added [`core/streaming.py`](../core/streaming.py:1) for memory-safe JSONL streaming parser and [`core/timer.py`](../core/timer.py:1) for thread-safe performance telemetry.
- **Storage & Embedding Abstractions**: Introduced abstract base interfaces [`BaseVectorStore`](../vectorstores/base.py:1) ([`vectorstores/base.py`](../vectorstores/base.py:1)) and [`BaseEmbeddingService`](../embeddings/base.py:1) ([`embeddings/base.py`](../embeddings/base.py:1)).
- **Qdrant Vector Store & Service Manager**: Implemented [`QdrantVectorStore`](../vectorstores/qdrant.py:1) ([`vectorstores/qdrant.py`](../vectorstores/qdrant.py:1)) and cross-platform [`QdrantServiceManager`](../vectorstores/service_manager.py:1) ([`vectorstores/service_manager.py`](../vectorstores/service_manager.py:1)).
- **FastEmbed Provider & Text Extractors**: Implemented [`FastEmbedProvider`](../embeddings/fastembed_provider.py:1) ([`embeddings/fastembed_provider.py`](../embeddings/fastembed_provider.py:1)) with thread-safe LRU caching and [`embeddings/text_extractors.py`](../embeddings/text_extractors.py:1) for card payload cleaning and single/double-faced oracle text formatting.
- **Object-Oriented Ingestion Pipeline**: Implemented producer-consumer pipeline [`IngestionPipeline`](../ingestion/pipeline.py:1) ([`ingestion/pipeline.py`](../ingestion/pipeline.py:1)) and background worker [`IngestionWorker`](../ingestion/worker.py:1) ([`ingestion/worker.py`](../ingestion/worker.py:1)).
- **Object-Oriented Search & REPL CLI**: Implemented [`CardSearchEngine`](../search/engine.py:1) ([`search/engine.py`](../search/engine.py:1)) with non-mutating filter logic and [`InteractiveSearchCLI`](../search/cli.py:1) ([`search/cli.py`](../search/cli.py:1)) supporting `/narrow` query refinement.
- **Modernized CLI Dispatcher**: Refactored [`main.py`](../main.py:1) to use `argparse` with lazy service initialization and zero import-time side-effects.
- **Formal Documentation**: Created [`ARCHITECTURE.md`](ARCHITECTURE.md:1), [`PLANS.md`](PLANS.md:1), [`CHANGELOG.md`](CHANGELOG.md:1), [`DECISIONS.md`](DECISIONS.md:1), and root [`AGENTS.md`](../AGENTS.md:1), archiving legacy ad-hoc documents into `archive/`.

### Changed
- Refactored monolithic scripts (`ingest.py`, `search.py`, `qdrant_manager.py`, `card_model.py`) into structured thematic packages.
- Retired legacy ad-hoc docs and moved them to `archive/`.

### Removed
- Removed orphaned and defective `card_model.py` and `utils/card_dataclass_generator.py`.
