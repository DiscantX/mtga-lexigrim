# Architectural & Design Decisions (ADRs)

This document records key architectural decisions, rationale, and trade-offs for the **MTG Expert** project.

---

## 1. Direct JSON Streaming Dictionaries (`dict[str, Any]`) over Python Dataclasses for Bulk Ingestion

- **Context**: Early iterations attempted to instantiate strongly-typed `Card` dataclass objects for every record in the 100,000+ card Scryfall JSONL corpus.
- **Problem**: Instantiating 100,000+ complex dataclasses created massive garbage collection (GC) pressure, memory allocations, and CPU overhead. Furthermore, `card_model.py` suffered from missing imports (`fields`) and brittle schemas.
- **Decision**: Completely removed `card_model.py` and `utils/card_dataclass_generator.py`. Stream raw JSON records directly as dictionaries (`dict[str, Any]`) via [`JsonlStreamReader`](../core/streaming.py:116) and extract payloads using lightweight functions ([`extract_clean_payload()`](../embeddings/text_extractors.py:176)).
- **Consequence**: Kept memory flat during bulk ingestion and achieved maximum streaming throughput.

---

## 2. Decoupled Producer-Consumer Ingestion Architecture

- **Context**: Empirical benchmarking revealed conflicting optimal batch sizes:
  - Local CPU matrix math (`FastEmbed`) peaks in throughput at small batch sizes (`2` to `4`).
  - Remote database network roundtrips to Qdrant incur a fixed ~2.08s overhead per call, requiring large batch sizes (`128+`) for optimal network utilization.
- **Decision**: Implemented a producer-consumer architecture ([`IngestionPipeline`](../ingestion/pipeline.py:1) and [`IngestionWorker`](../ingestion/worker.py:1)) connected via a thread-safe `queue.Queue`.
  - **Single Background Upsert Worker**: To prevent concurrent file-lock contention on local embedded Qdrant (RocksDB storage), exactly one worker thread executes sequential batched upserts.
- **Consequence**: Decoupled local embedding generation from remote database latency, maximizing overall pipeline throughput.

---

## 3. Abstract Provider Interfaces (`BaseVectorStore`, `BaseEmbeddingService`)

- **Context**: The codebase was initially tightly coupled to Qdrant constructs and FastEmbed classes.
- **Decision**: Introduced abstract base classes [`BaseVectorStore`](../vectorstores/base.py:230) and [`BaseEmbeddingService`](../embeddings/base.py:51) enforcing strict provider contracts.
- **Consequence**: The system is now fully agnostic. Future migrations to alternative vector databases (e.g., pgvector, Chroma) or embedding backends (e.g., OpenAI, Ollama) require zero changes to core business logic.

---

## 4. Non-Mutating Filter Construction in Search

- **Context**: In legacy search code, appending candidate IDs for narrowing mutated caller query filters in place.
- **Problem**: Repeated searches caused candidate IDs to accumulate monotonically on the original filter object.
- **Decision**: Refactored [`CardSearchEngine.vector_search()`](../search/engine.py:32) to construct a fresh `models.Filter` combination without mutating input parameters.
- **Consequence**: Eliminated state leakage and ensured reliable, stateless cascading searches.

---

## 5. The "Rounding" Principle ("Do Rounding/Truncation Last")

- **Context**: Designing search narrowing and result ranking.
- **Decision**: Adhered strictly to the core principle: *"Carry the full value until the final display operation (do rounding/truncation last)."*
- **Consequence**: Cascading sub-searches constrain queries within valid candidate ID sets while preserving all qualifying candidate data until final display rendering.

---

## 6. Dual-Dataset Strategy (`oracle_cards` vs. `default_cards`) & Short-Term Deduplication

- **Context**: Ingesting the Scryfall `default_cards` dataset introduced numerous duplicate printings for functionally identical cards (reprints), generating search noise and diluting relevance ranking.
- **Decision**: 
  1. Adopt **`oracle_cards`** as the default and primary corpus for AI development, rules interrogation, and deckbuilding ([`docs/ARCHITECTURE.md`](ARCHITECTURE.md:1)), ensuring a 1:1 mapping per unique card concept (`oracle_id`).
  2. Maintain architectural extensibility to support **`default_cards`** optionally for collector-oriented workflows.
  3. Implement short-term post-processing deduplication by `oracle_id` in [`CardSearchEngine.vector_search()`](../search/engine.py:13) ([`search/engine.py`](../search/engine.py:6)) when querying reprint-heavy corpora, ensuring clean search results prior to a full database rebuild.
- **Consequence**: Keeps search relevance high, reduces search noise, and adheres to modular, agnostic design principles ([`docs/DECISIONS.md`](DECISIONS.md:1)) while supporting diverse ingestion sources.

---

## 7. Unified Data Download Subsystem & Agnostic Downloader

- **Context**: Automated retrieval of Scryfall bulk data required robust rate-limiting, header compliance, streaming decompression, and timestamp-based freshness tracking.
- **Decision**: 
  1. Implemented abstract base interfaces (`BaseDownloader`, `BaseDataProvider`) in [`ingestion/sources/base.py`](../ingestion/sources/base.py:1).
  2. Implemented `HttpDownloader` using standard library `urllib` and `zlib.decompressobj()` for on-the-fly streaming gzip decompression without intermediate `.gz` disk writes.
  3. Implemented `ScryfallClient` adhering to Scryfall API rate limits (100ms intervals, 429 exponential backoffs) and required headers (`User-Agent`, `Accept`).
  4. Implemented `CorpusSyncManager` managing corpus synchronization and manifest tracking (`corpus/.manifest.json`).
- **Consequence**: Automated data acquisition with flat memory usage, robust telemetry integration, and seamless UI/CLI synchronization support.
