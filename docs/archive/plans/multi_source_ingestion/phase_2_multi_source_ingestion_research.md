# Phase 2 Research & Planning: Multi-Source Data Ingestion and Qdrant Architecture

## 1. Executive Summary

This document outlines the architectural research, design decisions, and planning strategies for **Phase 2** of the **MTG Expert** project. Building upon the stable foundation of **Phase 1** (Scryfall card ingestion, vector storage, and semantic search via [`IngestionPipeline`](ingestion/pipeline.py:21) and [`QdrantVectorStore`](vectorstores/qdrant.py:11)), Phase 2 expands ingestion capabilities to encompass official game rules ([`corpus/MagicCompRules-20260819.txt`](corpus/MagicCompRules-20260819.txt)), card rulings ([`corpus/rulings-20260915210031.jsonl`](corpus/rulings-20260915210031.jsonl)), archetype deck examples, and advanced strategy literature. 

This document synthesizes our architectural analysis regarding collection structuring, hierarchical text chunking, dual-layer card ruling integration, incremental delta synchronization via content hashing, web scraping via `Crawl4AI`, LLM-assisted classification, authority weighting, and future agentic web retrieval middleware.

---

## 2. Project Context & Objectives

As established in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md:1) and [`docs/PLANS.md`](docs/PLANS.md:1), the long-term goal of **MTG Expert** is to create an advanced AI assistant capable of deckbuilding, synergy analysis, rules interrogation, and meta-game understanding. 

To achieve expert-level proficiency, the system requires structured access to:

1. **Official Game Rules**: For precise adjudication of complex rules interactions, sequencing, and game state mechanics.
2. **Card Rulings**: For edge-case interactions tied to specific cards.
3. **Deck Examples / Meta Archetypes**: For guiding archetype construction and synergy analysis.
4. **Strategy Literature & Guides**: For establishing foundational reasoning, mana curves, role assignment (beatdown vs. control), and mathematical mana base sizing.

---

## 3. Analysis of Additional Data Sources

### 3.1 Official Comprehensive Game Rules ([`corpus/MagicCompRules-20260819.txt`](corpus/MagicCompRules-20260819.txt))

- **Structure**: Hierarchical plain text document structured into chapters (e.g., `1. Game Concepts`), numbered sections (e.g., `100. General`), and alphanumeric rules (`100.1a`), concluding with a glossary.
- **Challenge**: Rules lack standalone meaning without contextual hierarchy. Embedding rule text in isolation strips away essential scope.

### 3.2 Card Rulings ([`corpus/rulings-20260915210031.jsonl`](corpus/rulings-20260915210031.jsonl))

- **Structure**: JSONL stream linking card concepts (`oracle_id`) to specific ruling notes, sources, and publication dates.
- **Dual-Layer Architecture Strategy**:
  - **Vector Dilution Warning**: Baking ruling text into card dense embedding vectors dilutes core card semantics (name, type, mana cost, oracle text formatted in [`extract_embedding_text()`](embeddings/text_extractors.py:40) in [`embeddings/text_extractors.py`](embeddings/text_extractors.py:1)). Cards with 10-30 rulings (e.g. *Blood Moon*, *Animate Dead*) would drift away from functionally similar cards toward a "rules adjudication" vector space.
  - **Payload Attachment**: Pre-join ruling lists into the `mtg_cards` Qdrant **payload** dictionary (`payload["rulings"]`), providing immediate context to the AI agent upon card retrieval without polluting the card's embedding vector.
  - **Standalone Vector Space**: Ingest rulings independently into a dedicated `mtg_rulings` vector collection to support direct semantic queries over ruling precedents (e.g., "What happens when copying a modal spell?").

### 3.3 Strategy Literature & Guides (Reid Duke's *Level One*, Mike Flores' *Who's the Beatdown?*, Frank Karsten's Mana Math)

- **Structure**: Unstructured long-form prose and articles covering foundational theory, math formulas, and matchup philosophy.
- **Challenge**: Raw LLMs struggle with quantitative synthesis (land counts) and abstract role assignment. Ingesting pedagogical literature provides essential semantic and mathematical anchors.

---

## 4. Database Architecture: Dedicated Collections Strategy

To store heterogeneous data sources in Qdrant ([`vectorstores/qdrant.py`](vectorstores/qdrant.py:11)), we adopt **dedicated collections**, implementing the abstract interface defined in [`BaseVectorStore`](vectorstores/base.py:4):

- `mtg_cards`: Scryfall card printings with pure dense vectors and enriched payload rulings ([`docs/payload_schema.md`](docs/payload_schema.md:1)).
- `mtg_rules`: Official parsed comprehensive rules.
- `mtg_rulings`: Card-specific oracle rulings indexed for direct semantic search over rules interactions.
- `mtg_decks`: Archetype decklists.
- `mtg_strategy`: Foundational strategy literature, theory, and curated guides.

