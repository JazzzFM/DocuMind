API Reference
=============

DocuMind provides a comprehensive REST API for document processing, search, and management.

Base URL
--------

.. code-block:: text

   http://localhost:8000/api/v1/

Authentication
--------------

All API endpoints require JWT authentication. Include the access token in the Authorization header:

.. code-block:: text

   Authorization: Bearer <your_access_token>

Authentication Endpoints
------------------------

Token Generation
~~~~~~~~~~~~~~~~

**POST** ``/auth/token/``

Generate JWT access and refresh tokens.

**Request Body:**

.. code-block:: json

   {
       "username": "your_username",
       "password": "your_password"
   }

**Response:**

.. code-block:: json

   {
       "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
       "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
   }

Token Refresh
~~~~~~~~~~~~~

**POST** ``/auth/token/refresh/``

Refresh an access token using a refresh token.

**Request Body:**

.. code-block:: json

   {
       "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
   }

**Response:**

.. code-block:: json

   {
       "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
   }

Document Processing Endpoints
-----------------------------

Single Document Processing
~~~~~~~~~~~~~~~~~~~~~~~~~~~

**POST** ``/documents/process/``

Process a single document through the complete pipeline.

**Request Parameters:**

* ``file`` (required): Document file (PDF, PNG, JPG, JPEG)
* ``extract_entities`` (optional): Whether to extract entities (default: true)
* ``force_ocr`` (optional): Force OCR even if cached (default: false)
* ``language`` (optional): OCR language hint (default: "eng")

**Response:**

.. code-block:: json

   {
       "status": "success",
       "document_id": "doc_12345",
       "document_type": "invoice",
       "confidence": 0.95,
       "extracted_entities": {
           "invoice_number": "INV-2024-001",
           "amount": "$1,234.56",
           "date": "2024-01-15"
       },
       "processing_time_ms": 2300,
       "ocr_confidence": 0.98
   }

Document Search
~~~~~~~~~~~~~~~

**GET** ``/documents/search/``

Search for documents using vector similarity and filters.

**Query Parameters:**

* ``query`` (required): Search query string
* ``document_type`` (optional): Filter by document type
* ``date_from`` (optional): Start date filter (YYYY-MM-DD)
* ``date_to`` (optional): End date filter (YYYY-MM-DD)
* ``limit`` (optional): Results per page (default: 20)
* ``offset`` (optional): Pagination offset (default: 0)

**Response:**

.. code-block:: json

   {
       "status": "success",
       "total_results": 150,
       "results": [
           {
               "document_id": "doc_12345",
               "document_type": "invoice",
               "similarity": 0.89,
               "extracted_entities": {...}
           }
       ]
   }

Batch Processing
~~~~~~~~~~~~~~~~

**POST** ``/documents/batch/``

Process multiple documents in batch.

**Request Parameters:**

* ``files`` (required): Array of document files
* ``async`` (optional): Process asynchronously (default: true)

**Response (Async):**

.. code-block:: json

   {
       "status": "processing",
       "task_id": "batch_abc-123",
       "message": "Batch processing initiated."
   }

**Response (Sync):**

.. code-block:: json

   {
       "status": "completed",
       "results": [
           {
               "document_id": "doc_1",
               "document_type": "invoice",
               "status": "success"
           }
       ]
   }

System Management Endpoints
----------------------------

System Status
~~~~~~~~~~~~~

**GET** ``/system/status/``

Get health status of all system components.

**Response:**

.. code-block:: json

   {
       "status": "healthy",
       "components": {
           "ocr": {
               "status": "healthy",
               "engine": "TesseractEngine"
           },
           "llm": {
               "status": "healthy",
               "provider": "openai"
           },
           "vector_search": {
               "status": "healthy",
               "collection_count": 1500
           },
           "cache": {
               "status": "healthy"
           }
       }
   }

Document Types
~~~~~~~~~~~~~~

**GET** ``/system/document-types/``

Get available document types and their configurations.

**Response:**

.. code-block:: json

   {
       "status": "success",
       "document_types": {
           "invoice": {
               "name": "Invoice",
               "description": "Invoice documents",
               "entities": [
                   {
                       "name": "invoice_number",
                       "type": "string",
                       "required": true,
                       "description": "Invoice number"
                   }
               ],
               "keywords": ["invoice", "bill", "payment"]
           }
       },
       "total_types": 9
   }

Statistics
~~~~~~~~~~

**GET** ``/system/statistics/``

Get system performance statistics.

**Response:**

.. code-block:: json

   {
       "status": "success",
       "statistics": {
           "classification": {
               "total_classifications": 1500,
               "accuracy": 0.92
           },
           "extraction": {
               "total_extractions": 1200,
               "success_rate": 0.89,
               "cache_hit_rate": 0.65
           },
           "vector_search": {
               "document_count": 1500,
               "collection_size": "50MB"
           }
       }
   }

Error Responses
---------------

All endpoints return consistent error responses:

.. code-block:: json

   {
       "status": "error",
       "code": "ERROR_CODE",
       "message": "Human-readable error message",
       "details": {
           "field": "Additional error details"
       }
   }

Common Error Codes
~~~~~~~~~~~~~~~~~~

* ``INVALID_FILE_TYPE``: Unsupported file format
* ``AUTHENTICATION_FAILED``: Invalid credentials
* ``TOKEN_EXPIRED``: JWT token has expired
* ``OCR_PROCESSING_ERROR``: OCR processing failed
* ``CLASSIFICATION_ERROR``: Document classification failed
* ``EXTRACTION_ERROR``: Entity extraction failed
* ``VALIDATION_ERROR``: Request validation failed

Rate Limiting
-------------

API endpoints are rate limited:

* **Anonymous users**: 100 requests per day
* **Authenticated users**: 1000 requests per day

Rate limit headers are included in responses:

.. code-block:: text

   X-RateLimit-Limit: 1000
   X-RateLimit-Remaining: 999
   X-RateLimit-Reset: 1640995200

Interactive Documentation
--------------------------

DocuMind provides interactive API documentation:

* **Swagger UI**: ``http://localhost:8000/api/schema/swagger-ui/``
* **ReDoc**: ``http://localhost:8000/api/schema/redoc/``
* **OpenAPI Schema**: ``http://localhost:8000/api/schema/``

The interactive documentation allows you to:

* Explore all available endpoints
* Test API calls directly from the browser
* View request/response schemas
* Understand authentication requirements