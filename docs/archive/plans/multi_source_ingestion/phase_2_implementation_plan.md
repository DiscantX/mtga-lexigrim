# Phase 2 Implementation Plan: Multi-Source Ingestion & Vector Architecture

## 1. Executive Summary & Architectural Decisions

This implementation plan details the execution steps for **Phase 2** of the **MTG Expert** project, expanding our ingestion and vector search capabilities beyond Scryfall card printings to encompass official comprehensive game rules ([`corpus/MagicCompRules-20260819.txt`](../corpus/MagicCompRules-20260819.txt)), card rulings ([`corpus/rulings-20260915210031.jsonl`](../corpus/rulings-20260915210031.jsonl)), representative archetype decklists, and foundational strategy literature.

### 1.1 Key Architectural Decision: Dual-Layer Card Rulings Strategy
**Decision**: **Pre-join card rulings into card Qdrant payloads while preserving pure card dense vectors, and maintain a dedicated `mtg_rulings` collection for standalone rules search.**

- **Rationale**:
  1. **Zero Vector Dilution & Drift**: A card's dense embedding vector must capture its core functional semantics (name, type line, mana cost, and oracle text via [`extract_embedding_text()`](../embeddings/text_extractors.py:40) in [`embeddings/text_extractors.py`](../embeddings/text_extractors.py:1)). Baking extensive ruling text into the embedding vector dilutes core mechanics, causing cards with dozens of rulings (e.g. *Blood Moon*, *Animate Dead*) to drift away from functionally similar cards toward a "rules adjudication" cluster.
  2. **Decoupled Payload Enrichment**: Pre-joining rulings from [`corpus/rulings-20260915210031.jsonl`](../corpus/rulings-20260915210031.jsonl) into the card's Qdrant payload (under a `"rulings"` list attribute in [`extract_clean_payload()`](../embeddings/text_extractors.py:3)) provides the AI agent with full edge-case context upon retrieval without polluting vector similarity.
  3. **Dual-Layer Architecture**:
     - **Layer 1 (Card Payload Attachment)**: Instant access to rulings when a card point is retrieved from `mtg_cards`.
     - **Layer 2 (Standalone `mtg_rulings` Collection)**: Vectorizes ruling text independently to enable direct semantic search over rulings when a query asks a general interaction question without naming a card.
  4. **Collections Architecture**:
     - [`mtg_cards`](phase_2_multi_source_ingestion_research.md:48): Card printings with pure dense vectors and enriched payload rulings.
     - [`mtg_rules`](phase_2_multi_source_ingestion_research.md:49): Official comprehensive rules chunked by hierarchical rule ID.
     - [`mtg_rulings`](phase_2_multi_source_ingestion_research.md:50): Standalone card rulings indexed for direct semantic search over rules interactions.
     - [`mtg_decks`](phase_2_multi_source_ingestion_research.md:51): Archetype decklists and card compositions.
     - [`mtg_strategy`](phase_2_multi_source_ingestion_research.md:53): Pedagogical literature, math guides, and theory articles.

---

## 2. Abstract Source Reader Interface

To support heterogeneous data sources without scattering custom parsing logic, we introduce an abstract source reader interface analogous to [`BaseVectorStore`](../vectorstores/base.py:230) ([`vectorstores/base.py`](../vectorstores/base.py:1)) and [`BaseEmbeddingService`](../embeddings/base.py:51) ([`embeddings/base.py`](../embeddings/base.py:1)).

### 2.1 Interface Definition (`ingestion/readers/base.py`)
```python
from abc import ABC, abstractmethod
from typing import Iterator, Dict, Any

class BaseSourceReader(ABC):
    """Abstract base interface for incremental data corpus readers."""
    
    @abstractmethod
    def stream_records(self) -> Iterator[Dict[str, Any]]:
        """Yield raw record dictionaries from the data source."""
        pass
```

