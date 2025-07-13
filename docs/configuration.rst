Configuration
=============

DocuMind uses a combination of environment variables, YAML configuration files, and Django settings for configuration.

Environment Variables
----------------------

Core Settings
~~~~~~~~~~~~~

.. code-block:: bash

   # Django Core Settings
   SECRET_KEY=your-secret-key-here
   DEBUG=False
   ALLOWED_HOSTS=localhost,127.0.0.1,yourdomain.com
   
   # Database Configuration
   DATABASE_URL=postgresql://user:password@localhost:5432/documind
   # or for SQLite (development)
   DATABASE_URL=sqlite:///db.sqlite3

Authentication & Security
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # JWT Token Settings
   JWT_ACCESS_TOKEN_LIFETIME=3600  # 1 hour in seconds
   JWT_REFRESH_TOKEN_LIFETIME=86400  # 24 hours in seconds
   
   # CORS Settings
   CORS_ALLOWED_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
   CORS_ALLOW_CREDENTIALS=true

LLM Configuration
~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # LLM Provider Settings
   LLM_PROVIDER=openai
   OPENAI_API_KEY=your-openai-api-key
   LLM_MODEL=gpt-4-turbo-preview
   LLM_TEMPERATURE=0.1
   LLM_MAX_TOKENS=1000
   
   # Alternative: Azure OpenAI
   LLM_PROVIDER=azure_openai
   AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
   AZURE_OPENAI_API_KEY=your-azure-key
   AZURE_OPENAI_API_VERSION=2024-02-15-preview

OCR Configuration
~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # OCR Engine Settings
   OCR_ENGINE=tesseract
   TESSERACT_CMD=/usr/bin/tesseract
   OCR_LANGUAGES=eng,spa,fra
   OCR_DPI=300
   OCR_TIMEOUT_SECONDS=30

Vector Database
~~~~~~~~~~~~~~~

.. code-block:: bash

   # ChromaDB Settings
   CHROMA_PERSIST_DIRECTORY=./chroma_db
   CHROMA_COLLECTION_NAME=documents
   CHROMA_DISTANCE_FUNCTION=cosine
   
   # Sentence Transformers
   EMBEDDING_MODEL=all-MiniLM-L6-v2
   EMBEDDING_CACHE_SIZE=1000

Caching
~~~~~~~

.. code-block:: bash

   # Redis Cache Settings
   REDIS_URL=redis://localhost:6379/1
   CACHE_DEFAULT_TIMEOUT=3600
   
   # Cache Configuration
   ENABLE_OCR_CACHE=true
   ENABLE_CLASSIFICATION_CACHE=true
   ENABLE_EXTRACTION_CACHE=true
   OCR_CACHE_TIMEOUT=3600
   CLASSIFICATION_CACHE_TIMEOUT=1800
   EXTRACTION_CACHE_TIMEOUT=7200

Processing Settings
~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Document Processing
   MAX_FILE_SIZE_MB=50
   SUPPORTED_FILE_TYPES=pdf,png,jpg,jpeg
   MAX_PROCESSING_TIME_SECONDS=300
   
   # Batch Processing
   BATCH_SIZE_LIMIT=10
   ENABLE_ASYNC_PROCESSING=true

Logging
~~~~~~~

.. code-block:: bash

   # Logging Configuration
   LOG_LEVEL=INFO
   LOG_FORMAT=json
   LOG_FILE=/var/log/documind/app.log
   ENABLE_STRUCTURED_LOGGING=true

YAML Configuration Files
------------------------

Document Types Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

File: ``config/document_types.yaml``

This file defines all supported document types and their entity schemas:

.. code-block:: yaml

   invoice:
     entities:
       - name: invoice_number
         type: string
         required: true
         description: "Unique invoice identifier"
         pattern: "^[A-Z0-9-]+$"
       - name: amount
         type: amount
         required: true
         min_value: 0
         description: "Total invoice amount"
       - name: date
         type: date
         required: true
         description: "Invoice date"
       - name: vendor
         type: string
         required: true
         min_length: 2
         max_length: 100
         description: "Vendor name"
       - name: line_items
         type: array
         required: false
         description: "Invoice line items"
       - name: is_paid
         type: boolean
         required: false
         description: "Payment status"
     keywords:
       - invoice
       - bill
       - payment
       - due

   contract:
     entities:
       - name: contract_number
         type: string
         required: true
         description: "Contract identifier"
       - name: parties
         type: array
         required: true
         description: "Contract parties"
       - name: effective_date
         type: date
         required: true
         description: "Contract effective date"
       - name: expiry_date
         type: date
         required: false
         description: "Contract expiry date"
       - name: value
         type: amount
         required: false
         description: "Contract value"
     keywords:
       - contract
       - agreement
       - terms
       - parties

Entity Type Definitions
~~~~~~~~~~~~~~~~~~~~~~~

Each entity type supports different validation parameters:

**String Type:**

.. code-block:: yaml

   - name: entity_name
     type: string
     required: true
     min_length: 1
     max_length: 255
     pattern: "^[A-Za-z0-9\\s-]+$"
     description: "Entity description"

**Date Type:**

.. code-block:: yaml

   - name: date_field
     type: date
     required: true
     min_date: "2020-01-01"
     max_date: "2030-12-31"
     description: "Date field description"

**Amount Type:**

.. code-block:: yaml

   - name: amount_field
     type: amount
     required: true
     min_value: 0
     max_value: 1000000
     description: "Monetary amount"

**Number Type:**

.. code-block:: yaml

   - name: number_field
     type: number
     required: false
     min_value: 1
     max_value: 100
     decimal_places: 2
     description: "Numeric value"

**Array Type:**

.. code-block:: yaml

   - name: array_field
     type: array
     required: false
     min_items: 1
     max_items: 10
     description: "List of items"

**Boolean Type:**

.. code-block:: yaml

   - name: boolean_field
     type: boolean
     required: false
     description: "True/false value"

Prompt Templates
~~~~~~~~~~~~~~~~

Directory: ``config/prompts/``

Contains LLM prompt templates for entity extraction:

**default.txt** (fallback template):

.. code-block:: text

   You are an expert document analyst. Extract the following entities from this document:
   
   {entity_definitions}
   
   Guidelines:
   1. Extract information exactly as written
   2. Use null for missing values
   3. Return only valid JSON
   4. Be precise and accurate
   
   Document text:
   {document_text}
   
   Return ONLY a JSON object with the extracted entities:

**invoice.txt** (specialized for invoices):

.. code-block:: text

   You are an expert at processing invoice documents. Extract the following entities:
   
   {entity_definitions}
   
   Special instructions for invoices:
   - Invoice numbers are typically alphanumeric codes
   - Amounts should include currency symbols
   - Dates should be in YYYY-MM-DD format
   - Vendor names should be complete business names
   
   Document text:
   {document_text}
   
   Return ONLY a JSON object:

Django Settings
---------------

Core Django Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~

File: ``documind/settings.py``

.. code-block:: python

   import os
   from pathlib import Path
   
   # Build paths
   BASE_DIR = Path(__file__).resolve().parent.parent
   
   # Security
   SECRET_KEY = os.getenv('SECRET_KEY')
   DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
   ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost').split(',')
   
   # Database
   DATABASES = {
       'default': {
           'ENGINE': 'django.db.backends.postgresql',
           'NAME': os.getenv('DB_NAME', 'documind'),
           'USER': os.getenv('DB_USER', 'documind'),
           'PASSWORD': os.getenv('DB_PASSWORD'),
           'HOST': os.getenv('DB_HOST', 'localhost'),
           'PORT': os.getenv('DB_PORT', '5432'),
       }
   }

REST Framework Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

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
       },
       'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
       'PAGE_SIZE': 20
   }

JWT Configuration
~~~~~~~~~~~~~~~~~

.. code-block:: python

   from datetime import timedelta
   
   SIMPLE_JWT = {
       'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
       'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
       'ROTATE_REFRESH_TOKENS': True,
       'BLACKLIST_AFTER_ROTATION': True,
       'UPDATE_LAST_LOGIN': True,
       'ALGORITHM': 'HS256',
       'SIGNING_KEY': SECRET_KEY,
       'VERIFYING_KEY': None,
       'AUTH_HEADER_TYPES': ('Bearer',),
   }

