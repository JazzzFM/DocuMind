Quick Start Guide
=================

Get DocuMind up and running in minutes with this quick start guide.

1. Installation
---------------

**Using Docker (Recommended):**

.. code-block:: bash

   # Clone and start
   git clone https://github.com/yourusername/documind.git
   cd documind
   docker-compose -f docker-compose.prod.yml up -d

   # Create admin user
   docker-compose -f docker-compose.prod.yml exec web python manage.py createsuperuser

**Local Installation:**

.. code-block:: bash

   # Setup environment
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt

   # Configure environment
   cp .env.example .env
   # Edit .env with your settings

   # Run migrations and start
   cd documind
   python manage.py migrate
   python manage.py createsuperuser
   python manage.py runserver

2. Get API Token
----------------

First, obtain an authentication token:

.. code-block:: bash

   curl -X POST http://localhost:8000/api/v1/auth/token/ \
     -H "Content-Type: application/json" \
     -d '{
       "username": "your_username",
       "password": "your_password"
     }'

Response:

.. code-block:: json

   {
     "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
     "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
   }

Save the ``access`` token for subsequent requests.

3. Process Your First Document
------------------------------

Upload and process a document:

.. code-block:: bash

   curl -X POST http://localhost:8000/api/v1/documents/process/ \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
     -F "file=@invoice.pdf" \
     -F "extract_entities=true"

Response:

.. code-block:: json

   {
     "status": "success",
     "document_id": "invoice.pdf",
     "document_type": "invoice",
     "confidence": 0.95,
     "extracted_entities": {
       "invoice_number": "INV-2024-001",
       "amount": "$1,234.56",
       "date": "2024-01-15",
       "vendor": "Acme Corp"
     },
     "processing_time_ms": 2300
   }

4. Search Documents
-------------------

Search for processed documents:

.. code-block:: bash

   curl -X GET "http://localhost:8000/api/v1/documents/search/?query=invoice%20acme&limit=10" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

Response:

.. code-block:: json

   {
     "status": "success",
     "total_results": 5,
     "results": [
       {
         "document_id": "invoice.pdf",
         "document_type": "invoice",
         "similarity": 0.89,
         "extracted_entities": {
           "vendor": "Acme Corp",
           "amount": "$1,234.56"
         }
       }
     ]
   }

5. Check System Status
----------------------

Monitor system health:

.. code-block:: bash

   curl -X GET http://localhost:8000/api/v1/system/status/ \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

Response:

.. code-block:: json

   {
     "status": "healthy",
     "components": {
       "ocr": {"status": "healthy", "engine": "TesseractEngine"},
       "llm": {"status": "healthy", "provider": "openai"},
       "vector_search": {"status": "healthy", "collection_count": 150},
       "cache": {"status": "healthy"}
     }
   }

6. Interactive API Documentation
--------------------------------

Explore the complete API using the interactive documentation:

* **Swagger UI**: http://localhost:8000/api/schema/swagger-ui/
* **ReDoc**: http://localhost:8000/api/schema/redoc/

The interactive docs allow you to:

* Browse all available endpoints
* Test API calls directly in the browser
* View detailed request/response schemas
* Understand authentication requirements

7. Python Client Example
-------------------------

Here's a complete Python example:

.. code-block:: python

   import requests
   import json

   # Configuration
   BASE_URL = "http://localhost:8000/api/v1"
   USERNAME = "your_username"
   PASSWORD = "your_password"

   # Get authentication token
   auth_response = requests.post(
       f"{BASE_URL}/auth/token/",
       json={"username": USERNAME, "password": PASSWORD}
   )
   token = auth_response.json()["access"]

   # Setup headers
   headers = {"Authorization": f"Bearer {token}"}

   # Process a document
   with open("invoice.pdf", "rb") as f:
       files = {"file": f}
       data = {"extract_entities": "true"}
       
       response = requests.post(
           f"{BASE_URL}/documents/process/",
           headers=headers,
           files=files,
           data=data
       )

   result = response.json()
   print(f"Document Type: {result['document_type']}")
   print(f"Confidence: {result['confidence']}")
   print(f"Entities: {json.dumps(result['extracted_entities'], indent=2)}")

   # Search for documents
   search_response = requests.get(
       f"{BASE_URL}/documents/search/",
       headers=headers,
       params={"query": "invoice acme", "limit": 5}
   )

   search_results = search_response.json()
   print(f"Found {search_results['total_results']} documents")

8. Supported Document Types
---------------------------

DocuMind supports 9 document types out of the box:

* **invoice**: Bills, invoices, payment requests
* **contract**: Legal agreements, contracts, terms
* **form**: Applications, questionnaires, forms
* **report**: Business reports, analyses, summaries
* **assignment**: Academic assignments, homework
* **advertisement**: Marketing materials, ads, promotions
* **budget**: Financial budgets, cost planning
* **email**: Email communications, correspondence
* **file_folder**: File organization, directory listings

9. Batch Processing
-------------------

Process multiple documents at once:

.. code-block:: bash

   curl -X POST http://localhost:8000/api/v1/documents/batch/ \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
     -F "files=@doc1.pdf" \
     -F "files=@doc2.png" \
     -F "files=@doc3.jpg" \
     -F "async=false"

10. Next Steps
--------------

Now that you have DocuMind running:

1. **Explore the API**: Use the interactive documentation to test different endpoints
2. **Add Document Types**: Customize ``config/document_types.yaml`` for your use case
3. **Configure LLM**: Optimize prompts in ``config/prompts/`` for better extraction
4. **Scale Up**: Deploy with Kubernetes for production workloads
5. **Monitor Performance**: Use the statistics endpoint to track system performance

Common Use Cases
----------------

**Document Management System:**

.. code-block:: python

   # Process and categorize incoming documents
   for file_path in document_queue:
       result = process_document(file_path)
       store_in_database(result['document_type'], result['extracted_entities'])

**Invoice Processing:**

.. code-block:: python

   # Extract invoice data for accounting
   invoice_data = process_document("invoice.pdf")
   accounting_system.create_bill(
       vendor=invoice_data['entities']['vendor'],
       amount=invoice_data['entities']['amount'],
       due_date=invoice_data['entities']['due_date']
   )

**Contract Analysis:**

.. code-block:: python

   # Analyze contract terms
   contract_data = process_document("contract.pdf")
   legal_system.track_obligations(
       parties=contract_data['entities']['parties'],
       terms=contract_data['entities']['key_terms'],
       expiry=contract_data['entities']['expiry_date']
   )

Troubleshooting
---------------

**Common Issues:**

1. **"Token expired"**: Refresh your token using the refresh endpoint
2. **"Unsupported file type"**: Ensure you're uploading PDF, PNG, JPG, or JPEG files
3. **"OCR processing failed"**: Check if Tesseract is properly installed
4. **"LLM extraction failed"**: Verify your OpenAI API key is correct

**Getting Help:**

* Check system status: ``GET /api/v1/system/status/``
* View logs: ``docker-compose logs`` or Django debug output
* Refer to the full documentation for detailed troubleshooting

You're now ready to start processing documents with DocuMind! 🚀