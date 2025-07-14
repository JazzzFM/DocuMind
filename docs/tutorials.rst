Tutorials and Examples
======================

This section provides practical tutorials and examples for using DocuMind in various scenarios.

.. toctree::
   :maxdepth: 2
   :caption: Tutorials

   tutorials/getting_started
   tutorials/api_usage
   tutorials/batch_processing
   tutorials/custom_document_types
   tutorials/advanced_configuration

Getting Started Tutorial
=========================

This tutorial will walk you through setting up DocuMind and processing your first document.

Prerequisites
-------------

Before starting, ensure you have:

- Docker and Docker Compose installed
- Python 3.9+ (for local development)
- An OpenAI API key (for entity extraction)

Quick Setup
-----------

1. **Clone the repository:**

   .. code-block:: bash

      git clone https://github.com/yourusername/documind.git
      cd documind

2. **Configure environment variables:**

   .. code-block:: bash

      cp .env.example .env
      # Edit .env with your configuration

3. **Start the services:**

   .. code-block:: bash

      docker-compose -f docker-compose.prod.yml up -d

4. **Verify the installation:**

   .. code-block:: bash

      curl http://localhost:8000/api/v1/system/status/

First Document Processing
--------------------------

Let's process a sample invoice document:

.. code-block:: python

   import requests
   import json

   # API configuration
   BASE_URL = "http://localhost:8000/api/v1"
   
   # Step 1: Get authentication token
   auth_response = requests.post(f"{BASE_URL}/token/", {
       "username": "admin",
       "password": "adminpassword"
   })
   token = auth_response.json()["access"]
   
   # Step 2: Set up headers
   headers = {
       "Authorization": f"Bearer {token}"
   }
   
   # Step 3: Process a document
   with open("sample_invoice.pdf", "rb") as file:
       response = requests.post(
           f"{BASE_URL}/documents/process/",
           headers=headers,
           files={"file": file},
           data={"extract_entities": True}
       )
   
   # Step 4: View results
   result = response.json()
   print(json.dumps(result, indent=2))

Expected output:

.. code-block:: json

   {
     "status": "success",
     "document_id": "sample_invoice.pdf",
     "document_type": "invoice",
     "confidence": 0.95,
     "extracted_entities": {
       "invoice_number": "INV-2024-001",
       "vendor_name": "Acme Corporation",
       "total_amount": "$1,234.56",
       "invoice_date": "2024-01-15",
       "due_date": "2024-02-15"
     }
   }

API Usage Examples
==================

Authentication
--------------

All API endpoints require JWT authentication:

.. code-block:: python

   import requests

   def get_auth_token(username, password):
       """Get JWT authentication token"""
       response = requests.post("http://localhost:8000/api/v1/token/", {
           "username": username,
           "password": password
       })
       return response.json()["access"]

   def make_authenticated_request(endpoint, token, method="GET", **kwargs):
       """Make authenticated API request"""
       headers = {"Authorization": f"Bearer {token}"}
       if method == "GET":
           return requests.get(endpoint, headers=headers, **kwargs)
       elif method == "POST":
           return requests.post(endpoint, headers=headers, **kwargs)

Document Processing
-------------------

**Single Document Processing:**

.. code-block:: python

   def process_document(file_path, token):
       """Process a single document"""
       url = "http://localhost:8000/api/v1/documents/process/"
       headers = {"Authorization": f"Bearer {token}"}
       
       with open(file_path, "rb") as f:
           response = requests.post(
               url,
               headers=headers,
               files={"file": f},
               data={"extract_entities": True}
           )
       
       return response.json()

   # Usage
   token = get_auth_token("admin", "adminpassword")
   result = process_document("invoice.pdf", token)
   print(f"Document type: {result['document_type']}")
   print(f"Confidence: {result['confidence']:.2f}")

**Document Search:**