Cache Configuration
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   CACHES = {
       'default': {
           'BACKEND': 'django_redis.cache.RedisCache',
           'LOCATION': os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/1'),
           'OPTIONS': {
               'CLIENT_CLASS': 'django_redis.client.DefaultClient',
           }
       }
   }

Custom Settings
~~~~~~~~~~~~~~~

.. code-block:: python

   # DocuMind specific settings
   DOCUMIND_SETTINGS = {
       'DOCUMENT_TYPES_CONFIG': os.path.join(BASE_DIR, 'config', 'document_types.yaml'),
       'PROMPTS_CONFIG_DIR': os.path.join(BASE_DIR, 'config', 'prompts'),
       'MAX_FILE_SIZE': 50 * 1024 * 1024,  # 50MB
       'SUPPORTED_FILE_TYPES': ['pdf', 'png', 'jpg', 'jpeg'],
       'OCR_SETTINGS': {
           'ENGINE': 'tesseract',
           'LANGUAGES': ['eng', 'spa'],
           'DPI': 300,
           'TIMEOUT': 30
       },
       'LLM_SETTINGS': {
           'PROVIDER': os.getenv('LLM_PROVIDER', 'openai'),
           'MODEL': os.getenv('LLM_MODEL', 'gpt-4-turbo-preview'),
           'TEMPERATURE': float(os.getenv('LLM_TEMPERATURE', '0.1')),
           'MAX_TOKENS': int(os.getenv('LLM_MAX_TOKENS', '1000'))
       }
   }

Configuration Validation
-------------------------

DocuMind includes configuration validation to ensure proper setup:

.. code-block:: python

   from documents.config_loader import validate_configuration
   
   def validate_config():
       """Validate DocuMind configuration"""
       try:
           # Validate document types configuration
           validate_configuration()
           print("✓ Configuration is valid")
       except Exception as e:
           print(f"✗ Configuration error: {e}")
           return False
       return True

Environment-Specific Configurations
------------------------------------

Development Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Development settings
   DEBUG=True
   SECRET_KEY=dev-secret-key
   DATABASE_URL=sqlite:///db.sqlite3
   REDIS_URL=redis://localhost:6379/1
   LOG_LEVEL=DEBUG
   ENABLE_PROCESSING_CACHE=False

Production Configuration
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Production settings
   DEBUG=False
   SECRET_KEY=secure-production-key
   DATABASE_URL=postgresql://user:pass@prod-db:5432/documind
   REDIS_URL=redis://prod-redis:6379/1
   LOG_LEVEL=INFO
   ENABLE_PROCESSING_CACHE=True
   ALLOWED_HOSTS=api.yourdomain.com

Testing Configuration
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Test settings
   DEBUG=True
   SECRET_KEY=test-secret-key
   DATABASE_URL=sqlite:///:memory:
   REDIS_URL=redis://localhost:6379/15
   LOG_LEVEL=WARNING
   ENABLE_PROCESSING_CACHE=False

Configuration Best Practices
-----------------------------

1. **Environment Variables**: Use environment variables for sensitive data
2. **Version Control**: Never commit secrets to version control
3. **Documentation**: Document all configuration options
4. **Validation**: Validate configuration on startup
5. **Defaults**: Provide sensible defaults for optional settings
6. **Separation**: Separate configuration by environment

Security Considerations
-----------------------

- Store sensitive values in environment variables
- Use strong secret keys in production
- Enable HTTPS in production environments
- Configure proper CORS settings
- Implement rate limiting
- Use secure database connections
- Regular security updates

Configuration Management Tools
------------------------------

For complex deployments, consider using:

- **Docker Compose**: Environment variable files
- **Kubernetes**: ConfigMaps and Secrets
- **HashiCorp Vault**: Secret management
- **AWS Parameter Store**: Cloud-based configuration
- **Environment-specific .env files**: Local development