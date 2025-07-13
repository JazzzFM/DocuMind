Documents Module
================

The documents module is the core of DocuMind, providing document processing, classification, and entity extraction capabilities.

Overview
--------

The documents module contains several sub-modules:

- **OCR**: Text extraction from images and PDFs
- **Classification**: Document type classification using hybrid approach
- **Extraction**: Entity extraction using LLMs
- **LLM**: Large Language Model integration layer
- **Storage**: Vector database and document storage

Core Components
---------------

Document Processor
~~~~~~~~~~~~~~~~~~

.. automodule:: documents.processor
   :members:
   :undoc-members:
   :show-inheritance:

Configuration Loader
~~~~~~~~~~~~~~~~~~~~~

.. automodule:: documents.config_loader
   :members:
   :undoc-members:
   :show-inheritance:

Document Processing Pipeline
----------------------------

The document processing pipeline follows these steps:

1. **OCR Processing**: Extract text from document images
2. **Classification**: Determine document type using hybrid approach
3. **Entity Extraction**: Extract structured entities using LLMs
4. **Validation**: Validate extracted entities against schemas
5. **Storage**: Store results in vector database

Pipeline Example
~~~~~~~~~~~~~~~~

.. code-block:: python

   from documents.processor import DocumentProcessor
   
   # Initialize processor
   processor = DocumentProcessor()
   
   # Process a document
   with open('invoice.pdf', 'rb') as file:
       result = processor.process_document(
           file_content=file.read(),
           filename='invoice.pdf',
           extract_entities=True
       )
   
   print(f"Document Type: {result['document_type']}")
   print(f"Confidence: {result['confidence']}")
   print(f"Entities: {result['extracted_entities']}")

Configuration Management
------------------------

Document types and their entity schemas are configured via YAML files:

Document Types Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Located at ``config/document_types.yaml``:

.. code-block:: yaml

   invoice:
     entities:
       - name: invoice_number
         type: string
         required: true
         description: "Unique invoice identifier"
       - name: amount
         type: amount
         required: true
         description: "Total invoice amount"
       - name: date
         type: date
         required: true
         description: "Invoice date"
     keywords:
       - invoice
       - bill
       - payment

Loading Configuration
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from documents.config_loader import load_document_types
   
   # Load all document types
   document_types = load_document_types()
   
   # Access specific type
   invoice_config = document_types['invoice']
   print(f"Invoice entities: {invoice_config.entities}")

Entity Schemas
--------------

The system supports various entity types with validation:

String Entities
~~~~~~~~~~~~~~~

.. code-block:: yaml

   - name: vendor_name
     type: string
     required: true
     min_length: 2
     max_length: 100
     pattern: "^[A-Za-z0-9\\s&.-]+$"

Date Entities
~~~~~~~~~~~~~

.. code-block:: yaml

   - name: invoice_date
     type: date
     required: true
     description: "Date the invoice was issued"

Amount Entities
~~~~~~~~~~~~~~~

.. code-block:: yaml

   - name: total_amount
     type: amount
     required: true
     min_value: 0
     description: "Total invoice amount with currency"

Number Entities
~~~~~~~~~~~~~~~

.. code-block:: yaml

   - name: line_count
     type: number
     required: false
     min_value: 1
     max_value: 100

Array Entities
~~~~~~~~~~~~~~

.. code-block:: yaml

   - name: line_items
     type: array
     required: false
     description: "List of invoice line items"

Boolean Entities
~~~~~~~~~~~~~~~~

.. code-block:: yaml

   - name: is_paid
     type: boolean
     required: false
     description: "Payment status"

Processing Statistics
---------------------

The documents module tracks comprehensive processing statistics:

.. code-block:: python

   from documents.processor import DocumentProcessor
   
   processor = DocumentProcessor()
   stats = processor.get_processing_statistics()
   
   print(f"Total documents processed: {stats['total_processed']}")
   print(f"Classification accuracy: {stats['classification_accuracy']:.2%}")
   print(f"Extraction success rate: {stats['extraction_success_rate']:.2%}")
   print(f"Average processing time: {stats['avg_processing_time_ms']}ms")

Document Type Distribution
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Get document type statistics
   type_stats = stats['document_types']
   for doc_type, count in type_stats.items():
       print(f"{doc_type}: {count} documents")

Processing Performance
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Performance metrics
   performance = stats['performance']
   print(f"OCR average time: {performance['ocr_avg_time_ms']}ms")
   print(f"Classification average time: {performance['classification_avg_time_ms']}ms")
   print(f"Extraction average time: {performance['extraction_avg_time_ms']}ms")

Error Handling
--------------

