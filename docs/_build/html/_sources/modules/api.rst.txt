API Module
==========

The API module provides the REST API endpoints for DocuMind using Django REST Framework.

Views
-----

.. automodule:: api.views
   :members:
   :undoc-members:
   :show-inheritance:

Serializers
-----------

.. automodule:: api.serializers
   :members:
   :undoc-members:
   :show-inheritance:

Authentication
--------------

The API uses JWT (JSON Web Token) authentication provided by Django REST Framework SimpleJWT.

Token Generation
~~~~~~~~~~~~~~~~

.. code-block:: python

   from rest_framework_simplejwt.views import TokenObtainPairView
   
   # POST /api/v1/auth/token/
   {
       "username": "your_username", 
       "password": "your_password"
   }

Token Usage
~~~~~~~~~~~

Include the access token in the Authorization header:

.. code-block:: http

   Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

API Endpoints
-------------

Document Processing
~~~~~~~~~~~~~~~~~~~

**POST** ``/api/v1/documents/process/``

Process a single document through the complete pipeline.

**Parameters:**
- ``file`` (file): Document to process (PDF, PNG, JPG, JPEG)
- ``extract_entities`` (boolean): Whether to extract entities (default: true)
- ``force_ocr`` (boolean): Force OCR processing (default: false)
- ``language`` (string): OCR language hint (default: "eng")

**Response:**

.. code-block:: json

   {
       "status": "success",
       "document_id": "document.pdf",
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

**GET** ``/api/v1/documents/search/``

Search documents using vector similarity.

**Query Parameters:**
- ``query`` (string): Search query
- ``document_type`` (string): Filter by document type
- ``date_from`` (date): Start date filter
- ``date_to`` (date): End date filter
- ``limit`` (integer): Results per page (default: 20)
- ``offset`` (integer): Pagination offset (default: 0)

Batch Processing
~~~~~~~~~~~~~~~~

**POST** ``/api/v1/documents/batch/``

Process multiple documents in batch.

**Parameters:**
- ``files`` (array): Array of document files
- ``async`` (boolean): Process asynchronously (default: true)

System Endpoints
~~~~~~~~~~~~~~~~

**GET** ``/api/v1/system/status/``

Get system health status.

**GET** ``/api/v1/system/document-types/``

Get available document types configuration.

**GET** ``/api/v1/system/statistics/``

Get system performance statistics.

Error Handling
--------------

The API returns consistent error responses:

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

- ``INVALID_FILE_TYPE``: Unsupported file format
- ``AUTHENTICATION_FAILED``: Invalid credentials
- ``TOKEN_EXPIRED``: JWT token has expired
- ``OCR_PROCESSING_ERROR``: OCR processing failed
- ``CLASSIFICATION_ERROR``: Document classification failed
- ``EXTRACTION_ERROR``: Entity extraction failed
- ``VALIDATION_ERROR``: Request validation failed

Rate Limiting
-------------

API endpoints implement rate limiting:

- **Anonymous users**: 100 requests per day
- **Authenticated users**: 1000 requests per day

Rate limit information is included in response headers:

.. code-block:: http

   X-RateLimit-Limit: 1000
   X-RateLimit-Remaining: 999
   X-RateLimit-Reset: 1640995200

Response Formats
----------------

All API responses follow a consistent format:

Success Response
~~~~~~~~~~~~~~~~

.. code-block:: json

   {
       "status": "success",
       "data": {
           "key": "value"
       },
       "metadata": {
           "processing_time_ms": 150,
           "cache_hit": false
       }
   }

Error Response
~~~~~~~~~~~~~~

.. code-block:: json

   {
       "status": "error",
       "code": "ERROR_CODE",
       "message": "Descriptive error message",
       "details": {
           "field_errors": {
               "field_name": "Field-specific error"
           }
       }
   }

Interactive Documentation
--------------------------

The API provides interactive documentation through:

- **Swagger UI**: Available at ``/api/schema/swagger-ui/``
- **ReDoc**: Available at ``/api/schema/redoc/``
- **OpenAPI Schema**: Available at ``/api/schema/``

Testing
-------

The API module includes comprehensive tests:

.. code-block:: python

   # Run API tests
   python manage.py test api.tests
   
   # Run with coverage
   coverage run --source='.' manage.py test api.tests
   coverage report

Customization
-------------

To extend the API:

1. **Add New Endpoints**: Create view classes inheriting from DRF views
2. **Custom Serializers**: Define serializers for request/response validation
3. **Authentication**: Implement custom authentication backends
4. **Permissions**: Define custom permission classes
5. **Throttling**: Configure custom rate limiting rules

Example Custom View
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from rest_framework.views import APIView
   from rest_framework.response import Response
   from rest_framework.permissions import IsAuthenticated
   
   class CustomDocumentView(APIView):
       permission_classes = [IsAuthenticated]
       
       def post(self, request):
           # Custom document processing logic
           return Response({
               "status": "success",
               "message": "Custom processing completed"
           })

Configuration
-------------

API configuration is managed through Django settings:

.. code-block:: python

   # API Settings
   REST_FRAMEWORK = {
       'DEFAULT_AUTHENTICATION_CLASSES': [
           'rest_framework_simplejwt.authentication.JWTAuthentication',
       ],
       'DEFAULT_PERMISSION_CLASSES': [
           'rest_framework.permissions.IsAuthenticated',
       ],
       'DEFAULT_THROTTLE_CLASSES': [
           'rest_framework.throttling.AnonRateThrottle',
           'rest_framework.throttling.UserRateThrottle'
       ],
       'DEFAULT_THROTTLE_RATES': {
           'anon': '100/day',
           'user': '1000/day'
       }
   }