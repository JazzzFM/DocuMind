Classification Module
====================

The classification module implements a hybrid document classification system using vector embeddings and keyword matching.

Document Classifier
--------------------

.. automodule:: documents.classification.classifier
   :members:
   :undoc-members:
   :show-inheritance:

Embedding Generator
-------------------

.. automodule:: documents.classification.embedding_generator
   :members:
   :undoc-members:
   :show-inheritance:

Keyword Matcher
----------------

.. automodule:: documents.classification.keyword_matcher
   :members:
   :undoc-members:
   :show-inheritance:

Vector Search
-------------

.. automodule:: documents.classification.vector_search
   :members:
   :undoc-members:
   :show-inheritance:

Feedback Tracker
-----------------

.. automodule:: documents.classification.feedback_tracker
   :members:
   :undoc-members:
   :show-inheritance:

Usage Example
-------------

.. code-block:: python

   from documents.classification.classifier import DocumentClassifier
   
   # Initialize classifier
   classifier = DocumentClassifier()
   
   # Classify a document
   document_text = "Invoice #12345 dated 2024-01-15..."
   doc_type, confidence = classifier.classify(document_text)
   
   print(f"Document Type: {doc_type}")
   print(f"Confidence: {confidence:.2f}")
   
   # Add document to vector index
   classifier.add_document_to_index(
       document_id="doc_123",
       text=document_text,
       document_type=doc_type,
       metadata={"amount": "$1,234.56"}
   )

Classification Process
----------------------

The classification process follows these steps:

1. **Text Preprocessing**: Clean and normalize input text
2. **Embedding Generation**: Generate vector embeddings using Sentence Transformers
3. **Vector Search**: Query ChromaDB for similar documents
4. **Keyword Matching**: Apply keyword-based scoring
5. **Score Combination**: Combine vector and keyword scores
6. **Classification**: Return document type with confidence score

Document Types
--------------

Currently supported document types:

* **invoice**: Invoice documents with billing information
* **contract**: Legal contracts and agreements  
* **form**: Application forms and questionnaires
* **report**: Business reports and analyses
* **assignment**: Academic assignments and homework
* **advertisement**: Marketing and promotional materials
* **budget**: Financial budgets and planning documents
* **email**: Email communications
* **file_folder**: File organization documents

Configuration
-------------

Document types are configured in ``config/document_types.yaml``:

.. code-block:: yaml

   invoice:
     name: "Invoice"
     keywords: ["invoice", "bill", "payment", "due date"]
     entities:
       - name: invoice_number
         type: string
         required: true
       - name: amount
         type: amount
         required: true