# MTG Expert Implementation Plans & Roadmap

This document outlines the master development roadmap and historical execution plans for the **MTG Expert** project.

---

## 1. Project Roadmap Summary

- **Phase 1: Foundation, Configuration & Core Utilities** ([`archive/plans/phase_1_foundation_and_core.md`](archive/plans/phase_1_foundation_and_core.md:1)): **Completed & Stable**. Established directory layout, centralized settings ([`config/settings.py`](../config/settings.py:1)), memory-safe JSONL streaming ([`core/streaming.py`](../core/streaming.py:1)), and thread-safe telemetry ([`core/timer.py`](../core/timer.py:1)).
- **Phase 2: Storage & Embedding Abstractions** ([`archive/plans/phase_2_storage_and_embeddings.md`](archive/plans/phase_2_storage_and_embeddings.md:1)): **Completed & Stable**. Implemented abstract base interfaces (`BaseVectorStore`, `BaseEmbeddingService`), FastEmbed provider with thread-safe LRU caching ([`embeddings/fastembed_provider.py`](../embeddings/fastembed_provider.py:1)), text extractors ([`embeddings/text_extractors.py`](../embeddings/text_extractors.py:1)), Qdrant vector store ([`vectorstores/qdrant.py`](../vectorstores/qdrant.py:1)), and cross-platform service manager ([`vectorstores/service_manager.py`](../vectorstores/service_manager.py:1)).
- **Phase 3: Ingestion Pipeline Refactoring** ([`archive/plans/phase_3_ingestion_pipeline.md`](archive/plans/phase_3_ingestion_pipeline.md:1)): **Completed & Stable**. Replaced procedural ingestion scripts with an object-oriented producer-consumer pipeline ([`IngestionPipeline`](../ingestion/pipeline.py:1)) and [`IngestionWorker`](../ingestion/worker.py:1) featuring inline stream pipelining, flat memory footprint, and exponential backoff retries.
- **Phase 4: Search Engine, CLI & Benchmarking** ([`archive/plans/phase_4_search_cli_benchmark.md`](archive/plans/phase_4_search_cli_benchmark.md:1) & [`archive/plans/interactive_search_and_narrowing.md`](archive/plans/interactive_search_and_narrowing.md:1)): **Completed & Stable**. Implemented object-oriented search engine ([`CardSearchEngine`](../search/engine.py:1)), interactive REPL CLI supporting `/narrow` query refinement ([`InteractiveSearchCLI`](../search/cli.py:1)), clean `argparse` dispatcher ([`main.py`](../main.py:1)), benchmark test suites, and mock fixtures ([`tests/fixtures/sample_cards.json`](../tests/fixtures/sample_cards.json:1)).
- **Phase 5 (Upcoming): AI Integration & Chatbot Interface**: To be initiated once Phase 1 data ingestion and vector search are fully verified in production. Will introduce provider/model agnostic middleware (starting with Google Gemini) for deckbuilding assistance, synergy analysis, and rules interrogation.

---

## 2. Historical Implementation Plans Index

All detailed historical implementation plans developed during the refactor are preserved in the archive folder:
- [`archive/plans/phase_1_foundation_and_core.md`](archive/plans/phase_1_foundation_and_core.md:1)
- [`archive/plans/phase_2_storage_and_embeddings.md`](archive/plans/phase_2_storage_and_embeddings.md:1)
- [`archive/plans/phase_3_ingestion_pipeline.md`](archive/plans/phase_3_ingestion_pipeline.md:1)
- [`archive/plans/phase_4_search_cli_benchmark.md`](archive/plans/phase_4_search_cli_benchmark.md:1)
- [`archive/plans/interactive_search_and_narrowing.md`](archive/plans/interactive_search_and_narrowing.md:1)
- [`archive/plans/refactor.md`](archive/plans/refactor.md:1)
- [`archive/plans/SYSTEM ARCHITECTURE REFACTOR TASK - INGESTION PIPELINE OPTIMIZATION.md`](archive/plans/SYSTEM%20ARCHITECTURE%20REFACTOR%20TASK%20-%20INGESTION%20PIPELINE%20OPTIMIZATION.md:1)
