from abc import ABC, abstractmethod
from typing import Iterator, Dict, Any

class BaseSourceReader(ABC):
    """Abstract base interface for incremental data corpus readers."""
    
    @abstractmethod
    def stream_records(self) -> Iterator[Dict[str, Any]]:
        """Yield raw record dictionaries from the data source."""
        pass
