# Qdrant Card Payload Schema & Field Filtering Documentation

This document records the whitelist of retained fields vs excluded fields in [`ingest.py`](ingest.py:1) when upserting Magic: The Gathering card data into Qdrant.

---

## 1. Retained Fields (Included in Qdrant Payload)
These fields are stored in Qdrant point payloads to support AI semantic search results, frontend rendering, and database filtering:

*   **Core Identity & Rules**:
    *   `id`: Unique Scryfall UUID for the printing.
    *   `oracle_id`: Canonical UUID for the card concept.
    *   `name`: Card name.
    *   `lang`: Card language (e.g. `"en"`).
    *   `mana_cost`: Mana cost string (e.g. `"{1}{U}"`).
    *   `cmc`: Converted mana cost / mana value (indexed integer/float).
    *   `type_line`: Type line (e.g. `"Instant"`).
    *   `oracle_text`: Rules text.
    *   `colors`: Color array (indexed keyword).
    *   `color_identity`: Color identity array.
    *   `keywords`: Keyword abilities array.
    *   `power`, `toughness`, `loyalty`, `defense`: Stat strings.
    *   `card_faces`: Double-faced card face details.
*   **Set & Edition Metadata**:
    *   `set`: Set code (e.g. `"neo"`).
    *   `set_id`: Set UUID.
    *   `set_name`: Full set name.
    *   `set_type`: Type of set.
    *   `collector_number`: Collector number within set.
    *   `rarity`: Rarity string.
    *   `released_at`: Release date.
*   **Media & Rendering**:
    *   `image_uris`: CDN image URLs (`small`, `normal`, `art_crop`, etc.).
*   **Legalities**:
    *   `legalities`: Format legalities dictionary (used by [`search.py`](search.py:1) filters).

---

## 2. Excluded Fields (Dropped from Qdrant Payload)
To achieve an ~80% reduction in Qdrant storage and memory footprint, the following non-essential or reconstructible fields are stripped during ingestion:

*   **API & Web URIs** (Reconstructible from `id` / `set`):
    *   `uri`, `scryfall_uri`, `rulings_uri`, `scryfall_set_uri`, `set_uri`, `set_search_uri`, `prints_search_uri`
*   **External Links & Affiliate Dictionaries**:
    *   `related_uris`, `purchase_uris`
*   **Stale Financial Data**:
    *   `prices` (`usd`, `eur`, `tix`, etc.)
*   **Cross-Platform ID Lists**:
    *   `multiverse_ids`, `mtgo_id`, `mtgo_foil_id`, `tcgplayer_id`, `tcgplayer_etched_id`, `cardmarket_id`, `arena_id`, `artist_ids`, `illustration_id`
*   **Printing & Object Metadata**:
    *   `object`, `booster`, `border_color`, `full_art`, `story_spotlight`, `textless`, `variation`, `oversized`, `game_changer`, `highres_image`, `image_status`, `image_updated_at`, `finishes`, `promo_types`, `games`, `all_parts`, `preview`
