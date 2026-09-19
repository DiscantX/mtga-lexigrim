from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, Optional, Callable


@dataclass
class BulkMetadata:
    """Strongly typed data container holding dataset metadata."""
    name: str
    bulk_type: str
    download_url: str
    updated_at: str
    compressed_size_bytes: int
    file_format: str = ".jsonl"


class BaseDownloader(ABC):
    """Abstract base class defining the HTTP downloading contract."""

    @abstractmethod
    def download_file(
        self,
        url: str,
        destination_path: str,
        decompress_gzip: bool = True,
        progress_callback: Optional[Callable[[float, str, str], None]] = None
    ) -> str:
        """Download a file from a URL, optionally decompressing gzip streams on the fly,
        and report progress via progress_callback(percentage, speed, message).
        """
        pass


class BaseDataProvider(ABC):
    """Abstract base class for data source endpoints (Scryfall, rules repos, etc.)."""

    @abstractmethod
    def get_available_bulk_metadata(self) -> Dict[str, BulkMetadata]:
        """Fetch and return all available bulk data descriptors keyed by bulk_type."""
        pass

    @abstractmethod
    def get_bulk_metadata(self, bulk_type: str) -> Optional[BulkMetadata]:
        """Fetch metadata for a specific bulk data type."""
        pass

    @abstractmethod
    def fetch_item_by_id(self, item_id: str) -> Dict[str, Any]:
        """Fetch a single item by ID from the data provider."""
        pass
