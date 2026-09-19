# Architectural Research & Implementation Plan: Scryfall API Client & Unified Data Download Subsystem

## 1. Documentation & Scryfall API Insights

According to [`docs/scryfall_api_documentation.md`](docs/scryfall_api_documentation.md:1) and [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md:13):

1. **Scryfall Bulk Data Endpoint (`GET https://api.scryfall.com/bulk-data`)**:
   - Provides a live catalog of available bulk corpora updated every 12–24 hours ([`docs/scryfall_api_documentation.md:113-205`](docs/scryfall_api_documentation.md:113)).
   - Supports key bulk file types: `oracle_cards` (default for text/rules embedding), `default_cards`, `all_cards`, `rulings`, `oracle_tags`, and `art_tags` ([`docs/scryfall_api_documentation.md:81-96`](docs/scryfall_api_documentation.md:81)).
   - Returns metadata including `id` (UUID), `type` (computer-readable name), `updated_at` (ISO 8601 timestamp), `jsonl_download_uri` (direct download URL), and `compressed_size` (size in bytes) ([`docs/scryfall_api_documentation.md:100-112`](docs/scryfall_api_documentation.md:100)).
2. **Download Protocols & Rate Limiting**:
   - The metadata endpoint (`api.scryfall.com`) requires HTTP headers: `User-Agent` (e.g., `LexiGrim/1.0`) and `Accept: application/json` ([`docs/scryfall_api_documentation.md:26-33`](docs/scryfall_api_documentation.md:26)), with hard rate limits (10 req/sec general, 2 req/sec card search/named/collection, 10 req/min manifest) ([`docs/scryfall_api_documentation.md:36-44`](docs/scryfall_api_documentation.md:36)).
   - Direct download file origins (`*.scryfall.io`) serve gzipped JSONL archives (`.jsonl.gz`) and have **no rate limits** ([`docs/scryfall_api_documentation.md:45`](docs/scryfall_api_documentation.md:45), [`docs/scryfall_api_documentation.md:65-68`](docs/scryfall_api_documentation.md:65)).
3. **Freshness & Update Validation**:
   - Timestamp comparisons (`updated_at`) against local corpus files enable precise detection of whether a file is missing, already up-to-date, or superseded by a newer bulk dump.

---

## 2. Existing Codebase Type Definitions & Locations

The new download subsystem will interact directly with existing core streaming, configuration, orchestration, and UI components:

| Type / Interface / Function | Source Location | Role in Architecture |
| :--- | :--- | :--- |
| [`Settings`](config/settings.py:7) | [`config/settings.py:7`](config/settings.py:7) | Centralized dataclass storing [`Settings.data_corpus_path`](config/settings.py:9), collection names, stream buffer sizes ([`Settings.stream_chunk_size`](config/settings.py:64)), and retry policies. |
| [`BaseSourceReader`](ingestion/readers/base.py:4) | [`ingestion/readers/base.py:4`](ingestion/readers/base.py:4) | Abstract stream reader base class defining [`BaseSourceReader.stream_records()`](ingestion/readers/base.py:8). |
| [`JsonlStreamReader`](core/streaming.py:5) | [`core/streaming.py:5`](core/streaming.py:5) | Memory-safe streaming JSONL decoder yielding records via [`JsonlStreamReader.stream()`](core/streaming.py:23) and counting lines via [`JsonlStreamReader.count_lines()`](core/streaming.py:13). |
| [`IngestionOrchestrator`](ingestion/orchestrator.py:17) | [`ingestion/orchestrator.py:17`](ingestion/orchestrator.py:17) | Auto-routes corpus files to pipelines via [`IngestionOrchestrator.detect_and_run()`](ingestion/orchestrator.py:34) and executes full discovery via [`IngestionOrchestrator.run_all()`](ingestion/orchestrator.py:100). |
| [`IngestionPipeline`](ingestion/pipeline.py:46) | [`ingestion/pipeline.py:46`](ingestion/pipeline.py:46) | Card corpus producer-consumer pipeline executed via [`IngestionPipeline.run()`](ingestion/pipeline.py:67). |
| [`RulingsIngestionPipeline`](ingestion/pipelines/rulings_pipeline.py:16) | [`ingestion/pipelines/rulings_pipeline.py:16`](ingestion/pipelines/rulings_pipeline.py:16) | Card rulings pipeline executed via [`RulingsIngestionPipeline.run()`](ingestion/pipelines/rulings_pipeline.py:31). |
| [`RulesIngestionPipeline`](ingestion/pipelines/rules_pipeline.py:16) | [`ingestion/pipelines/rules_pipeline.py:16`](ingestion/pipelines/rules_pipeline.py:16) | Comprehensive game rules pipeline executed via [`RulesIngestionPipeline.run()`](ingestion/pipelines/rules_pipeline.py:31). |
| [`StrategyIngestionPipeline`](ingestion/pipelines/strategy_pipeline.py:14) | [`ingestion/pipelines/strategy_pipeline.py:14`](ingestion/pipelines/strategy_pipeline.py:14) | Markdown strategy article pipeline executed via [`StrategyIngestionPipeline.run()`](ingestion/pipelines/strategy_pipeline.py:28). |
| [`LexiGrimSession`](ui/controller.py:9) | [`ui/controller.py:9`](ui/controller.py:9) | Interactive controller managing background threads via [`LexiGrimSession.trigger_background_ingestion()`](ui/controller.py:60) and feeding [`LexiGrimSession.ingestion_progress_queue`](ui/controller.py:19). |
| [`InteractiveCLIShell`](ui/cli/app.py:18) | [`ui/cli/app.py:18`](ui/cli/app.py:18) | CLI interface rendering live status headers via [`InteractiveCLIShell.render_header()`](ui/cli/app.py:100) and parsing slash commands in [`InteractiveCLIShell.handle_user_input()`](ui/cli/app.py:127). |

