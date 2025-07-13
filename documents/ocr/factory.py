from django.conf import settings
from documents.ocr.tesseract_engine import TesseractEngine
from documents.ocr.google_vision_engine import GoogleVisionEngine
from documents.ocr.azure_engine import AzureEngine

class OCRFactory:
    """Factory for creating OCR engines."""

    @staticmethod
    def get_engine():
        """Gets the OCR engine based on the settings."""
        engine_name = settings.OCR_ENGINE
        if engine_name == "tesseract":
            return TesseractEngine()
        elif engine_name == "google_vision":
            return GoogleVisionEngine()
        elif engine_name == "azure":
            return AzureEngine()
        else:
            raise ValueError(f"Unknown OCR engine: {engine_name}")