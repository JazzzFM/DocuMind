from django.conf import settings
from documents.ocr.tesseract_engine import TesseractEngine

class OCRFactory:
    """Factory for creating OCR engines."""

    @staticmethod
    def get_engine():
        """Gets the OCR engine based on the settings."""
        engine_name = settings.OCR_ENGINE
        if engine_name == "tesseract":
            return TesseractEngine()
        # Add other engines here as they are implemented
        else:
            raise ValueError(f"Unknown OCR engine: {engine_name}")