#### Rationale:

1. **Clean Schema Isolation**: Different data types do not share attributes, preventing sparse, bloated payloads and schema pollution.
2. **Optimized Semantic Spaces**: Queries target specific collections based on user intent, maximizing vector similarity precision.
3. **Pristine Vector Semantics**: Isolating card vectors from ruling text prevents semantic drift while maintaining full ruling context in payload metadata.
4. **Modular Alignment**: Aligns cleanly with our strongly-typed [`Settings`](config/settings.py:54) configuration ([`config/settings.py`](config/settings.py:1)) and Qdrant client architecture.

---

## 5. Web Acquisition, Scraping, & LLM-Assisted Classification

### 5.1 RSS & `Crawl4AI` Integration

- **RSS Discovery**: Using RSS feeds (e.g., [`https://mtgdecks.net/articles/feed.rss`](https://mtgdecks.net/articles/feed.rss)) provides a chronological stream of immutable article URLs and publication timestamps.
- **Crawl4AI**: Open-source, LLM-friendly crawler that renders JavaScript and extracts clean Markdown while stripping away boilerplate navigation, ads, and footers.

### 5.2 LLM-Assisted Pre-Ingestion Classification

To prevent manual tagging bottlenecks and noisy ingestion:

- **Gemini Flash Preprocessing**: During acquisition, the scraper passes article metadata and summary text to Google Gemini to automatically generate a structured classification payload:

  - `article_type`: Classified into `GUIDES`, `THEORY`, `META`, `NEWS`, `SPOILERS`, `LIMITED`, etc.
  - `authority_tier`: Graded from Tier 1 (canonical/evergreen, e.g., Frank Karsten, Reid Duke) to Tier 3.
  - `evergreen`: Boolean flag (`true` for math/theory, `false` for transient listicles).
  - `semantic_summary`: A concise abstract prepended to chunks for enhanced retrieval.
- **Gatekeeper Filtering**: Automatically drops transient categories like `NEWS` or `SPOILERS` to keep Qdrant uncluttered.

---

## 6. Chunking, Text Formulation, & Hierarchical Context

### 6.1 Game Rules Chunking Strategy

- Each individual rule forms an independent Qdrant point, prepended with its hierarchical path (Chapter > Section > Rule ID).

### 6.2 Strategy Articles Normalization & Chunking

- **Intermediate Schema**: Standardized `StrategyArticle` dict structure.
- **Recursive Chunking**: Split long-form prose into 512–1024 token chunks with ~10% overlap.
- **Provenance Header Prepending**:
  ```python
  def format_chunk_for_embedding(article: dict, chunk_text: str, chunk_idx: int) -> str:
      return (
          f"Source: {article['source']} | Title: {article['title']} | "
          f"Author: {article.get('author', 'Unknown')} | Section Part {chunk_idx + 1}\n\n"
          f"{chunk_text}"
      )
  ```

---

## 7. Incremental Ingestion, Updates, & Content Hashing

To handle incremental updates (errata, banned lists, rule revisions), we implement a **Content Hashing & Delta Synchronization** pattern using cryptographic SHA-256 hashes over embedding text and core payload filters. Unchanged records are skipped (`card_id in existing_ids` + matching hash), while modified records trigger clean upsert overwrites.

---

## 8. AI Layer Interaction & Future Agentic Web Retrieval

### 8.1 Intent-Driven Retrieval Router & Parallel Search

The Phase 2 AI agent middleware (built over [`CardSearchEngine`](search/engine.py:6) in [`search/engine.py`](search/engine.py:1)) routes queries to dedicated collections (`mtg_cards`, `mtg_rules`, `mtg_rulings`, `mtg_decks`, `mtg_strategy`):

- **Targeted Single-Collection Search**: Card synergy and deck queries route directly to `mtg_cards` (with attached ruling payloads returned automatically).
- **Parallel Multi-Collection Rules Search**: Complex rules and judge questions trigger **parallel asynchronous vector searches** across `mtg_rules` and `mtg_rulings`. The query engine aggregates relevant Comprehensive Rules passages and ruling precedents before passing context to the LLM.

### 8.2 On-the-Fly Web Retrieval & Tool Calling

- **Decoupled Scraping Services**: By structuring scrapers, cleaners, and the [`FastEmbedProvider`](embeddings/fastembed_provider.py:85) ([`embeddings/fastembed_provider.py`](embeddings/fastembed_provider.py:1)) as modular services, the future AI agent can invoke dynamic tools (e.g., `fetch_web_article(url)`) to generate ephemeral embeddings for breaking rules or tournament lists on the fly.

---

## 9. Deferred Research Items

- **Embedding of Metadata**: The question of whether to explicitly bake categorical attributes (colors, color identity, format legalities) into embedding text vectors versus keeping them strictly in Qdrant payloads ([`docs/payload_schema.md`](docs/payload_schema.md:1)) remains **deferred** for further research.
