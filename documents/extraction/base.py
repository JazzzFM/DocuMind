from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseEntityExtractor(ABC):
    """Abstract base class for entity extractors."""

    @abstractmethod
    def extract_entities(self, document_type: str, text: str) -> Dict[str, Any]:
        """Extracts entities from a given text based on document type."""
        pass