.. code-block:: python

   def search_documents(query, token, document_type=None, limit=20):
       """Search documents using vector similarity"""
       url = "http://localhost:8000/api/v1/documents/search/"
       headers = {"Authorization": f"Bearer {token}"}
       
       params = {
           "query": query,
           "limit": limit
       }
       if document_type:
           params["document_type"] = document_type
       
       response = requests.get(url, headers=headers, params=params)
       return response.json()

   # Usage
   results = search_documents("invoice Acme Corp", token, document_type="invoice")
   for doc in results["results"]:
       print(f"Document: {doc['document_id']}, Similarity: {doc['similarity']:.2f}")

Batch Processing
================

Command Line Interface
-----------------------

DocuMind provides a Django management command for batch processing:

.. code-block:: bash

   # Process all documents in a directory
   docker-compose -f docker-compose.prod.yml exec web \\
     python documind/manage.py process_documents \\
     --input-dir /path/to/documents \\
     --workers 4 \\
     --output-csv results.csv

**Command options:**

- ``--input-dir``: Directory containing documents to process
- ``--workers``: Number of parallel workers (default: 4)
- ``--output-csv``: Output file for results (optional)

API Batch Processing
--------------------

For programmatic batch processing:

.. code-block:: python

   import os
   import time
   from concurrent.futures import ThreadPoolExecutor, as_completed

   def process_directory(directory_path, token, max_workers=4):
       """Process all documents in a directory"""
       files = [
           os.path.join(directory_path, f) 
           for f in os.listdir(directory_path)
           if f.lower().endswith(('.pdf', '.png', '.jpg', '.jpeg'))
       ]
       
       results = []
       with ThreadPoolExecutor(max_workers=max_workers) as executor:
           # Submit all files for processing
           future_to_file = {
               executor.submit(process_document, file_path, token): file_path
               for file_path in files
           }
           
           # Collect results as they complete
           for future in as_completed(future_to_file):
               file_path = future_to_file[future]
               try:
                   result = future.result()
                   result['file_path'] = file_path
                   results.append(result)
                   print(f"Processed: {os.path.basename(file_path)}")
               except Exception as e:
                   print(f"Error processing {file_path}: {e}")
       
       return results

   # Usage
   token = get_auth_token("admin", "adminpassword")
   results = process_directory("/path/to/documents", token)
   
   # Generate summary
   by_type = {}
   for result in results:
       doc_type = result.get('document_type', 'unknown')
       by_type[doc_type] = by_type.get(doc_type, 0) + 1
   
   print("\\nProcessing Summary:")
   for doc_type, count in by_type.items():
       print(f"  {doc_type}: {count} documents")

Custom Document Types
======================

Adding New Document Types
-------------------------

DocuMind supports adding custom document types via YAML configuration:

.. code-block:: yaml

   # config/document_types.yaml
   receipt:
     name: "Receipt"
     description: "Purchase receipt or sales slip"
     keywords:
       - "receipt"
       - "purchase"
       - "total"
       - "cash"
       - "credit"
     entities:
       - name: "store_name"
         type: "string"
         required: true
         description: "Name of the store or merchant"
       - name: "transaction_date"
         type: "date"
         required: true
         description: "Date of the transaction"
       - name: "total_amount"
         type: "amount"
         required: true
         description: "Total purchase amount"
       - name: "payment_method"
         type: "string"
         required: false
         description: "Payment method used"
       - name: "items"
         type: "array"
         required: false
         description: "List of purchased items"

Custom Prompt Templates
-----------------------

Create custom LLM prompts for new document types:

.. code-block:: text

   # config/prompts/receipt.txt
   You are an expert at extracting information from receipts and purchase documents.
   
   Extract the following information from this receipt:
   
   Required fields:
   - store_name: The name of the store or merchant
   - transaction_date: Date of the transaction (format: YYYY-MM-DD)
   - total_amount: Total amount paid (include currency symbol)
   
   Optional fields:
   - payment_method: How the payment was made (cash, credit, debit, etc.)
   - items: List of items purchased with quantities and prices
   
   Document text:
   {document_text}
   
   Return the information as valid JSON only, no other text:

Testing Custom Types
--------------------

After adding a new document type:

.. code-block:: python

   # Test the new document type
   def test_custom_document_type():
       token = get_auth_token("admin", "adminpassword")
       
       # Check if new type is available
       response = requests.get(
           "http://localhost:8000/api/v1/system/document-types/",
           headers={"Authorization": f"Bearer {token}"}
       )
       doc_types = response.json()["document_types"]
       
       if "receipt" in doc_types:
           print("Receipt document type successfully added!")
           print(f"Keywords: {doc_types['receipt']['keywords']}")
           print(f"Entities: {len(doc_types['receipt']['entities'])} defined")
       else:
           print("Receipt document type not found. Check configuration.")

   test_custom_document_type()

Advanced Configuration
======================

Performance Tuning
-------------------

**OCR Optimization:**

.. code-block:: python

   # Configure OCR engine in settings
   OCR_ENGINE = "tesseract"  # or "google_vision", "azure_form_recognizer"
   OCR_PREPROCESSING = True  # Enable image preprocessing
   OCR_CACHE_TIMEOUT = 3600  # Cache OCR results for 1 hour

**LLM Configuration:**

.. code-block:: python

   # LLM settings for optimal performance
   LLM_PROVIDER = "openai"
   LLM_MODEL = "gpt-4-turbo-preview"  # Balance of speed and accuracy
   LLM_TEMPERATURE = 0.1  # Low temperature for consistent results
   LLM_CACHE_TIMEOUT = 3600  # Cache LLM responses

**Classification Tuning:**

.. code-block:: python

   # Adjust classification weights
   classifier = DocumentClassifier(
       embedding_weight=0.7,  # Increase for better semantic understanding
       keyword_weight=0.3     # Decrease if keywords are less reliable
   )

Monitoring and Logging
----------------------

**Enable detailed logging:**

.. code-block:: python

   # settings.py
   LOGGING = {
       'version': 1,
       'disable_existing_loggers': False,
       'handlers': {
           'file': {
               'level': 'INFO',
               'class': 'logging.FileHandler',
               'filename': '/var/log/documind/app.log',
           },
       },
       'loggers': {
           'documents': {
               'handlers': ['file'],
               'level': 'INFO',
               'propagate': True,
           },
       },
   }

**Monitor system performance:**

.. code-block:: python

   def monitor_system_performance(token):
       """Monitor system performance metrics"""
       response = requests.get(
           "http://localhost:8000/api/v1/system/statistics/",
           headers={"Authorization": f"Bearer {token}"}
       )
       stats = response.json()
       
       print(f"Total documents processed: {stats['total_documents']}")
       print(f"Average processing time: {stats['avg_processing_time_ms']}ms")
       print(f"Classification accuracy: {stats['classification_accuracy']:.1%}")
       print(f"Entity extraction precision: {stats['extraction_precision']:.1%}")

Troubleshooting
===============

Common Issues
-------------

**1. Authentication Errors:**

.. code-block:: python

   # Check token expiration
   import jwt
   import datetime

   def check_token_expiry(token):
       try:
           decoded = jwt.decode(token, options={"verify_signature": False})
           exp_timestamp = decoded.get('exp')
           if exp_timestamp:
               exp_date = datetime.datetime.fromtimestamp(exp_timestamp)
               if exp_date < datetime.datetime.now():
                   print("Token has expired. Please get a new token.")
               else:
                   print(f"Token expires at: {exp_date}")
       except Exception as e:
           print(f"Error checking token: {e}")

**2. Processing Failures:**

.. code-block:: python

   def handle_processing_errors(file_path, token):
       """Robust document processing with error handling"""
       try:
           result = process_document(file_path, token)
           if result.get('status') == 'error':
               print(f"Processing failed: {result.get('message')}")
               return None
           return result
       except requests.exceptions.RequestException as e:
           print(f"Network error: {e}")
           return None
       except Exception as e:
           print(f"Unexpected error: {e}")
           return None

**3. Performance Issues:**

.. code-block:: bash

   # Check system status
   curl -H "Authorization: Bearer $TOKEN" \\
     http://localhost:8000/api/v1/system/status/

   # Monitor Docker container resources
   docker stats documind-web-1

   # Check logs
   docker-compose -f docker-compose.prod.yml logs --tail=100 web

