# MTG Expert Changelog

All notable changes to this project will be documented in this file.

---

## [1.1.0] - 2026-09-19 (Scryfall API Client & Unified Data Download Subsystem)

### Added
- **Unified Data Acquisition & Download Subsystem** ([`ingestion/sources/`](../ingestion/sources/)):
  - Abstract base contracts [`BulkMetadata`](../ingestion/sources/base.py:1), [`BaseDownloader`](../ingestion/sources/base.py:1), and [`BaseDataProvider`](../ingestion/sources/base.py:1) in [`ingestion/sources/base.py`](../ingestion/sources/base.py:1).
  - Agnostic streaming downloader [`HttpDownloader`](../ingestion/sources/downloader.py:1) ([`ingestion/sources/downloader.py`](../ingestion/sources/downloader.py:1)) supporting chunked downloads and on-the-fly streaming gzip decompression via `zlib.decompressobj()`.
  - Concrete Scryfall API client [`ScryfallClient`](../ingestion/sources/scryfall.py:1) ([`ingestion/sources/scryfall.py`](../ingestion/sources/scryfall.py:1)) with required compliance headers (`User-Agent`, `Accept`), rate limiting (100ms throttle), and HTTP 429 exponential backoff retry logic.
  - Corpus synchronization manager [`CorpusSyncManager`](../ingestion/sources/sync.py:1) ([`ingestion/sources/sync.py`](../ingestion/sources/sync.py:1)) supporting missing corpus detection, timestamp freshness verification against remote `updated_at`, manifest persistence (`corpus/.manifest.json`), and stale file cleanup.
- **Oracle Tags Pipeline Stub**: Added [`OracleTagsIngestionPipeline`](../ingestion/pipelines/oracle_tags_pipeline.py:1) ([`ingestion/pipelines/oracle_tags_pipeline.py`](../ingestion/pipelines/oracle_tags_pipeline.py:1)) as a documented no-op stub for future semantic tag integration.
- **UI & CLI Integration**:
  - Added background sync support (`LexiGrimSession.trigger_background_sync()`) and live progress telemetry in [`LexiGrimSession`](../ui/controller.py:1) and [`InteractiveCLIShell`](../ui/cli/app.py:1).
  - Added interactive `/sync [type]` command in [`InteractiveCLIShell`](../ui/cli/app.py:1).
  - Added `--sync [type]` CLI flag in [`main.py`](../main.py:1) for automated corpus acquisition and ingestion prior to execution.

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