---

## 3. Architecture & Design Plan: Unified Download Subsystem

To adhere to the project's strict modular, object-oriented, and provider-agnostic standards ([`docs/ARCHITECTURE.md:13-19`](docs/ARCHITECTURE.md:13)), we decouple generic HTTP downloading, data provider querying, and corpus lifecycle management.

```
data/
├── __init__.py
├── base.py                   # Agnostic BaseDownloader, BaseDataProvider, and BulkMetadata interfaces
├── downloader.py             # Agnostic HttpDownloader with streaming decompression and progress callbacks
├── sync.py                   # CorpusSyncManager orchestrating missing/updated dataset checks
└── providers/
    ├── __init__.py
    ├── scryfall.py           # Concrete ScryfallClient implementing BaseDataProvider & Scryfall rate limits
    └── web_articles.py       # Future provider for MTG strategy articles and web content
```

### 3.1 Generic Abstract Interfaces ([`data/base.py`](data/base.py:1))
1. **`BulkMetadata`**: Lightweight dataclass containing `name`, `bulk_type`, `download_url`, `updated_at`, `compressed_size_bytes`, and `file_format` (`.jsonl.gz`, `.txt`, `.md`).
2. **`BaseDownloader`**: Abstract interface for downloading streams:
   - `download_file(url: str, destination_path: str, decompress_gzip: bool = True, progress_callback: Optional[Callable[[float, str, str], None]] = None) -> str`
3. **`BaseDataProvider`**: Abstract interface for data sources:
   - `get_available_bulk_metadata() -> Dict[str, BulkMetadata]`
   - `get_bulk_metadata(bulk_type: str) -> Optional[BulkMetadata]`
   - `fetch_item_by_id(item_id: str) -> Dict[str, Any]` (for future single card/pricing lookups)

### 3.2 Agnostic Streaming Downloader ([`data/downloader.py`](data/downloader.py:1))
- Implements `BaseDownloader` using streaming HTTP chunks (`stream_chunk_size` from [`Settings`](config/settings.py:7)).
- Features inline on-the-fly decompression using standard library `gzip` / `zlib.decompressobj()`, avoiding writing intermediate `.gz` files to disk if uncompressed `.jsonl` is desired, while keeping memory consumption bounded.
- Emits progress updates via `progress_callback(percentage: float, speed: str, message: str)` matching the existing signature in [`LexiGrimSession`](ui/controller.py:73).

### 3.3 Scryfall Data Provider ([`data/providers/scryfall.py`](data/providers/scryfall.py:1))
- Implements `BaseDataProvider` specifically for Scryfall:
  - Enforces required `User-Agent` and `Accept` headers.
  - Implements a request throttler respecting the 100ms rate limit and handling HTTP 429 backoff.
  - Queries `https://api.scryfall.com/bulk-data` and normalizes records into `BulkMetadata` objects for `oracle_cards`, `default_cards`, `all_cards`, `rulings`, and `oracle_tags`.

### 3.4 Corpus Synchronization Manager ([`data/sync.py`](data/sync.py:1))
- Manages datasets in `corpus/` by maintaining a manifest (`corpus/.manifest.json`):
  1. **Missing Corpus Detection**: If a requested corpus (`oracle_cards`, `rulings`, `oracle_tags`) does not exist on disk, it triggers the download.
  2. **Update Detection**: Queries the provider's `updated_at` timestamp. If newer than the local manifest timestamp, downloads the latest export and replaces or archives the stale corpus.
  3. **No-Op / Cache Preservation**: Skips downloads when local files are current.
- Integrates with [`IngestionOrchestrator.run_all()`](ingestion/orchestrator.py:100) to ensure the vector database can be automatically refreshed with minimal manual intervention.

### 3.5 Planning for Oracle Tags (`oracle_tags`)
- Oracle tags map community-curated gameplay classifications to `oracle_id`.
- The download subsystem will pull `oracle_tags` into `corpus/oracle-tags-<timestamp>.jsonl`.
- Future ingestion will introduce an [`OracleTagsIngestionPipeline`](ingestion/pipelines/oracle_tags_pipeline.py:1) or enrich card payload attributes in [`IngestionPipeline`](ingestion/pipeline.py:46) to support advanced semantic query filters (e.g. tag-based narrowing in [`CardSearchEngine`](search/engine.py:1)).

---

## 4. UI Integration & CLI Workflow

1. **Terminal Header Progress**: [`InteractiveCLIShell.render_header()`](ui/cli/app.py:100) and [`LexiGrimSession`](ui/controller.py:9) will render download progress percentage, transfer rate (e.g., `5.4 MB/s`), and file status seamlessly via the existing queue mechanism.
2. **Commands**:
   - `/sync [type]` (e.g., `/sync oracle_cards` or bare `/sync`): Triggers background corpus checking, downloading, and subsequent ingestion.
   - CLI flag `python main.py --sync` to check and download required corpora prior to pipeline execution.