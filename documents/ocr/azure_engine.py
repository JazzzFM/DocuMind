from documents.ocr.base import BaseOCREngine

class AzureEngine(BaseOCREngine):
    """Azure OCR Engine implementation."""

    def _extract_text(self, file_path: str) -> str:
        # Placeholder for actual Azure OCR API call
        print(f"Extracting text from {file_path} using Azure")
        return "Text extracted by Azure"
