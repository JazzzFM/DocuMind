import pytesseract
from PIL import Image
from pdf2image import convert_from_path, PDFInfoNotInstalledError, PDFPageCountError
from documents.ocr.base import BaseOCREngine
from documents.exceptions import OCRProcessingError

class TesseractEngine(BaseOCREngine):
    """OCR engine implementation using Tesseract."""

    def _extract_text(self, file_path: str) -> str:
        """Extracts text from a given file (PDF or image)."""
        try:
            if file_path.lower().endswith(".pdf"):
                pages = convert_from_path(file_path)
                text = "".join([pytesseract.image_to_string(page) for page in pages])
                return text
            else:
                return pytesseract.image_to_string(Image.open(file_path))
        except (pytesseract.TesseractError, PDFInfoNotInstalledError, PDFPageCountError, FileNotFoundError) as e:
            raise OCRProcessingError(f"Error during Tesseract OCR processing: {e}") from e
        except Exception as e:
            raise OCRProcessingError(f"An unexpected error occurred during Tesseract OCR processing: {e}") from e