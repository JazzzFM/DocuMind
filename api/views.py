from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from documents.ocr.factory import OCRFactory
from documents.classification.classifier import DocumentClassifier
from documents.extraction.llm_extractor import get_llm_extractor
from .serializers import DocumentProcessSerializer, DocumentSearchSerializer, DocumentBatchProcessSerializer
from documents.classification.vector_search import VectorSearch
from documents.exceptions import DocumentProcessingError, OCRProcessingError, DocumentClassificationError, EntityExtractionError
from documents.config_loader import get_document_types
from documents.llm.factory import LLMFactory
import os
import uuid
import logging

logger = logging.getLogger(__name__)

ALLOWED_FILE_TYPES = ['.pdf', '.png', '.jpg', '.jpeg']

def is_allowed_file_type(filename):
    return os.path.splitext(filename)[1].lower() in ALLOWED_FILE_TYPES

class DocumentProcessView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs):
        serializer = DocumentProcessSerializer(data=request.data)
        if serializer.is_valid():
            file_obj = serializer.validated_data['file']
            extract_entities = serializer.validated_data.get('extract_entities', True)
            # force_ocr = serializer.validated_data.get('force_ocr', False)
            # language = serializer.validated_data.get('language', 'eng')

            if not is_allowed_file_type(file_obj.name):
                return Response({'status': 'error', 'message': 'Unsupported file type.'}, status=status.HTTP_400_BAD_REQUEST)

            # Save the uploaded file temporarily
            temp_file_path = os.path.join('/tmp', str(uuid.uuid4()) + file_obj.name)
            with open(temp_file_path, 'wb+') as destination:
                for chunk in file_obj.chunks():
                    destination.write(chunk)
            
            try:
                ocr_engine = OCRFactory.get_engine()
                classifier = DocumentClassifier()
                extractor = get_llm_extractor()

                # OCR
                text = ocr_engine.extract_text(temp_file_path)

                # Classification
                doc_type, confidence, _ = classifier.classify(text)

                extracted_entities_data = {}
                if extract_entities and doc_type != 'unknown':
                    extraction_result = extractor.extract_entities(doc_type, text)
                    extracted_entities_data = extraction_result.get('entities', {})
                    classifier.add_document_to_index(file_obj.name, text, doc_type, extracted_entities_data) # Add to ChromaDB

                return Response({
                    'status': 'success',
                    'document_id': file_obj.name,
                    'document_type': doc_type,
                    'confidence': confidence,
                    'extracted_entities': extracted_entities_data,
                }, status=status.HTTP_200_OK)

            except OCRProcessingError as e:
                return Response({'status': 'error', 'message': f'OCR processing failed: {e}'}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
            except DocumentClassificationError as e:
                return Response({'status': 'error', 'message': f'Document classification failed: {e}'}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
            except EntityExtractionError as e:
                return Response({'status': 'error', 'message': f'Entity extraction failed: {e}'}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
            except DocumentProcessingError as e:
                return Response({'status': 'error', 'message': f'Document processing failed: {e}'}, status=status.HTTP_400_BAD_REQUEST)
            except FileNotFoundError as e:
                return Response({'status': 'error', 'message': f'File not found during processing: {e}'}, status=status.HTTP_404_NOT_FOUND)
            except Exception as e:
                return Response({'status': 'error', 'message': f'An unexpected error occurred: {e}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            finally:
                # Clean up the temporary file
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class DocumentSearchView(APIView):
    def get(self, request, *args, **kwargs):
        serializer = DocumentSearchSerializer(data=request.query_params)
        if serializer.is_valid():
            query = serializer.validated_data.get('query')
            document_type = serializer.validated_data.get('document_type')
            # date_from = serializer.validated_data.get('date_from')
            # date_to = serializer.validated_data.get('date_to')
            limit = serializer.validated_data.get('limit', 20)
            offset = serializer.validated_data.get('offset', 0)

            vector_search = VectorSearch()
            embedding_generator = DocumentClassifier().embedding_generator # Reuse embedding generator

            try:
                query_embedding = embedding_generator.generate_embedding(query)

                where_clause = {}
                if document_type:
                    where_clause['document_type'] = document_type
                
                # TODO: Add date filtering

                results = vector_search.search(query_embedding, n_results=limit + offset)

                # Filter and paginate results
                filtered_results = []
                if results and results['ids']:
                    for i in range(len(results['ids'][0])):
                        metadata = results['metadatas'][0][i]
                        doc_id = results['ids'][0][i]
                        distance = results['distances'][0][i]

                        # Apply document_type filter if present
                        if document_type and metadata.get('document_type') != document_type:
                            continue

                        filtered_results.append({
                            'document_id': doc_id,
                            'document_type': metadata.get('document_type'),
                            'extracted_entities': {k: v for k, v in metadata.items() if k != 'document_type'},
                            'similarity': 1 - distance # Convert distance to similarity
                        })
                
                # Apply offset and limit
                paginated_results = filtered_results[offset:offset+limit]

                return Response({
                    'status': 'success',
                    'total_results': len(filtered_results),
                    'results': paginated_results
                }, status=status.HTTP_200_OK)
            except Exception as e:
                return Response({'status': 'error', 'message': f'Search failed: {e}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class DocumentBatchProcessView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs):
        serializer = DocumentBatchProcessSerializer(data=request.data)
        if serializer.is_valid():
            files = serializer.validated_data['files']
            async_process = serializer.validated_data.get('async', True)

            # Validate file types for batch processing
            for file_obj in files:
                if not is_allowed_file_type(file_obj.name):
                    return Response({'status': 'error', 'message': f'Unsupported file type: {file_obj.name}'}, status=status.HTTP_400_BAD_REQUEST)

            # In a real application, you would offload this to a task queue (e.g., Celery)
            # For now, we'll just simulate the processing.
            if async_process:
                # Simulate a background task ID
                task_id = str(uuid.uuid4())
                # Here you would typically send files to a Celery task
                # For demonstration, we'll just return a success message
                return Response({
                    'status': 'processing',
                    'task_id': task_id,
                    'message': 'Batch processing initiated. Check task status later.'
                }, status=status.HTTP_202_ACCEPTED)
            else:
                # Synchronous processing (for small batches or testing)
                results = []
                for file_obj in files:
                    # Save the uploaded file temporarily
                    temp_file_path = os.path.join('/tmp', str(uuid.uuid4()) + file_obj.name)
                    with open(temp_file_path, 'wb+') as destination:
                        for chunk in file_obj.chunks():
                            destination.write(chunk)
                    
                    try:
                        ocr_engine = OCRFactory.get_engine()
                        classifier = DocumentClassifier()
                        extractor = get_llm_extractor()

                        text = ocr_engine.extract_text(temp_file_path)
                        doc_type, confidence, _ = classifier.classify(text)
                        extracted_entities_data = {}
                        if doc_type != 'unknown':
                            extraction_result = extractor.extract_entities(doc_type, text)
                            extracted_entities_data = extraction_result.get('entities', {})
                            classifier.add_document_to_index(file_obj.name, text, doc_type, extracted_entities_data)

                        results.append({
                            'document_id': file_obj.name,
                            'document_type': doc_type,
                            'confidence': confidence,
                            'extracted_entities': extracted_entities_data,
                            'status': 'success'
                        })
                    except OCRProcessingError as e:
                        results.append({'document_id': file_obj.name, 'status': 'error', 'message': f'OCR processing failed: {e}', 'error_type': 'OCR_ERROR'})
                    except DocumentClassificationError as e:
                        results.append({'document_id': file_obj.name, 'status': 'error', 'message': f'Document classification failed: {e}', 'error_type': 'CLASSIFICATION_ERROR'})
                    except EntityExtractionError as e:
                        results.append({'document_id': file_obj.name, 'status': 'error', 'message': f'Entity extraction failed: {e}', 'error_type': 'EXTRACTION_ERROR'})
                    except DocumentProcessingError as e:
                        results.append({'document_id': file_obj.name, 'status': 'error', 'message': f'Document processing failed: {e}', 'error_type': 'PROCESSING_ERROR'})
                    except FileNotFoundError as e:
                        results.append({'document_id': file_obj.name, 'status': 'error', 'message': f'File not found during processing: {e}', 'error_type': 'FILE_NOT_FOUND'})
                    except Exception as e:
                        results.append({'document_id': file_obj.name, 'status': 'error', 'message': f'An unexpected error occurred: {e}', 'error_type': 'UNEXPECTED_ERROR'})
                    finally:
                        if os.path.exists(temp_file_path):
                            os.remove(temp_file_path)
                
                return Response({
                    'status': 'completed',
                    'results': results
                }, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SystemStatusView(APIView):
    """
    Check system status and health of all components.
    """
    
    def get(self, request):
        try:
            status_info = {
                'status': 'healthy',
                'components': {}
            }
            
            # Check OCR Engine
            try:
                ocr_engine = OCRFactory.get_engine()
                status_info['components']['ocr'] = {
                    'status': 'healthy',
                    'engine': ocr_engine.__class__.__name__
                }
            except Exception as e:
                status_info['components']['ocr'] = {
                    'status': 'error',
                    'error': str(e)
                }
                status_info['status'] = 'degraded'
            
            # Check LLM Provider
            try:
                llm_factory = LLMFactory()
                provider = llm_factory.get_provider()
                # Test provider connection
                provider_status = provider.test_connection()
                status_info['components']['llm'] = {
                    'status': 'healthy' if provider_status else 'error',
                    'provider': provider.get_provider_name()
                }
                if not provider_status:
                    status_info['status'] = 'degraded'
            except Exception as e:
                status_info['components']['llm'] = {
                    'status': 'error',
                    'error': str(e)
                }
                status_info['status'] = 'degraded'
            
            # Check Vector Search
            try:
                vector_search = VectorSearch()
                collection_info = vector_search.get_collection_info()
                status_info['components']['vector_search'] = {
                    'status': 'healthy',
                    'collection_count': collection_info.get('document_count', 0)
                }
            except Exception as e:
                status_info['components']['vector_search'] = {
                    'status': 'error',
                    'error': str(e)
                }
                status_info['status'] = 'degraded'
            
            # Check Cache
            try:
                from django.core.cache import cache
                cache.set('health_check', 'ok', 30)
                cache_test = cache.get('health_check')
                status_info['components']['cache'] = {
                    'status': 'healthy' if cache_test == 'ok' else 'error'
                }
                if cache_test != 'ok':
                    status_info['status'] = 'degraded'
            except Exception as e:
                status_info['components']['cache'] = {
                    'status': 'error',
                    'error': str(e)
                }
                status_info['status'] = 'degraded'
            
            return Response(status_info, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'status': 'error',
                'message': f'Health check failed: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DocumentTypesView(APIView):
    """
    Get available document types and their configurations.
    """
    
    def get(self, request):
        try:
            document_types = get_document_types()
            
            # Format response with entity information
            formatted_types = {}
            for doc_type, config in document_types.items():
                formatted_types[doc_type] = {
                    'name': config.name,
                    'description': getattr(config, 'description', f'{doc_type.title()} documents'),
                    'entities': [
                        {
                            'name': entity['name'],
                            'type': entity['type'],
                            'required': entity.get('required', False),
                            'description': entity.get('description', '')
                        }
                        for entity in config.entities
                    ],
                    'keywords': getattr(config, 'keywords', [])
                }
            
            return Response({
                'status': 'success',
                'document_types': formatted_types,
                'total_types': len(document_types)
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'status': 'error',
                'message': f'Failed to retrieve document types: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class StatisticsView(APIView):
    """
    Get system performance statistics.
    """
    
    def get(self, request):
        try:
            stats = {
                'classification': {},
                'extraction': {},
                'vector_search': {}
            }
            
            # Get classification statistics
            try:
                classifier = DocumentClassifier()
                classification_stats = classifier.get_classification_statistics()
                stats['classification'] = classification_stats
            except Exception as e:
                logger.warning(f"Failed to get classification stats: {e}")
                stats['classification'] = {'error': str(e)}
            
            # Get extraction statistics
            try:
                extractor = get_llm_extractor()
                extraction_stats = extractor.get_extraction_statistics()
                stats['extraction'] = extraction_stats
            except Exception as e:
                logger.warning(f"Failed to get extraction stats: {e}")
                stats['extraction'] = {'error': str(e)}
            
            # Get vector search statistics
            try:
                vector_search = VectorSearch()
                vector_stats = vector_search.get_collection_info()
                stats['vector_search'] = vector_stats
            except Exception as e:
                logger.warning(f"Failed to get vector search stats: {e}")
                stats['vector_search'] = {'error': str(e)}
            
            return Response({
                'status': 'success',
                'statistics': stats
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'status': 'error',
                'message': f'Failed to retrieve statistics: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)