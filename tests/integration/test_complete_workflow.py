"""
Integration Tests for Complete Document Processing Workflow
Tests the entire pipeline from file upload to entity extraction and storage.
"""
import pytest
import io
import tempfile
from unittest.mock import patch, MagicMock
from django.test import TestCase, TransactionTestCase
from django.contrib.auth.models import User
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from rest_framework import status
from PIL import Image


class CompleteWorkflowIntegrationTest(TransactionTestCase):
    """Integration test for complete document processing workflow."""
    
    def setUp(self):
        """Set up test environment."""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Authenticate user
        token_url = reverse('token_obtain_pair')
        token_data = {'username': 'testuser', 'password': 'testpass123'}
        token_response = self.client.post(token_url, token_data, format='json')
        self.access_token = token_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
    
    def create_test_invoice_image(self):
        """Create a test image that simulates an invoice."""
        # Create a simple image with text-like patterns
        image = Image.new('RGB', (800, 600), color='white')
        # In a real test, you might draw text on the image
        # For now, we'll just create a blank image
        image_file = io.BytesIO()
        image.save(image_file, format='PNG')
        image_file.seek(0)
        return image_file
    
    @patch('api.views.OCRFactory.get_engine')
    @patch('api.views.DocumentClassifier')
    @patch('api.views.get_llm_extractor')
    def test_complete_invoice_processing_workflow(self, mock_extractor, mock_classifier, mock_ocr_factory):
        """Test complete workflow: Upload → OCR → Classification → Extraction → Storage → Search."""
        
        # Step 1: Mock OCR to return invoice-like text
        mock_ocr_engine = MagicMock()
        invoice_text = \"\"\"
        INVOICE
        Invoice Number: INV-2024-001
        Date: January 15, 2024
        Bill To: ABC Company
        Amount Due: $1,250.00
        Due Date: February 15, 2024
        \"\"\"
        mock_ocr_engine.extract_text.return_value = invoice_text
        mock_ocr_factory.return_value = mock_ocr_engine
        
        # Step 2: Mock classifier to identify as invoice
        mock_classifier_instance = MagicMock()
        mock_classifier_instance.classify.return_value = ('invoice', 0.95)
        mock_classifier_instance.add_document_to_index.return_value = None
        mock_classifier.return_value = mock_classifier_instance
        
        # Step 3: Mock entity extractor
        mock_extractor_instance = MagicMock()
        mock_extractor_instance.extract_entities.return_value = {
            'entities': {
                'invoice_number': 'INV-2024-001',
                'amount': '$1,250.00',
                'date': '2024-01-15',
                'due_date': '2024-02-15',
                'vendor': 'ABC Company'
            },
            'validation_summary': {
                'total_entities': 5,
                'valid_entities': 5,
                'invalid_entities': 0,
                'validation_rate': 1.0
            },
            'extraction_metadata': {
                'provider_used': 'openai',
                'processing_time': 1.2
            }
        }
        mock_extractor.return_value = mock_extractor_instance
        
        # Step 4: Process the document
        image_file = self.create_test_invoice_image()
        uploaded_file = SimpleUploadedFile(
            "invoice_001.png",
            image_file.getvalue(),
            content_type="image/png"
        )
        
        process_url = reverse('document_process')
        process_data = {
            'file': uploaded_file,
            'extract_entities': True
        }
        
        # Make the processing request
        response = self.client.post(process_url, process_data, format='multipart')
        
        # Step 5: Verify processing response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'success')
        self.assertEqual(response.data['document_type'], 'invoice')
        self.assertEqual(response.data['confidence'], 0.95)
        
        # Verify extracted entities
        entities = response.data['extracted_entities']
        self.assertEqual(entities['invoice_number'], 'INV-2024-001')
        self.assertEqual(entities['amount'], '$1,250.00')
        self.assertEqual(entities['date'], '2024-01-15')
        
        # Step 6: Verify OCR was called correctly
        mock_ocr_engine.extract_text.assert_called_once()
        
        # Step 7: Verify classification was called
        mock_classifier_instance.classify.assert_called_once_with(invoice_text)
        
        # Step 8: Verify entity extraction was called
        mock_extractor_instance.extract_entities.assert_called_once_with('invoice', invoice_text)
        
        # Step 9: Verify document was added to index
        mock_classifier_instance.add_document_to_index.assert_called_once()
        add_to_index_call = mock_classifier_instance.add_document_to_index.call_args
        self.assertEqual(add_to_index_call[0][0], 'invoice_001.png')  # filename
        self.assertEqual(add_to_index_call[0][1], invoice_text)  # text
        self.assertEqual(add_to_index_call[0][2], 'invoice')  # doc_type
    
    @patch('api.views.VectorSearch')
    @patch('api.views.DocumentClassifier')
    def test_search_workflow_after_processing(self, mock_classifier, mock_vector_search):
        """Test document search after processing documents."""
        
        # Mock the search functionality
        mock_classifier_instance = MagicMock()
        mock_embedding_generator = MagicMock()
        mock_embedding_generator.generate_embedding.return_value = [0.1, 0.2, 0.3]
        mock_classifier_instance.embedding_generator = mock_embedding_generator
        mock_classifier.return_value = mock_classifier_instance
        
        # Mock search results
        mock_search_instance = MagicMock()
        mock_search_instance.search.return_value = {
            'ids': [['invoice_001.png', 'invoice_002.png']],
            'metadatas': [[
                {
                    'document_type': 'invoice',
                    'invoice_number': 'INV-2024-001',
                    'amount': '$1,250.00'
                },
                {
                    'document_type': 'invoice',
                    'invoice_number': 'INV-2024-002',
                    'amount': '$750.00'
                }
            ]],
            'distances': [[0.1, 0.15]]
        }
        mock_vector_search.return_value = mock_search_instance
        
        # Perform search
        search_url = reverse('document_search')
        search_params = {
            'query': 'invoice documents with amounts',
            'document_type': 'invoice',
            'limit': 10
        }
        
        response = self.client.get(search_url, search_params)
        
        # Verify search response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'success')
        self.assertEqual(response.data['total_results'], 2)
        
        results = response.data['results']
        self.assertEqual(len(results), 2)
        
        # Verify first result
        first_result = results[0]
        self.assertEqual(first_result['document_id'], 'invoice_001.png')
        self.assertEqual(first_result['document_type'], 'invoice')
        self.assertIn('similarity', first_result)
        
        # Verify similarity calculation (1 - distance)
        self.assertAlmostEqual(first_result['similarity'], 0.9, places=1)
    
    @patch('api.views.OCRFactory.get_engine')
    @patch('api.views.DocumentClassifier')  
    @patch('api.views.get_llm_extractor')
    def test_batch_processing_workflow(self, mock_extractor, mock_classifier, mock_ocr_factory):
        """Test batch processing workflow with multiple documents."""
        
        # Mock OCR for different document types
        mock_ocr_engine = MagicMock()
        ocr_responses = [
            "INVOICE\\nInvoice Number: INV-001\\nAmount: $500.00",
            "CONTRACT\\nService Agreement\\nParty A: Company ABC",
            "APPLICATION FORM\\nName: John Doe\\nDate: 2024-01-15"
        ]
        mock_ocr_engine.extract_text.side_effect = ocr_responses
        mock_ocr_factory.return_value = mock_ocr_engine
        
        # Mock classifier for different document types
        mock_classifier_instance = MagicMock()
        classification_responses = [
            ('invoice', 0.90),
            ('contract', 0.85),
            ('form', 0.80)
        ]
        mock_classifier_instance.classify.side_effect = classification_responses
        mock_classifier_instance.add_document_to_index.return_value = None
        mock_classifier.return_value = mock_classifier_instance
        
        # Mock extractor for different entities
        mock_extractor_instance = MagicMock()
        extraction_responses = [
            {'entities': {'invoice_number': 'INV-001', 'amount': '$500.00'}},
            {'entities': {'contract_title': 'Service Agreement', 'party_a': 'Company ABC'}},
            {'entities': {'applicant_name': 'John Doe', 'date': '2024-01-15'}}
        ]
        mock_extractor_instance.extract_entities.side_effect = extraction_responses
        mock_extractor.return_value = mock_extractor_instance
        
        # Create test files
        files = []
        filenames = ['invoice.png', 'contract.png', 'form.png']
        for filename in filenames:
            image_file = self.create_test_invoice_image()
            uploaded_file = SimpleUploadedFile(
                filename,
                image_file.getvalue(),
                content_type="image/png"
            )
            files.append(uploaded_file)
        
        # Process batch (synchronous)
        batch_url = reverse('document_batch_process')
        batch_data = {
            'files': files,
            'async': False
        }
        
        response = self.client.post(batch_url, batch_data, format='multipart')
        
        # Verify batch processing response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'completed')
        self.assertEqual(len(response.data['results']), 3)
        
        # Verify individual results
        results = response.data['results']
        
        # Invoice result
        invoice_result = results[0]
        self.assertEqual(invoice_result['status'], 'success')
        self.assertEqual(invoice_result['document_type'], 'invoice')
        self.assertEqual(invoice_result['confidence'], 0.90)
        self.assertEqual(invoice_result['extracted_entities']['invoice_number'], 'INV-001')
        
        # Contract result
        contract_result = results[1]
        self.assertEqual(contract_result['document_type'], 'contract')
        self.assertEqual(contract_result['confidence'], 0.85)
        
        # Form result
        form_result = results[2]
        self.assertEqual(form_result['document_type'], 'form')
        self.assertEqual(form_result['confidence'], 0.80)
        
        # Verify all components were called correct number of times
        self.assertEqual(mock_ocr_engine.extract_text.call_count, 3)
        self.assertEqual(mock_classifier_instance.classify.call_count, 3)
        self.assertEqual(mock_extractor_instance.extract_entities.call_count, 3)
        self.assertEqual(mock_classifier_instance.add_document_to_index.call_count, 3)
    
    def test_system_monitoring_workflow(self):
        """Test system monitoring endpoints workflow."""
        
        # Test system status
        with patch('api.views.OCRFactory.get_engine') as mock_ocr, \
             patch('api.views.LLMFactory') as mock_llm_factory, \
             patch('api.views.VectorSearch') as mock_vector_search:
            
            # Mock healthy components
            mock_ocr.return_value = MagicMock()
            
            mock_llm_factory_instance = MagicMock()
            mock_provider = MagicMock()
            mock_provider.test_connection.return_value = True
            mock_provider.get_provider_name.return_value = 'openai'
            mock_llm_factory_instance.get_provider.return_value = mock_provider
            mock_llm_factory.return_value = mock_llm_factory_instance
            
            mock_vector_search_instance = MagicMock()
            mock_vector_search_instance.get_collection_info.return_value = {'document_count': 150}
            mock_vector_search.return_value = mock_vector_search_instance
            
            # Check system status
            status_url = reverse('system_status')
            status_response = self.client.get(status_url)
            
            self.assertEqual(status_response.status_code, status.HTTP_200_OK)
            self.assertEqual(status_response.data['status'], 'healthy')
            
            # Check all components are healthy
            components = status_response.data['components']
            for component_name in ['ocr', 'llm', 'vector_search', 'cache']:
                self.assertIn(component_name, components)
        
        # Test document types endpoint
        with patch('documents.config_loader.get_document_types') as mock_get_types:
            mock_config = MagicMock()
            mock_config.name = 'Invoice'
            mock_config.entities = [{'name': 'invoice_number', 'type': 'string', 'required': True}]
            mock_config.keywords = ['invoice', 'bill']
            mock_get_types.return_value = {'invoice': mock_config}
            
            types_url = reverse('document_types')
            types_response = self.client.get(types_url)
            
            self.assertEqual(types_response.status_code, status.HTTP_200_OK)
            self.assertEqual(types_response.data['total_types'], 1)
        
        # Test statistics endpoint
        with patch('api.views.DocumentClassifier') as mock_classifier, \
             patch('api.views.get_llm_extractor') as mock_extractor, \
             patch('api.views.VectorSearch') as mock_vector_search:
            
            # Mock statistics
            mock_classifier_instance = MagicMock()
            mock_classifier_instance.get_classification_statistics.return_value = {
                'total_classifications': 100,
                'accuracy': 0.95
            }
            mock_classifier.return_value = mock_classifier_instance
            
            mock_extractor_instance = MagicMock()
            mock_extractor_instance.get_extraction_statistics.return_value = {
                'total_extractions': 85,
                'success_rate': 0.88
            }
            mock_extractor.return_value = mock_extractor_instance
            
            mock_vector_search_instance = MagicMock()
            mock_vector_search_instance.get_collection_info.return_value = {
                'document_count': 150
            }
            mock_vector_search.return_value = mock_vector_search_instance
            
            stats_url = reverse('statistics')
            stats_response = self.client.get(stats_url)
            
            self.assertEqual(stats_response.status_code, status.HTTP_200_OK)
            stats = stats_response.data['statistics']
            self.assertEqual(stats['classification']['total_classifications'], 100)
            self.assertEqual(stats['extraction']['total_extractions'], 85)


