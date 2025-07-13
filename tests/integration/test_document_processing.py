import pytest
from unittest.mock import MagicMock, patch
from django.conf import settings
from documents.ocr.tesseract_engine import TesseractEngine
from documents.classification.classifier import DocumentClassifier
from documents.extraction.llm_extractor import LLMExtractor
from documents.llm.openai_provider import OpenAIProvider
from documents.classification.embedding_generator import EmbeddingGenerator
from documents.classification.keyword_matcher import KeywordMatcher
from documents.classification.vector_search import VectorSearch
import os

# Mock Django settings for DOCUMENT_TYPES and CACHES
@pytest.fixture(autouse=True)
def setup_django_settings():
    if not settings.configured:
        settings.configure(
            DOCUMENT_TYPES={
                "invoice": {
                    "name": "Invoice",
                    "keywords": ["invoice", "bill", "payment", "due date"],
                    "entities": ["invoice_number", "invoice_date", "vendor_name", "total_amount", "due_date"],
                },
                "contract": {
                    "name": "Contract",
                    "keywords": ["contract", "agreement", "party"],
                    "entities": ["contract_title"],
                },
            },
            CACHES={
                'default': {
                    'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
                    'LOCATION': 'unique-snowflake',
                }
            },
            BASE_DIR=os.path.dirname(os.path.abspath(__file__)), # Mock BASE_DIR for prompt path
        )

@pytest.fixture(autouse=True)
def clear_cache():
    from django.core.cache import cache
    cache.clear()

class TestDocumentProcessingIntegration:
    @patch.object(TesseractEngine, '_extract_text', return_value="This is a test invoice with a total amount of $100.00 and invoice number INV-2024-001.")
    @patch('documents.ocr.base.BaseOCREngine.get_file_hash', return_value="dummy_ocr_hash")
    @patch.object(EmbeddingGenerator, 'generate_embedding', return_value=[0.1, 0.2, 0.3])
    @patch.object(KeywordMatcher, 'match', return_value={'invoice': 2, 'contract': 0})
    @patch.object(VectorSearch, 'search', return_value={'metadatas': [[{'document_type': 'invoice'}]], 'distances': [[0.1]]})
    @patch.object(OpenAIProvider, 'get_completion', return_value='{"invoice_number": "INV-2024-001", "total_amount": "$100.00"}')
    @patch.object(VectorSearch, 'upsert')
    def test_full_document_processing_flow(self, mock_vector_search_upsert, mock_openai_completion, mock_vector_search_search, mock_keyword_match, mock_embedding_gen, mock_get_file_hash, mock_tesseract_extract_text):
        # Create a dummy prompt file for the LLMExtractor
        prompt_dir = os.path.join(settings.BASE_DIR.parent, "config", "prompts")
        os.makedirs(prompt_dir, exist_ok=True)
        prompt_file_path = os.path.join(prompt_dir, "invoice.txt")
        with open(prompt_file_path, 'w') as f:
            f.write("Extract entities from the following invoice text: {text}")

        # 1. OCR Process
        ocr_engine = TesseractEngine()
        extracted_text = ocr_engine.extract_text("dummy_invoice.pdf")
        assert "test invoice" in extracted_text
        mock_tesseract_extract_text.assert_called_once_with("dummy_invoice.pdf")

        # 2. Classification Process
        classifier = DocumentClassifier()
        doc_type, confidence = classifier.classify(extracted_text)
        assert doc_type == "invoice"
        assert confidence > 0
        mock_embedding_gen.assert_called_with(extracted_text)
        mock_keyword_match.assert_called_with(extracted_text)
        mock_vector_search_search.assert_called()

        # 3. Entity Extraction Process
        extractor = LLMExtractor()
        extracted_entities = extractor.extract_entities("invoice", extracted_text)
        assert extracted_entities["invoice_number"] == "INV-2024-001"
        assert extracted_entities["total_amount"] == "$100.00"
        mock_openai_completion.assert_called()

        # Clean up dummy prompt file
        os.remove(prompt_file_path)

        # Test add_document_to_index (part of classification, but tested here for full flow)
        classifier.add_document_to_index("doc_id_123", extracted_text, doc_type, extracted_entities)
        mock_vector_search_upsert.assert_called_once_with(
            [0.1, 0.2, 0.3],
            {'document_type': 'invoice', 'invoice_number': 'INV-2024-001', 'invoice_date': None, 'vendor_name': None, 'total_amount': '$100.00', 'due_date': None},
            "doc_id_123"
        )
