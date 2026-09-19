import json
import time
import urllib.request
import urllib.error
from typing import Dict, Any, Optional
from ingestion.sources.base import BaseDataProvider, BulkMetadata


class ScryfallClient(BaseDataProvider):
    """Concrete data provider for Scryfall REST API and bulk data catalogs."""

    BULK_TYPES_MAP = {
        "oracle_cards": "oracle_cards",
        "default_cards": "default_cards",
        "all_cards": "all_cards",
        "rulings": "rulings",
        "oracle_tags": "oracle_tags"
    }

    def __init__(self, request_delay: float = 0.1, max_retries: int = 3):
        self.request_delay = request_delay
        self.max_retries = max_retries
        self._last_request_time = 0.0

    def _throttle(self) -> None:
        """Enforce rate limiting (minimum request_delay seconds between calls)."""
        now = time.time()
        elapsed = now - self._last_request_time
        if elapsed < self.request_delay:
            time.sleep(self.request_delay - elapsed)
        self._last_request_time = time.time()

    def _make_request(self, url: str) -> Dict[str, Any]:
        """Make HTTP GET request with required headers, throttling, and 429 backoff retry logic."""
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "LexiGrim/1.0",
                "Accept": "application/json"
            }
        )

        backoff = 1.0
        for attempt in range(self.max_retries):
            self._throttle()
            try:
                with urllib.request.urlopen(req) as response:
                    data = response.read().decode("utf-8")
                    return json.loads(data)
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    if attempt == self.max_retries - 1:
                        raise RuntimeError(f"Scryfall API rate limit exceeded (429) after {self.max_retries} attempts.")
                    time.sleep(backoff)
                    backoff *= 2.0
                    continue
                raise RuntimeError(f"Scryfall API HTTP error {e.code}: {e.reason} for URL {url}")
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise RuntimeError(f"Failed to request Scryfall API ({url}): {e}")
                time.sleep(backoff)
                backoff *= 2.0

        raise RuntimeError(f"Failed to fetch {url} after {self.max_retries} retries.")

    def get_available_bulk_metadata(self) -> Dict[str, BulkMetadata]:
        """Fetch bulk data catalog from https://api.scryfall.com/bulk-data and map to BulkMetadata."""
        url = "https://api.scryfall.com/bulk-data"
        response_json = self._make_request(url)
        
        data_list = response_json.get("data", [])
        result = {}

        for item in data_list:
            bulk_type = item.get("type")
            if bulk_type in self.BULK_TYPES_MAP:
                metadata = BulkMetadata(
                    name=item.get("name", bulk_type),
                    bulk_type=bulk_type,
                    download_url=item.get("download_uri") or item.get("uri"),
                    updated_at=item.get("updated_at", ""),
                    compressed_size_bytes=item.get("compressed_size", 0),
                    file_format=".jsonl"
                )
                result[bulk_type] = metadata

        return result

    def get_bulk_metadata(self, bulk_type: str) -> Optional[BulkMetadata]:
        """Fetch metadata for a specific bulk type."""
        all_meta = self.get_available_bulk_metadata()
        return all_meta.get(bulk_type)

    def fetch_item_by_id(self, item_id: str) -> Dict[str, Any]:
        """Fetch a single card or object by ID from Scryfall API."""
        url = f"https://api.scryfall.com/cards/{item_id}"
        return self._make_request(url)
