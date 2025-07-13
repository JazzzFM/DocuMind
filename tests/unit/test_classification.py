import pytest
from unittest.mock import MagicMock, patch
from documents.classification.classifier import DocumentClassifier
from documents.classification.embedding_generator import EmbeddingGenerator
from documents.classification.keyword_matcher import KeywordMatcher
from documents.classification.vector_search import VectorSearch
from django.conf import settings
import numpy as np

# Mock Django settings for DOCUMENT_TYPES
@pytest.fixture(autouse=True)
def setup_document_types_settings():
    if not settings.configured:
        settings.configure(
            DOCUMENT_TYPES={
                "invoice": {
                    "name": "Invoice",
                    "keywords": ["invoice", "bill", "payment", "due date"],
                    "entities": ["invoice_number"],
                },
                "contract": {
                    "name": "Contract",
                    "keywords": ["contract", "agreement", "party"],
                    "entities": ["contract_title"],
                },
            }
        )

class TestEmbeddingGenerator:
    @patch('documents.classification.embedding_generator.SentenceTransformer')
    def test_generate_embedding(self, MockSentenceTransformer):
        mock_model = MockSentenceTransformer.return_value
        mock_model.encode.return_value = [0.1, 0.2, 0.3] # Return a list
        generator = EmbeddingGenerator()
        embedding = generator.generate_embedding("test text")
        mock_model.encode.assert_called_once_with("test text")
        assert embedding == [0.1, 0.2, 0.3]

class TestKeywordMatcher:
    def test_match(self):
        matcher = KeywordMatcher()
        text = "This is an invoice with a payment due."
        scores = matcher.match(text)
        assert scores["invoice"] > 0
        assert scores["contract"] == 0

    def test_match_case_insensitive(self):
        matcher = KeywordMatcher()
        text = "This is a Contract agreement."
        scores = matcher.match(text)
        assert scores["contract"] > 0

    def test_match_no_keywords(self):
        matcher = KeywordMatcher()
        text = "Some random text."
        scores = matcher.match(text)
        assert all(score == 0 for score in scores.values())

class TestVectorSearch:
    @patch('chromadb.PersistentClient')
    def test_upsert(self, MockPersistentClient):
        mock_client = MockPersistentClient.return_value
        mock_collection = mock_client.get_or_create_collection.return_value
        search = VectorSearch()
        embedding = [0.1, 0.2, 0.3]
        metadata = {"document_type": "invoice"}
        document_id = "doc123"
        search.upsert(embedding, metadata, document_id)
        mock_collection.upsert.assert_called_once_with(
            embeddings=[embedding],
            metadatas=[metadata],
            ids=[document_id]
        )

    @patch('chromadb.PersistentClient')
    def test_search(self, MockPersistentClient):
        mock_client = MockPersistentClient.return_value
        mock_collection = mock_client.get_or_create_collection.return_value
        mock_collection.query.return_value = {
            "metadatas": [[{"document_type": "invoice"}]],
            "distances": [[0.1]],
        }
        search = VectorSearch()
        embedding = [0.1, 0.2, 0.3]
        results = search.search(embedding)
        mock_collection.query.assert_called_once_with(
            query_embeddings=[embedding],
            n_results=5,
            include=["metadatas", "distances"]
        )
        assert results["metadatas"][0][0]["document_type"] == "invoice"

class TestDocumentClassifier:
    @patch.object(EmbeddingGenerator, 'generate_embedding', return_value=[0.1, 0.2, 0.3]) # Return a list
    @patch.object(KeywordMatcher, 'match', return_value={'invoice': 2, 'contract': 0})
    @patch.object(VectorSearch, 'search', return_value={'metadatas': [[{'document_type': 'invoice'}]], 'distances': [[0.1]]})
    def test_classify_invoice(self, mock_vector_search, mock_keyword_match, mock_embedding_gen):
        classifier = DocumentClassifier()
        doc_type, confidence = classifier.classify("This is an invoice")
        assert doc_type == "invoice"
        assert confidence > 0

    @patch.object(EmbeddingGenerator, 'generate_embedding', return_value=[0.1, 0.2, 0.3]) # Return a list
    @patch.object(KeywordMatcher, 'match', return_value={'invoice': 0, 'contract': 2})
    @patch.object(VectorSearch, 'search', return_value={'metadatas': [[{'document_type': 'contract'}]], 'distances': [[0.1]]})
    def test_classify_contract(self, mock_vector_search, mock_keyword_match, mock_embedding_gen):
        classifier = DocumentClassifier()
        doc_type, confidence = classifier.classify("This is a contract")
        assert doc_type == "contract"
        assert confidence > 0

    @patch.object(EmbeddingGenerator, 'generate_embedding', return_value=[0.1, 0.2, 0.3]) # Return a list
    @patch.object(KeywordMatcher, 'match', return_value={'invoice': 0, 'contract': 0})
    @patch.object(VectorSearch, 'search', return_value={'metadatas': [[{'document_type': 'unknown'}]], 'distances': [[0.9]]})
    def test_classify_unknown_below_threshold(self, mock_vector_search, mock_keyword_match, mock_embedding_gen):
        classifier = DocumentClassifier()
        doc_type, confidence = classifier.classify("This is some random text", confidence_threshold=0.9)
        assert doc_type == "unknown"
        assert confidence < 0.9

    @patch.object(EmbeddingGenerator, 'generate_embedding', return_value=[0.1, 0.2, 0.3]) # Return a list
    @patch.object(KeywordMatcher, 'match', return_value={'invoice': 0, 'contract': 0})
    @patch.object(VectorSearch, 'search', return_value={'metadatas': [], 'distances': []})
    def test_classify_no_matches(self, mock_vector_search, mock_keyword_match, mock_embedding_gen):
        classifier = DocumentClassifier()
        doc_type, confidence = classifier.classify("This is some random text")
        assert doc_type == "unknown"
        assert confidence == 0.0

    @patch.object(EmbeddingGenerator, 'generate_embedding', return_value=[0.1, 0.2, 0.3]) # Return a list
    @patch.object(VectorSearch, 'upsert')
    def test_add_document_to_index(self, mock_vector_search, mock_embedding_gen):
        classifier = DocumentClassifier()
        classifier.add_document_to_index("doc123", "test text", "invoice", {"invoice_number": "123"})
        mock_embedding_gen.assert_called_once_with("test text")
        mock_vector_search.assert_called_once_with(
            [0.1, 0.2, 0.3],
            {'document_type': 'invoice', 'invoice_number': '123'},
            "doc123"
        )
