"""
Base OCR Engine Module for DocuMind Document Processing System.

This module provides the abstract base class for all OCR engines in the system.
It implements common functionality like caching and file handling, while requiring
concrete implementations to provide the actual text extraction logic.

Classes:
    BaseOCREngine: Abstract base class for OCR engines

Example:
    Creating a custom OCR engine:
    
    ```python
    from documents.ocr.base import BaseOCREngine
    
    class CustomOCREngine(BaseOCREngine):
        def _extract_text(self, file_path: str) -> str:
            # Custom OCR implementation
            return extracted_text
    ```
"""

from abc import ABC, abstractmethod
import hashlib
from django.core.cache import cache

class BaseOCREngine(ABC):
    """
    Abstract base class for OCR engines.
    
    This class provides a common interface for all OCR implementations in the system.
    It includes built-in caching functionality to improve performance by avoiding
    redundant OCR operations on the same files.
    
    The caching mechanism uses SHA256 file hashes as cache keys to ensure that
    identical files are processed only once, regardless of their filename.
    
    Attributes:
        None
        
    Methods:
        extract_text: Public method to extract text with optional caching
        get_file_hash: Generate SHA256 hash for file-based caching
        _extract_text: Abstract method for actual OCR implementation
        
    Example:
        ```python
        # Usage in concrete implementation
        engine = TesseractEngine()
        text = engine.extract_text('/path/to/document.pdf')
        
        # Second call will use cached result
        text = engine.extract_text('/path/to/document.pdf')
        ```
    """

    def get_file_hash(self, file_path: str) -> str:
        """
        Compute SHA256 hash of a file for caching purposes.
        
        Args:
            file_path (str): Path to the file to hash
            
        Returns:
            str: Hexadecimal SHA256 hash of the file
            
        Raises:
            FileNotFoundError: If the file doesn't exist
            IOError: If the file cannot be read
            
        Example:
            >>> engine = TesseractEngine()
            >>> hash_value = engine.get_file_hash('/path/to/document.pdf')
            >>> print(len(hash_value))
            64
        """
        hasher = hashlib.sha256()
        with open(file_path, 'rb') as f:
            buf = f.read()
            hasher.update(buf)
        return hasher.hexdigest()

    def extract_text(self, file_path: str, use_cache: bool = True) -> str:
        """
        Extract text from a document file with optional caching.
        
        This method first checks the cache for previously extracted text using
        the file's SHA256 hash. If not found, it processes the file and caches
        the result for future use.
        
        Args:
            file_path (str): Path to the document file
            use_cache (bool): Whether to use caching (default: True)
            
        Returns:
            str: Extracted text from the document
            
        Raises:
            FileNotFoundError: If the file doesn't exist
            OCRProcessingError: If OCR processing fails
            
        Example:
            >>> engine = TesseractEngine()
            >>> text = engine.extract_text('/path/to/invoice.pdf')
            >>> print(text[:50])
            'INVOICE\nCompany Name: Acme Corp\nInvoice Number: 001'
        """
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
        """
        Internal method to extract text from a document file.
        
        This method must be implemented by concrete OCR engine classes.
        It should contain the actual logic for text extraction without
        caching considerations.
        
        Args:
            file_path (str): Path to the document file
            
        Returns:
            str: Extracted text from the document
            
        Raises:
            NotImplementedError: If not implemented by subclass
            OCRProcessingError: If OCR processing fails
            
        Note:
            This is an abstract method and must be implemented by all
            concrete OCR engine classes.
        """
        pass
