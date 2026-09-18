from abc import ABC, abstractmethod
from typing import Any, Dict, List, Tuple

FormattedText = List[Tuple[str, str]]

class PluggableWidget(ABC):
    """Abstract base class for pluggable UI components (widgets) in LexiGrim."""

    def __init__(self, title: str = "Widget"):
        self.title = title
        self.data: Dict[str, Any] = {}

    @abstractmethod
    def update(self, data: Dict[str, Any]) -> None:
        """Receive updated data model and re-cache representation."""
        pass

    @abstractmethod
    def render(self, width: int, height: int) -> FormattedText:
        """Render component to structured styled tokens matching allocated size."""
        pass