The documents module implements comprehensive error handling:

Processing Errors
~~~~~~~~~~~~~~~~~

.. code-block:: python

   try:
       result = processor.process_document(file_content, filename)
   except OCRProcessingError as e:
       print(f"OCR failed: {e}")
   except ClassificationError as e:
       print(f"Classification failed: {e}")
   except ExtractionError as e:
       print(f"Entity extraction failed: {e}")
   except ValidationError as e:
       print(f"Validation failed: {e}")

Custom Exceptions
~~~~~~~~~~~~~~~~~

.. code-block:: python

   class DocumentProcessingError(Exception):
       """Base exception for document processing errors"""
       pass
   
   class OCRProcessingError(DocumentProcessingError):
       """Raised when OCR processing fails"""
       pass
   
   class ClassificationError(DocumentProcessingError):
       """Raised when document classification fails"""
       pass

Caching and Performance
-----------------------

The documents module implements multiple levels of caching:

OCR Caching
~~~~~~~~~~~

OCR results are cached based on document hash to avoid reprocessing:

.. code-block:: python

   # OCR cache configuration
   OCR_CACHE_TIMEOUT = 3600  # 1 hour
   OCR_CACHE_KEY_PREFIX = "ocr:"

Classification Caching
~~~~~~~~~~~~~~~~~~~~~~~

Classification results are cached for similar documents:

.. code-block:: python

   # Classification cache configuration
   CLASSIFICATION_CACHE_TIMEOUT = 1800  # 30 minutes
   CLASSIFICATION_CACHE_KEY_PREFIX = "classification:"

Extraction Caching
~~~~~~~~~~~~~~~~~~~

LLM extraction results are cached to reduce API costs:

.. code-block:: python

   # Extraction cache configuration
   EXTRACTION_CACHE_TIMEOUT = 7200  # 2 hours
   EXTRACTION_CACHE_KEY_PREFIX = "extraction:"

Testing
-------

The documents module includes comprehensive tests:

.. code-block:: bash

   # Run all document tests
   python manage.py test documents.tests
   
   # Run specific test modules
   python manage.py test documents.tests.test_processor
   python manage.py test documents.tests.test_config_loader

Unit Tests
~~~~~~~~~~

.. code-block:: python

   from django.test import TestCase
   from documents.processor import DocumentProcessor
   
   class DocumentProcessorTestCase(TestCase):
       def setUp(self):
           self.processor = DocumentProcessor()
       
       def test_process_pdf_document(self):
           with open('test_files/sample_invoice.pdf', 'rb') as f:
               result = self.processor.process_document(
                   f.read(), 
                   'sample_invoice.pdf'
               )
           
           self.assertEqual(result['status'], 'success')
           self.assertEqual(result['document_type'], 'invoice')
           self.assertGreater(result['confidence'], 0.8)

Integration Tests
~~~~~~~~~~~~~~~~~

.. code-block:: python

   class DocumentPipelineIntegrationTestCase(TestCase):
       def test_complete_pipeline(self):
           """Test complete document processing pipeline"""
           # Test OCR -> Classification -> Extraction workflow
           pass

Extending the Module
--------------------

To extend the documents module:

1. **Add Document Types**: Update ``config/document_types.yaml``
2. **Custom Processors**: Inherit from base processor classes
3. **New Entity Types**: Extend the entity validation system
4. **Custom Validators**: Create custom validation functions

Adding New Document Types
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   # Add to config/document_types.yaml
   purchase_order:
     entities:
       - name: po_number
         type: string
         required: true
       - name: supplier
         type: string
         required: true
       - name: items
         type: array
         required: false
     keywords:
       - purchase order
       - PO
       - procurement

Custom Entity Validators
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from documents.extraction.entity_validator import register_validator
   
   @register_validator('email')
   def validate_email(value, config):
       """Custom email validation"""
       import re
       email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
       if re.match(email_pattern, value):
           return ValidationResult(value=value, is_valid=True)
       else:
           return ValidationResult(
               value=value, 
               is_valid=False, 
               error_message="Invalid email format"
           )

Configuration
-------------

Environment variables for the documents module:

.. code-block:: bash

   # Document processing settings
   DOCUMENT_TYPES_CONFIG_PATH=config/document_types.yaml
   PROMPTS_CONFIG_PATH=config/prompts/
   
   # Processing timeouts
   OCR_TIMEOUT_SECONDS=30
   CLASSIFICATION_TIMEOUT_SECONDS=10
   EXTRACTION_TIMEOUT_SECONDS=60
   
   # Cache settings
   ENABLE_PROCESSING_CACHE=true
   CACHE_TIMEOUT_SECONDS=3600