Best Practices
==============

Document Quality
----------------

- **Use high-quality scans**: 300 DPI or higher for best OCR results
- **Ensure proper orientation**: Rotate documents to correct orientation
- **Good lighting**: Avoid shadows and glare in scanned documents
- **Clear text**: Ensure text is legible and not blurred

API Usage
---------

- **Implement retry logic**: Handle temporary failures gracefully
- **Use appropriate timeouts**: Set reasonable timeouts for API calls
- **Batch similar operations**: Group related API calls to improve efficiency
- **Cache authentication tokens**: Reuse tokens until they expire

Security
--------

- **Secure API keys**: Never commit API keys to version control
- **Use HTTPS**: Always use HTTPS in production environments
- **Implement rate limiting**: Protect against abuse with proper rate limits
- **Regular updates**: Keep the system updated with security patches

Example Integration
===================

Here's a complete example integrating DocuMind into a document management workflow:

.. code-block:: python

   import os
   import json
   import logging
   from datetime import datetime
   from typing import List, Dict, Optional

   class DocumentProcessor:
       """Complete document processing workflow"""
       
       def __init__(self, base_url: str, username: str, password: str):
           self.base_url = base_url
           self.username = username
           self.password = password
           self.token = None
           self.logger = logging.getLogger(__name__)
       
       def authenticate(self) -> bool:
           """Authenticate and get access token"""
           try:
               response = requests.post(f"{self.base_url}/token/", {
                   "username": self.username,
                   "password": self.password
               })
               if response.status_code == 200:
                   self.token = response.json()["access"]
                   return True
               return False
           except Exception as e:
               self.logger.error(f"Authentication failed: {e}")
               return False
       
       def process_workflow(self, input_dir: str, output_dir: str) -> Dict:
           """Complete document processing workflow"""
           if not self.authenticate():
               raise Exception("Authentication failed")
           
           results = {
               "processed": 0,
               "failed": 0,
               "by_type": {},
               "errors": []
           }
           
           for filename in os.listdir(input_dir):
               if not filename.lower().endswith(('.pdf', '.png', '.jpg', '.jpeg')):
                   continue
               
               file_path = os.path.join(input_dir, filename)
               try:
                   # Process document
                   result = self.process_document(file_path)
                   
                   if result.get("status") == "success":
                       # Update statistics
                       results["processed"] += 1
                       doc_type = result["document_type"]
                       results["by_type"][doc_type] = results["by_type"].get(doc_type, 0) + 1
                       
                       # Save results
                       output_file = os.path.join(output_dir, f"{filename}.json")
                       with open(output_file, "w") as f:
                           json.dump(result, f, indent=2)
                       
                       self.logger.info(f"Processed: {filename} -> {doc_type}")
                   else:
                       results["failed"] += 1
                       results["errors"].append(f"{filename}: {result.get('message')}")
                       
               except Exception as e:
                   results["failed"] += 1
                   results["errors"].append(f"{filename}: {str(e)}")
                   self.logger.error(f"Error processing {filename}: {e}")
           
           return results
       
       def process_document(self, file_path: str) -> Dict:
           """Process a single document"""
           headers = {"Authorization": f"Bearer {self.token}"}
           
           with open(file_path, "rb") as f:
               response = requests.post(
                   f"{self.base_url}/documents/process/",
                   headers=headers,
                   files={"file": f}
               )
           
           return response.json()

   # Usage example
   if __name__ == "__main__":
       processor = DocumentProcessor(
           base_url="http://localhost:8000/api/v1",
           username="admin",
           password="adminpassword"
       )
       
       results = processor.process_workflow(
           input_dir="/path/to/input/documents",
           output_dir="/path/to/output/results"
       )
       
       print(f"Processing complete: {results['processed']} succeeded, {results['failed']} failed")
       print(f"Document types: {results['by_type']}")

This complete example demonstrates:

- Authentication handling
- Error management
- Batch processing
- Result storage
- Statistics tracking
- Logging integration

For more advanced use cases and integration patterns, see the API reference documentation.