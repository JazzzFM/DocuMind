from abc import ABC, abstractmethod
import hashlib
from django.core.cache import cache

class BaseOCREngine(ABC):
    """Abstract base class for OCR engines."""

    def get_file_hash(self, file_path: str) -> str:
        """Computes the SHA256 hash of a file."""
        hasher = hashlib.sha256()
        with open(file_path, 'rb') as f:
            buf = f.read()
            hasher.update(buf)
        return hasher.hexdigest()

    def extract_text(self, file_path: str, use_cache: bool = True) -> str:
        """Extracts text from a given file, using cache if available."""
        if use_cache:
            file_hash = self.get_file_hash(file_path)
            cached_text = cache.get(file_hash)
            if cached_text:
                return cached_text

        text = self._extract_text(file_path)

        if use_cache:
            cache.set(file_hash, text)

        return text

    @abstractmethod
    def _extract_text(self, file_path: str) -> str:
        """Internal method to extract text from a given file."""
        pass