### 2.2 Concrete Readers
1. **[`JsonlStreamReader`](../core/streaming.py:116)** ([`core/streaming.py`](../core/streaming.py:1)): Existing memory-safe JSONL reader for cards and rulings.
2. **`TextRuleReader`**: Parses [`corpus/MagicCompRules-20260819.txt`](../corpus/MagicCompRules-20260819.txt) into hierarchical rule records (Chapter > Section > Rule ID).
3. **`MarkdownArticleReader`**: Parses strategy articles and guides into structured chunks with provenance headers.

---

## 3. Configuration & Multi-Collection Qdrant Updates

We will extend [`Settings`](../config/settings.py:7) in [`config/settings.py`](../config/settings.py:1) to support multi-collection routing:

```python
@dataclass
class Settings:
    # Existing settings...
    qdrant_collection_cards: str = "mtg_cards"
    qdrant_collection_rules: str = "mtg_rules"
    qdrant_collection_rulings: str = "mtg_rulings"
    qdrant_collection_decks: str = "mtg_decks"
    qdrant_collection_strategy: str = "mtg_strategy"
```

[`QdrantVectorStore`](../vectorstores/qdrant.py:11) ([`vectorstores/qdrant.py`](../vectorstores/qdrant.py:1)) will accept an optional `collection_name` parameter on upsert and search methods to seamlessly target any of the five collections.

---

## 4. Ingestion Pipelines & Parsers

### 4.1 Comprehensive Rules Parser (`ingestion/parsers/rules_parser.py`)
- Reads [`corpus/MagicCompRules-20260819.txt`](../corpus/MagicCompRules-20260819.txt) line by line.
- Uses regex to detect Chapter headers (e.g., `1. Game Concepts`), Section headers (e.g., `100. General`), and individual rule identifiers (e.g., `100.1a`).
- Generates structured records:
  ```python
  {
      "rule_id": "100.1a",
      "chapter": "1. Game Concepts",
      "section": "100. General",
      "text": "100.1a Two or more players are required to play a traditional game of Magic.",
      "hierarchy_path": "1. Game Concepts > 100. General > 100.1a"
  }
  ```

### 4.2 Card Rulings Pre-Join & Separate Ingestion (`ingestion/pipelines/card_pipeline.py`)
- During card ingestion, [`corpus/rulings-20260915210031.jsonl`](../corpus/rulings-20260915210031.jsonl) is indexed into an in-memory dictionary mapping `oracle_id` -> list of ruling dicts.
- **Payload Pre-Join**: Associated rulings are stored directly in the card's Qdrant payload dictionary (`payload["rulings"]`) via [`extract_clean_payload()`](../embeddings/text_extractors.py:3). The dense embedding text generated by [`extract_embedding_text()`](../embeddings/text_extractors.py:40) remains unpolluted.
- **Standalone Collection Pipeline**: In parallel, ruling entries are streamed into the `mtg_rulings` collection as individual vectorized points carrying `oracle_id`, `card_name`, and `comment`.

---

## 5. AI Search Router & Multi-Collection Dispatch

The Phase 2 search middleware built over [`CardSearchEngine`](../search/engine.py:1) ([`search/engine.py`](../search/engine.py:1)) handles intent routing:

- **Targeted Card Search**: Searches `mtg_cards`. Top results include payload-attached rulings for immediate context rendering.
- **Parallel Rules Interrogation**: When a query asks about general rules interactions, the engine executes **parallel vector queries** across `mtg_rules` and `mtg_rulings`, aggregating rules passages and ruling precedents before generating LLM responses.

---

## 6. Execution Steps & Milestones

1. **Milestone 1**: Implement `BaseSourceReader` interface and refactor [`JsonlStreamReader`](../core/streaming.py:116) to inherit from it.
2. **Milestone 2**: Update [`Settings`](../config/settings.py:7) and [`QdrantVectorStore`](../vectorstores/qdrant.py:11) for multi-collection support across five collections.
3. **Milestone 3**: Build `TextRuleReader` and rules ingestion pipeline for [`corpus/MagicCompRules-20260819.txt`](../corpus/MagicCompRules-20260819.txt).
4. **Milestone 4**: Implement rulings pre-join into card payloads and standalone `mtg_rulings` ingestion pipeline.
5. **Milestone 5**: Implement strategy article ingestion and recursive chunking pipeline.
