Extraction Module
=================

The extraction module handles entity extraction from documents using Large Language Models (LLMs).

Base Extractor
---------------

.. automodule:: documents.extraction.base
   :members:
   :undoc-members:
   :show-inheritance:

LLM Extractor
-------------

.. automodule:: documents.extraction.llm_extractor
   :members:
   :undoc-members:
   :show-inheritance:

Prompt Manager
--------------

.. automodule:: documents.extraction.prompt_manager
   :members:
   :undoc-members:
   :show-inheritance:

Entity Validator
----------------

.. automodule:: documents.extraction.entity_validator
   :members:
   :undoc-members:
   :show-inheritance:

Usage Example
-------------

.. code-block:: python

   from documents.extraction.llm_extractor import get_llm_extractor
   
   # Get the LLM extractor instance
   extractor = get_llm_extractor()
   
   # Extract entities from a document
   document_text = "Invoice #INV-001 dated 2024-01-15 for $1,234.56"
   document_type = "invoice"
   
   result = extractor.extract_entities(document_type, document_text)
   
   print("Extracted entities:")
   for entity_name, entity_value in result['entities'].items():
       print(f"  {entity_name}: {entity_value}")
   
   print(f"Validation summary: {result['validation_summary']}")

Entity Types
------------

The system supports various entity types with automatic validation:

String Entities
~~~~~~~~~~~~~~~

Basic text fields with optional pattern validation:

.. code-block:: yaml

   - name: vendor_name
     type: string
     required: true
     min_length: 2
     max_length: 100

Date Entities
~~~~~~~~~~~~~

Date fields with automatic format normalization:

.. code-block:: yaml

   - name: invoice_date
     type: date
     required: true
     description: "Date the invoice was issued"

Amount Entities
~~~~~~~~~~~~~~~

Monetary amounts with currency detection:

.. code-block:: yaml

   - name: total_amount
     type: amount
     required: true
     min_value: 0
     description: "Total invoice amount"

Number Entities
~~~~~~~~~~~~~~~

Numeric values with range validation:

.. code-block:: yaml

   - name: quantity
     type: number
     required: false
     min_value: 1
     max_value: 1000

Array Entities
~~~~~~~~~~~~~~

Lists of items:

.. code-block:: yaml

   - name: line_items
     type: array
     required: false
     description: "List of invoice line items"

Boolean Entities
~~~~~~~~~~~~~~~~

True/false values:

.. code-block:: yaml

   - name: is_paid
     type: boolean
     required: false
     description: "Whether the invoice has been paid"

Prompt Templates
----------------

Entity extraction uses document-specific prompt templates located in ``config/prompts/``:

* ``default.txt``: Fallback template for all document types
* ``invoice.txt``: Specialized template for invoices
* ``contract.txt``: Specialized template for contracts
* ``form.txt``: Specialized template for forms
* And more...

Custom Prompt Example
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: text

   You are an expert at extracting information from invoice documents.
   
   Extract the following entities from this invoice document:
   
   - invoice_number (string, REQUIRED): The unique invoice identifier
   - amount (amount, REQUIRED): Total amount due including currency symbol
   - date (date, REQUIRED): Invoice date in YYYY-MM-DD format
   
   Guidelines:
   1. Be precise and extract exactly what's written
   2. Use null for missing values
   3. Return only valid JSON
   
   Document text:
   {document_text}
   
   Return ONLY a valid JSON object with the extracted entities:

Validation Process
------------------

Entity validation follows these steps:

1. **Type Validation**: Ensure extracted value matches expected type
2. **Format Normalization**: Convert to standard formats (dates, amounts)
3. **Range Checking**: Validate against min/max constraints
4. **Pattern Matching**: Check against regex patterns if specified
5. **Required Field Validation**: Ensure all required fields are present

Statistics and Monitoring
--------------------------

The extraction system provides comprehensive statistics:

.. code-block:: python

   # Get extraction statistics
   stats = extractor.get_extraction_statistics()
   
   print(f"Total extractions: {stats['total_extractions']}")
   print(f"Success rate: {stats['success_rate']:.2%}")
   print(f"Cache hit rate: {stats['cache_hit_rate']:.2%}")
   
   # Get validation statistics
   validation_stats = stats['validation_statistics']
   print(f"Validation success rate: {validation_stats['successful_validations'] / validation_stats['total_validations']:.2%}")