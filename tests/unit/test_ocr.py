import pytest
from unittest.mock import MagicMock, patch
from documents.ocr.base import BaseOCREngine
from documents.ocr.tesseract_engine import TesseractEngine
from django.core.cache import cache
import os

# Mock settings for Django cache
@pytest.fixture(autouse=True)
def setup_django_settings():
    from django.conf import settings
    if not settings.configured:
        settings.configure(
            CACHES={
                'default': {
                    'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
                    'LOCATION': 'unique-snowflake',
                }
            }
        )

@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()

class TestBaseOCREngine:
    def test_abstract_methods(self):
        with pytest.raises(TypeError):
            BaseOCREngine()

    @patch('documents.ocr.base.BaseOCREngine._extract_text')
    def test_extract_text_with_caching(self, mock_extract_text):
        mock_extract_text.return_value = "Extracted Text"

        class ConcreteOCREngine(BaseOCREngine):
            def _extract_text(self, file_path: str) -> str:
                return mock_extract_text(file_path)

        engine = ConcreteOCREngine()
        test_file_path = "test_file.txt"

        # Create a dummy file for hashing
        with open(test_file_path, 'w') as f:
            f.write("dummy content")

        # First call - should call _extract_text and cache
        text1 = engine.extract_text(test_file_path)
        mock_extract_text.assert_called_once_with(test_file_path)
        assert text1 == "Extracted Text"

        mock_extract_text.reset_mock()

        # Second call - should use cache and not call _extract_text
        text2 = engine.extract_text(test_file_path)
        mock_extract_text.assert_not_called()
        assert text2 == "Extracted Text"

        os.remove(test_file_path)

class TestTesseractEngine:
    @patch('pytesseract.image_to_string')
    @patch('PIL.Image.open')
    def test_extract_text_image(self, mock_image_open, mock_image_to_string):
        mock_image_to_string.return_value = "Image Text"
        mock_image_open.return_value = MagicMock()

        engine = TesseractEngine()
        test_image_path = "test_image.png"
        with open(test_image_path, 'w') as f: # Create dummy file
            f.write("dummy image content")

        text = engine.extract_text(test_image_path)
        mock_image_open.assert_called_once_with(test_image_path)
        mock_image_to_string.assert_called_once()
        assert text == "Image Text"

        os.remove(test_image_path)

    @patch('pytesseract.image_to_string')
    @patch('pdf2image.convert_from_path')
    def test_extract_text_pdf(self, mock_convert_from_path, mock_image_to_string):
        mock_image_to_string.return_value = "PDF Page Text"
        mock_convert_from_path.return_value = [MagicMock(), MagicMock()]

        engine = TesseractEngine()
        test_pdf_path = "test_document.pdf"
        with open(test_pdf_path, 'w') as f: # Create dummy file
            f.write("dummy pdf content")

        text = engine.extract_text(test_pdf_path)
        mock_convert_from_path.assert_called_once_with(test_pdf_path)
        assert mock_image_to_string.call_count == 2 # Called for each page
        assert text == "PDF Page TextPDF Page Text"

        os.remove(test_pdf_path)
