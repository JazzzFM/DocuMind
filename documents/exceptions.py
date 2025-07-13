class DocumentProcessingError(Exception):
    """Custom exception for document processing errors."""
    pass

class DocumentClassificationError(DocumentProcessingError):
    """Custom exception for document classification errors."""
    pass

class EntityExtractionError(DocumentProcessingError):
    """Custom exception for entity extraction errors."""
    pass

class OCRProcessingError(DocumentProcessingError):
    """Custom exception for OCR processing errors."""
    pass