# Revised Architecture Plan: Scryfall API Client & Unified Data Download Subsystem

## 1. Directory Structure Adjustment

Per project architecture rules, raw data directories (`data/`, `corpus/`, `.qdrant_storage/`) are reserved strictly for storage artifacts and must never house Python modules. The download, provider, and synchronization mechanisms belong to the ingestion data acquisition layer under [`ingestion/sources/`](ingestion/sources/):

```
ingestion/
├── __init__.py
├── chunking.py
├── orchestrator.py               # IngestionOrchestrator routing corpora to pipelines
├── pipeline.py                   # IngestionPipeline (card corpus)
├── runner.py                     # Standalone runners
├── worker.py                     # IngestionWorker
├── pipelines/
│   ├── __init__.py
│   ├── rules_pipeline.py         # RulesIngestionPipeline
│   ├── rulings_pipeline.py       # RulingsIngestionPipeline
│   ├── strategy_pipeline.py      # StrategyIngestionPipeline
│   └── oracle_tags_pipeline.py   # Stub / NO-OP pipeline for Oracle Tags
├── readers/
│   ├── __init__.py
│   ├── base.py                   # BaseSourceReader
│   ├── markdown_reader.py        # MarkdownArticleReader
│   └── rule_reader.py            # ComprehensiveRulesReader
└── sources/                      # Unified Data Acquisition & Download Subsystem
    ├── __init__.py
    ├── base.py                   # BaseDownloader, BaseDataProvider, and BulkMetadata interfaces
    ├── downloader.py             # Agnostic HttpDownloader with streaming decompression & progress callbacks
    ├── sync.py                   # CorpusSyncManager orchestrating corpus verification & download
    └── scryfall.py               # ScryfallClient implementing BaseDataProvider, rate limits, & bulk mapping
```

---

## 2. Core Abstractions & Agnostic Design

### 2.1 Generic Base Interfaces ([`ingestion/sources/base.py`](ingestion/sources/base.py:1))
- **`BulkMetadata`**: Strongly typed data container holding `name`, `bulk_type` (`oracle_cards`, `default_cards`, `all_cards`, `rulings`, `oracle_tags`), `download_url`, `updated_at`, `compressed_size_bytes`, and `file_format`.
- **`BaseDownloader`**: Abstract base class defining the downloading contract:
  - `download_file(url: str, destination_path: str, decompress_gzip: bool = True, progress_callback: Optional[Callable[[float, str, str], None]] = None) -> str`
- **`BaseDataProvider`**: Abstract base class for endpoints (Scryfall, MTG rules repositories, strategy blogs, etc.):
  - `get_available_bulk_metadata() -> Dict[str, BulkMetadata]`
  - `get_bulk_metadata(bulk_type: str) -> Optional[BulkMetadata]`
  - `fetch_item_by_id(item_id: str) -> Dict[str, Any]` (for future single card/pricing lookups)

### 2.2 Agnostic Streaming Downloader ([`ingestion/sources/downloader.py`](ingestion/sources/downloader.py:1))
- Implements `BaseDownloader` using Python standard library HTTP streams or `urllib.request`.
- Streams in chunks defined by [`Settings.stream_chunk_size`](config/settings.py:64) in [`config/settings.py`](config/settings.py:1).
- Supports streaming inline gzip decompression via `zlib.decompressobj()`, decompressing directly into destination `.jsonl` files without keeping intermediate `.gz` files on disk or inflating memory.
- Fires `progress_callback(percentage: float, speed: str, message: str)` on every chunk to feed progress queues.

### 2.3 Concrete Scryfall Provider ([`ingestion/sources/scryfall.py`](ingestion/sources/scryfall.py:1))
- Implements `BaseDataProvider` specifically targeting `https://api.scryfall.com` and `*.scryfall.io` per [`docs/scryfall_api_documentation.md`](docs/scryfall_api_documentation.md:1):
  - Injects required headers: `User-Agent: LexiGrim/1.0` and `Accept: application/json` ([`docs/scryfall_api_documentation.md:26-33`](docs/scryfall_api_documentation.md:26)).
  - Implements request rate throttling (100ms between calls) and backoff on HTTP 429 ([`docs/scryfall_api_documentation.md:36-49`](docs/scryfall_api_documentation.md:36)).
  - Fetches and parses `GET https://api.scryfall.com/bulk-data` into standardized `BulkMetadata` instances for `oracle_cards`, `default_cards`, `all_cards`, `rulings`, and `oracle_tags`.

---

## 3. Corpus Synchronization Logic ([`ingestion/sources/sync.py`](ingestion/sources/sync.py:1))

The `CorpusSyncManager` orchestrates data acquisition into `corpus/`:

1. **Missing Corpus Detection (Goal A)**:
   - Scans `corpus/` for existing files matching the target type (e.g. `*oracle-cards*.jsonl`, `*rulings*.jsonl`, `*oracle-tags*.jsonl`).
   - If no matching file is found, triggers `download_file()` for the latest bulk URL.
2. **Freshness & Stale Update Detection (Goal B)**:
   - Maintains a local manifest (`corpus/.manifest.json`) recording downloaded file names, types, and their remote `updated_at` ISO timestamps.
   - Compares the provider's current `updated_at` against the local manifest.
   - If remote `updated_at` > local timestamp:
     - Downloads the updated `.jsonl` file.
     - Updates `corpus/.manifest.json`.
     - Optionally archives or removes superseded stale corpus files.
   - If timestamps match, logs that the corpus is up-to-date and skips downloading.

---

## 4. Oracle Tag Handling & Deferred Stub

As requested, Oracle Tag ingestion is deferred:
- **Acquisition**: `CorpusSyncManager` downloads and tracks `oracle_tags` into `corpus/oracle-tags-<timestamp>.jsonl` when requested.
- **Pipeline Stub ([`ingestion/pipelines/oracle_tags_pipeline.py`](ingestion/pipelines/oracle_tags_pipeline.py:1))**:
  - Implements `OracleTagsIngestionPipeline` containing a no-op `run()` method with clear docstrings and comments:
    ```python
    class OracleTagsIngestionPipeline:
        """Pipeline stub for ingesting and associating Scryfall Oracle Tags.
        
        NOTE: Full ingestion and vectorstore payload enrichment for Oracle Tags 
        is currently deferred. This stub provides an interface no-op for future extension.
        """
        def run(self, file_path: str, force_recreate: bool = False) -> None:
            # TODO: Implement Oracle Tags parser and card payload enrichment in Qdrant
            pass
    ```
- **Orchestrator Routing**: [`IngestionOrchestrator.detect_and_run()`](ingestion/orchestrator.py:34) routes `*oracle-tags*.jsonl` files to `OracleTagsIngestionPipeline` without breaking automated full-corpus scans.

---

## 5. UI Integration & Loading Bar Synchronization

The downloader integrates directly with the existing UI and session controller:
1. **Queue Compatibility**: The `progress_callback(percentage, speed, message)` passed to `HttpDownloader` matches the callback in [`LexiGrimSession`](ui/controller.py:73), pushing progress events into [`LexiGrimSession.ingestion_progress_queue`](ui/controller.py:19).
2. **Live Header Rendering**: [`InteractiveCLIShell.render_header()`](ui/cli/app.py:100) displays real-time download percentages and transfer speeds in the terminal dashboard header.
3. **Interactive Commands**:
   - `/sync` in [`InteractiveCLIShell.handle_user_input()`](ui/cli/app.py:127) checks and downloads missing/updated corpora in the background.
   - Dispatcher flag `python main.py --sync` executes synchronization before pipeline ingestion.