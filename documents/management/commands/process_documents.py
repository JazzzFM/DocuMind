import os
import csv
import time
from collections import defaultdict
from django.core.management.base import BaseCommand
from documents.ocr.factory import OCRFactory
from documents.classification.classifier import DocumentClassifier
from documents.extraction.llm_extractor import LLMExtractor
from concurrent.futures import ThreadPoolExecutor, as_completed
from django.conf import settings

class Command(BaseCommand):
    help = 'Processes documents in a given directory.'

    def add_arguments(self, parser):
        parser.add_argument('--input-dir', type=str, help='The input directory containing documents.', required=True)
        parser.add_argument('--workers', type=int, default=settings.WORKER_PROCESSES, help='Number of concurrent workers.')
        parser.add_argument('--output-csv', type=str, help='Optional: Path to a CSV file to save results.')

    def handle(self, *args, **options):
        input_dir = options['input_dir']
        workers = options['workers']
        output_csv = options['output_csv']

        if not os.path.isdir(input_dir):
            self.stderr.write(self.style.ERROR(f'Input directory "{input_dir}" does not exist.'))
            return

        self.stdout.write(self.style.SUCCESS(f'Starting document processing in "{input_dir}" with {workers} workers...'))

        ocr_engine = OCRFactory.get_engine()
        classifier = DocumentClassifier()
        extractor = LLMExtractor()

        files_to_process = [os.path.join(input_dir, f) for f in os.listdir(input_dir) if os.path.isfile(os.path.join(input_dir, f))]

        results = []
        start_time = time.time()
        processed_count = 0
        successful_count = 0
        failed_count = 0
        doc_type_counts = defaultdict(int)

        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_file = {executor.submit(self._process_single_file, file_path, ocr_engine, classifier, extractor): file_path for file_path in files_to_process}
            for future in as_completed(future_to_file):
                file_path = future_to_file[future]
                processed_count += 1
                try:
                    result = future.result()
                    results.append(result)
                    successful_count += 1
                    doc_type_counts[result['document_type']] += 1
                    self.stdout.write(f"Processed {os.path.basename(file_path)}: {result['document_type']} (Confidence: {result['confidence']:.2f})")
                except Exception as exc:
                    failed_count += 1
                    self.stderr.write(self.style.ERROR(f'Error processing {os.path.basename(file_path)}: {exc}'))
                    results.append({'filename': os.path.basename(file_path), 'status': 'failed', 'error': str(exc)})

        end_time = time.time()
        total_time = end_time - start_time

        self.stdout.write(self.style.SUCCESS('\nDocument processing finished.'))
        self.stdout.write(self.style.SUCCESS(f'Total files processed: {processed_count}'))
        self.stdout.write(self.style.SUCCESS(f'Successful: {successful_count}'))
        self.stdout.write(self.style.ERROR(f'Failed: {failed_count}'))
        self.stdout.write(self.style.SUCCESS(f'Total time: {total_time:.2f} seconds'))
        self.stdout.write(self.style.SUCCESS(f'Documents by type: {dict(doc_type_counts)}'))

        if output_csv:
            self.stdout.write(f'Saving results to {output_csv}...')
            self._write_results_to_csv(output_csv, results)
            self.stdout.write(self.style.SUCCESS('Results saved.'))

    def _process_single_file(self, file_path, ocr_engine, classifier, extractor):
        filename = os.path.basename(file_path)
        text = ocr_engine.extract_text(file_path)

        doc_type, confidence, _ = classifier.classify(text)
        
        extracted_entities = {}
        if doc_type != 'unknown':
            extracted_entities = extractor.extract_entities(doc_type, text)
            classifier.add_document_to_index(filename, text, doc_type, extracted_entities) # Add to ChromaDB

        return {
            'filename': filename,
            'document_type': doc_type,
            'confidence': confidence,
            'entities': extracted_entities,
            'status': 'success',
            'error': None
        }

    def _write_results_to_csv(self, output_csv_path, results):
        if not results:
            return

        # Determine all possible headers from all results
        all_keys = set()
        for res in results:
            all_keys.update(res.keys())
            if 'entities' in res and isinstance(res['entities'], dict):
                all_keys.update(res['entities'].keys())
        
        # Define a consistent order for common fields
        ordered_headers = ['filename', 'status', 'document_type', 'confidence', 'error']
        # Add other keys, ensuring 'entities' is not a top-level header
        for key in sorted(list(all_keys)):
            if key not in ordered_headers and key != 'entities':
                ordered_headers.append(key)

        with open(output_csv_path, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=ordered_headers)
            writer.writeheader()
            for res in results:
                row = {k: v for k, v in res.items() if k != 'entities'} # Exclude 'entities' key itself
                if 'entities' in res and isinstance(res['entities'], dict):
                    row.update(res['entities'])
                writer.writerow(row)
