from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from documents.ocr.factory import OCRFactory
from documents.classification.classifier import DocumentClassifier
from documents.extraction.llm_extractor import LLMExtractor
from .serializers import DocumentProcessSerializer, DocumentSearchSerializer, DocumentBatchProcessSerializer
from documents.classification.vector_search import VectorSearch
from documents.exceptions import DocumentProcessingError, OCRProcessingError, DocumentClassificationError, EntityExtractionError
import os
import uuid

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
                extractor = LLMExtractor()

                # OCR
                text = ocr_engine.extract_text(temp_file_path)

                # Classification
                doc_type, confidence = classifier.classify(text)

                extracted_entities_data = {}
                if extract_entities and doc_type != 'unknown':
                    extracted_entities_data = extractor.extract_entities(doc_type, text)
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
                        extractor = LLMExtractor()

                        text = ocr_engine.extract_text(temp_file_path)
                        doc_type, confidence = classifier.classify(text)
                        extracted_entities_data = {}
                        if doc_type != 'unknown':
                            extracted_entities_data = extractor.extract_entities(doc_type, text)
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