class ErrorHandlingIntegrationTest(TestCase):
    """Integration tests for error handling across the workflow."""
    
    def setUp(self):
        """Set up test environment."""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        # Authenticate
        token_url = reverse('token_obtain_pair')
        token_data = {'username': 'testuser', 'password': 'testpass123'}
        token_response = self.client.post(token_url, token_data, format='json')
        self.access_token = token_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
    
    @patch('api.views.OCRFactory.get_engine')
    def test_ocr_failure_handling(self, mock_ocr_factory):
        """Test graceful handling of OCR failures."""
        from documents.exceptions import OCRProcessingError
        
        # Mock OCR to fail
        mock_ocr_engine = MagicMock()
        mock_ocr_engine.extract_text.side_effect = OCRProcessingError("OCR service unavailable")
        mock_ocr_factory.return_value = mock_ocr_engine
        
        # Create test file
        image = Image.new('RGB', (100, 100), color='white')
        image_file = io.BytesIO()
        image.save(image_file, format='PNG')
        image_file.seek(0)
        
        uploaded_file = SimpleUploadedFile(
            "test.png",
            image_file.getvalue(),
            content_type="image/png"
        )
        
        # Process document
        process_url = reverse('document_process')
        response = self.client.post(process_url, {'file': uploaded_file}, format='multipart')
        
        # Verify error handling
        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertEqual(response.data['status'], 'error')
        self.assertIn('OCR processing failed', response.data['message'])
    
    @patch('api.views.OCRFactory.get_engine')
    @patch('api.views.DocumentClassifier')
    def test_classification_failure_handling(self, mock_classifier, mock_ocr_factory):
        """Test handling of classification failures."""
        from documents.exceptions import DocumentClassificationError
        
        # Mock OCR success
        mock_ocr_engine = MagicMock()
        mock_ocr_engine.extract_text.return_value = "Some document text"
        mock_ocr_factory.return_value = mock_ocr_engine
        
        # Mock classifier failure
        mock_classifier_instance = MagicMock()
        mock_classifier_instance.classify.side_effect = DocumentClassificationError("Classification model unavailable")
        mock_classifier.return_value = mock_classifier_instance
        
        # Create and process test file
        image = Image.new('RGB', (100, 100), color='white')
        image_file = io.BytesIO()
        image.save(image_file, format='PNG')
        image_file.seek(0)
        
        uploaded_file = SimpleUploadedFile(
            "test.png",
            image_file.getvalue(),
            content_type="image/png"
        )
        
        process_url = reverse('document_process')
        response = self.client.post(process_url, {'file': uploaded_file}, format='multipart')
        
        # Verify error handling
        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertEqual(response.data['status'], 'error')
        self.assertIn('Document classification failed', response.data['message'])
    
    @patch('api.views.OCRFactory.get_engine')
    @patch('api.views.DocumentClassifier')
    @patch('api.views.get_llm_extractor')
    def test_extraction_failure_handling(self, mock_extractor, mock_classifier, mock_ocr_factory):
        """Test handling of entity extraction failures."""
        from documents.exceptions import EntityExtractionError
        
        # Mock OCR and classification success
        mock_ocr_engine = MagicMock()
        mock_ocr_engine.extract_text.return_value = "Invoice document"
        mock_ocr_factory.return_value = mock_ocr_engine
        
        mock_classifier_instance = MagicMock()
        mock_classifier_instance.classify.return_value = ('invoice', 0.85)
        mock_classifier.return_value = mock_classifier_instance
        
        # Mock extraction failure
        mock_extractor_instance = MagicMock()
        mock_extractor_instance.extract_entities.side_effect = EntityExtractionError("LLM service timeout")
        mock_extractor.return_value = mock_extractor_instance
        
        # Create and process test file
        image = Image.new('RGB', (100, 100), color='white')
        image_file = io.BytesIO()
        image.save(image_file, format='PNG')
        image_file.seek(0)
        
        uploaded_file = SimpleUploadedFile(
            "test.png",
            image_file.getvalue(),
            content_type="image/png"
        )
        
        process_url = reverse('document_process')
        response = self.client.post(process_url, {'file': uploaded_file}, format='multipart')
        
        # Verify error handling
        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertEqual(response.data['status'], 'error')
        self.assertIn('Entity extraction failed', response.data['message'])