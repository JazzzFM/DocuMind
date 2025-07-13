"""
Django management command for batch processing documents
"""
import os
import logging
from pathlib import Path
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import json
import csv
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from documents.ocr.factory import OCREngineFactory
from documents.classification.classifier import DocumentClassifier
from documents.extraction.llm_extractor import LLMEntityExtractor
from documents.models import ProcessedDocument

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Process documents in batch mode"""
    
    help = 'Process documents for classification and entity extraction'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--input-dir',
            type=str,
            required=True,
            help='Directory containing documents to process'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=10,
            help='Number of documents to process in each batch'
        )
        parser.add_argument(
            '--workers',
            type=int,
            default=settings.WORKER_PROCESSES,
            help='Number of worker processes'
        )
        parser.add_argument(
            '--skip-errors',
            action='store_true',
            help='Skip documents that fail processing'
        )
        parser.add_argument(
            '--output-file',
            type=str,
            help='Output CSV file for results'
        )
        parser.add_argument(
            '--ocr-engine',
            type=str,
            choices=OCREngineFactory.get_available_engines(),
            default=settings.OCR_ENGINE,
            help='OCR engine to use'
        )
        parser.add_argument(
            '--reprocess',
            action='store_true',
            help='Reprocess documents even if already in database'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run without saving to database'
        )
        parser.add_argument(
            '--log-level',
            type=str,
            choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
            default='INFO',
            help='Logging level'
        )
        parser.add_argument(
            '--file-pattern',
            type=str,
            default='*',
            help='File pattern to match (e.g., "*.pdf")'
        )
    
    def handle(self, *args, **options):
        # Configure logging
        logging.getLogger().setLevel(getattr(logging, options['log_level']))
        
        # Validate input directory
        input_dir = Path(options['input_dir'])
        if not input_dir.exists():
            raise CommandError(f"Input directory does not exist: {input_dir}")
        
        # Initialize components
        self.ocr_engine = OCREngineFactory.create_engine(options['ocr_engine'])
        self.classifier = DocumentClassifier()
        self.extractor = LLMEntityExtractor()
        
        # Collect documents to process
        documents = self._collect_documents(input_dir, options['file_pattern'])
        
        if not documents:
            self.stdout.write(self.style.WARNING('No documents found to process'))
            return
        
        self.stdout.write(
            self.style.SUCCESS(f'Found {len(documents)} documents to process')
        )
        
        # Process documents
        results = self._process_documents_batch(
            documents,
            batch_size=options['batch_size'],
            workers=options['workers'],
            skip_errors=options['skip_errors'],
            reprocess=options['reprocess'],
            dry_run=options['dry_run']
        )
        
        # Save results if requested
        if options['output_file']:
            self._save_results(results, options['output_file'])
        
        # Print summary
        self._print_summary(results)
    
    def _collect_documents(self, input_dir: Path, pattern: str) -> List[Path]:
        """Collect all documents matching the pattern"""
        documents = []
        
        for ext in settings.ALLOWED_FILE_EXTENSIONS:
            if pattern == '*' or pattern.endswith(ext):
                documents.extend(input_dir.glob(f'**/*{ext}'))
        
        # Also check for specific pattern
        if pattern != '*':
            documents.extend(input_dir.glob(f'**/{pattern}'))
        
        # Remove duplicates and sort
        documents = sorted(list(set(documents)))
        
        return documents
    
    def _process_documents_batch(self, documents: List[Path], batch_size: int,
                               workers: int, skip_errors: bool, 
                               reprocess: bool, dry_run: bool) -> List[Dict[str, Any]]:
        """Process documents in batches"""
        results = []
        total_batches = (len(documents) + batch_size - 1) // batch_size
        
        self.stdout.write(f'Processing {len(documents)} documents in {total_batches} batches...')
        
        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, len(documents))
            batch = documents[start_idx:end_idx]
            
            self.stdout.write(
                f'Processing batch {batch_num + 1}/{total_batches} '
                f'({len(batch)} documents)...'
            )
            
            # Process batch in parallel
            batch_results = self._process_batch_parallel(
                batch, workers, skip_errors, reprocess, dry_run
            )
            results.extend(batch_results)
        
        return results
    
    def _process_batch_parallel(self, batch: List[Path], workers: int,
                              skip_errors: bool, reprocess: bool,
                              dry_run: bool) -> List[Dict[str, Any]]:
        """Process a batch of documents in parallel"""
        results = []
        
        with ThreadPoolExecutor(max_workers=workers) as executor:
            # Submit tasks
            future_to_doc = {
                executor.submit(
                    self._process_single_document,
                    doc_path,
                    skip_errors,
                    reprocess,
                    dry_run
                ): doc_path
                for doc_path in batch
            }
            
            # Process results with progress bar
            with tqdm(total=len(batch), desc="Processing") as pbar:
                for future in as_completed(future_to_doc):
                    doc_path = future_to_doc[future]
                    try:
                        result = future.result()
                        if result:
                            results.append(result)
                    except Exception as e:
                        logger.error(f"Failed to process {doc_path}: {str(e)}")
                        if not skip_errors:
                            raise
                    finally:
                        pbar.update(1)
        
        return results
    
    def _process_single_document(self, doc_path: Path, skip_errors: bool,
                               reprocess: bool, dry_run: bool) -> Optional[Dict[str, Any]]:
        """Process a single document"""
        try:
            # Check if already processed
            if not reprocess and not dry_run:
                existing = ProcessedDocument.objects.filter(
                    file_path=str(doc_path)
                ).first()
                if existing:
                    logger.info(f"Skipping already processed document: {doc_path}")
                    return None
            
            # Start processing
            start_time = datetime.now()
            result = {
                'file_path': str(doc_path),
                'file_name': doc_path.name,
                'status': 'processing',
                'start_time': start_time
            }
            
            # OCR
            logger.info(f"Performing OCR on {doc_path.name}")
            ocr_result = self.ocr_engine.extract_text(str(doc_path))
            result['ocr_confidence'] = ocr_result.confidence
            result['text_length'] = len(ocr_result.text)
            
            # Classification
            logger.info(f"Classifying {doc_path.name}")
            classification = self.classifier.classify_document(ocr_result.text)
            result['document_type'] = classification['document_type']
            result['classification_confidence'] = classification['confidence']
            
            # Entity extraction
            if classification['document_type'] != 'unknown':
                doc_type_config = self.classifier.document_types.get(
                    classification['document_type']
                )
                if doc_type_config:
                    logger.info(f"Extracting entities from {doc_path.name}")
                    entities = self.extractor.extract_entities(
                        ocr_result.text,
                        classification['document_type'],
                        doc_type_config.entities
                    )
                    result['extracted_entities'] = entities
            
            # Add to vector database
            if not dry_run:
                doc_id = f"doc_{doc_path.stem}_{start_time.timestamp()}"
                self.classifier.add_document_to_index(
                    document_id=doc_id,
                    text=ocr_result.text,
                    document_type=classification['document_type'],
                    metadata={
                        'file_path': str(doc_path),
                        'ocr_confidence': ocr_result.confidence,
                        'classification_confidence': classification['confidence']
                    }
                )
                result['document_id'] = doc_id
                
                # Save to database
                self._save_to_database(result, ocr_result.text)
            
            # Calculate processing time
            end_time = datetime.now()
            result['processing_time'] = (end_time - start_time).total_seconds()
            result['status'] = 'success'
            
            logger.info(
                f"Successfully processed {doc_path.name} as {result['document_type']} "
                f"in {result['processing_time']:.2f}s"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing {doc_path}: {str(e)}")
            if skip_errors:
                return {
                    'file_path': str(doc_path),
                    'file_name': doc_path.name,
                    'status': 'error',
                    'error': str(e)
                }
            else:
                raise
    
    def _save_to_database(self, result: Dict[str, Any], text: str):
        """Save processing result to database"""
        ProcessedDocument.objects.update_or_create(
            file_path=result['file_path'],
            defaults={
                'file_name': result['file_name'],
                'document_type': result['document_type'],
                'ocr_text': text,
                'ocr_confidence': result['ocr_confidence'],
                'classification_confidence': result['classification_confidence'],
                'extracted_entities': result.get('extracted_entities', {}),
                'processing_time': result['processing_time'],
                'document_id': result.get('document_id', ''),
            }
        )
    
    def _save_results(self, results: List[Dict[str, Any]], output_file: str):
        """Save results to CSV file"""
        if not results:
            return
        
        # Prepare CSV data
        fieldnames = [
            'file_name', 'document_type', 'classification_confidence',
            'ocr_confidence', 'processing_time', 'status', 'error'
        ]
        
        # Add entity fields
        entity_fields = set()
        for result in results:
            if 'extracted_entities' in result:
                entity_fields.update(result['extracted_entities'].keys())
        
        fieldnames.extend(sorted(entity_fields))
        
        # Write CSV
        with open(output_file, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for result in results:
                row = {
                    'file_name': result['file_name'],
                    'document_type': result.get('document_type', 'unknown'),
                    'classification_confidence': result.get('classification_confidence', 0),
                    'ocr_confidence': result.get('ocr_confidence', 0),
                    'processing_time': result.get('processing_time', 0),
                    'status': result['status'],
                    'error': result.get('error', '')
                }
                
                # Add entity values
                if 'extracted_entities' in result:
                    for entity, value in result['extracted_entities'].items():
                        row[entity] = json.dumps(value) if isinstance(value, (list, dict)) else value
                
                writer.writerow(row)
        
        self.stdout.write(
            self.style.SUCCESS(f'Results saved to {output_file}')
        )
    
    def _print_summary(self, results: List[Dict[str, Any]]):
        """Print processing summary"""
        total = len(results)
        successful = sum(1 for r in results if r.get('status') == 'success')
        errors = sum(1 for r in results if r.get('status') == 'error')
        
        # Document type distribution
        type_counts = {}
        for result in results:
            if result.get('status') == 'success':
                doc_type = result.get('document_type', 'unknown')
                type_counts[doc_type] = type_counts.get(doc_type, 0) + 1
        
        # Average metrics
        avg_ocr_conf = sum(r.get('ocr_confidence', 0) for r in results if r.get('status') == 'success') / max(successful, 1)
        avg_class_conf = sum(r.get('classification_confidence', 0) for r in results if r.get('status') == 'success') / max(successful, 1)
        avg_time = sum(r.get('processing_time', 0) for r in results if r.get('status') == 'success') / max(successful, 1)
        
        # Print summary
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('PROCESSING SUMMARY'))
        self.stdout.write('='*60)
        self.stdout.write(f'Total documents: {total}')
        self.stdout.write(f'Successful: {successful}')
        self.stdout.write(f'Errors: {errors}')
        self.stdout.write('')
        
        self.stdout.write('Document Type Distribution:')
        for doc_type, count in sorted(type_counts.items()):
            percentage = (count / successful * 100) if successful > 0 else 0
            self.stdout.write(f'  {doc_type}: {count} ({percentage:.1f}%)')
        
        self.stdout.write('')
        self.stdout.write('Average Metrics:')
        self.stdout.write(f'  OCR Confidence: {avg_ocr_conf:.2%}')
        self.stdout.write(f'  Classification Confidence: {avg_class_conf:.2%}')
        self.stdout.write(f'  Processing Time: {avg_time:.2f}s')
        self.stdout.write('='*60)
