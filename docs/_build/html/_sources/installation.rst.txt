Installation
============

This guide provides detailed instructions for installing and setting up DocuMind in different environments.

Quick Start with Docker
------------------------

The fastest way to get DocuMind running is using Docker:

.. code-block:: bash

   # Clone the repository
   git clone https://github.com/yourusername/documind.git
   cd documind

   # Build and start services
   docker-compose -f docker-compose.prod.yml build
   docker-compose -f docker-compose.prod.yml up -d

   # Run migrations
   docker-compose -f docker-compose.prod.yml exec web python manage.py migrate

   # Create superuser
   docker-compose -f docker-compose.prod.yml exec web python manage.py createsuperuser

The API will be available at ``http://localhost:8000``.

Local Development Setup
-----------------------

For local development without Docker:

Prerequisites
~~~~~~~~~~~~~

Before installing DocuMind, ensure you have:

* **Python 3.9+**: `Download Python <https://www.python.org/downloads/>`_
* **PostgreSQL 12+**: `Download PostgreSQL <https://www.postgresql.org/download/>`_ (optional, SQLite used by default)
* **Redis 6+**: `Download Redis <https://redis.io/download>`_
* **Tesseract OCR**: Required for text extraction

System Dependencies
~~~~~~~~~~~~~~~~~~~

**Ubuntu/Debian:**

.. code-block:: bash

   sudo apt-get update
   sudo apt-get install -y \
       tesseract-ocr \
       tesseract-ocr-eng \
       tesseract-ocr-spa \
       poppler-utils \
       redis-server \
       postgresql-client

**macOS (with Homebrew):**

.. code-block:: bash

   brew install tesseract poppler redis postgresql

**Windows:**

Download and install:

* `Tesseract OCR <https://github.com/UB-Mannheim/tesseract/wiki>`_
* `Redis for Windows <https://github.com/microsoftarchive/redis/releases>`_
* `PostgreSQL <https://www.postgresql.org/download/windows/>`_
* `Poppler for Windows <https://github.com/oschwartz10612/poppler-windows/releases>`_

Python Environment
~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Create virtual environment
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate

   # Install dependencies
   pip install -r requirements.txt

Environment Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~

Copy the example environment file and configure it:

.. code-block:: bash

   cp .env.example .env

Edit ``.env`` with your settings:

.. code-block:: bash

   # Core Django Settings
   SECRET_KEY=your-secret-key-here
   DEBUG=True
   ALLOWED_HOSTS=localhost,127.0.0.1

   # Database (SQLite for development)
   DATABASE_URL=sqlite:///db.sqlite3

   # Redis
   REDIS_URL=redis://127.0.0.1:6379/1

   # LLM Configuration
   LLM_PROVIDER=openai
   OPENAI_API_KEY=your-openai-api-key
   LLM_MODEL=gpt-4-turbo-preview

   # ChromaDB
   CHROMA_PERSIST_DIRECTORY=./chroma_db
   CHROMA_COLLECTION_NAME=documents

Database Setup
~~~~~~~~~~~~~~

.. code-block:: bash

   # Navigate to Django project directory
   cd documind

   # Run migrations
   python manage.py migrate

   # Create superuser
   python manage.py createsuperuser

   # Start development server
   python manage.py runserver

Production Installation
-----------------------

For production deployment:

Environment Variables
~~~~~~~~~~~~~~~~~~~~~

Configure production environment variables:

.. code-block:: bash

   # Security
   SECRET_KEY=production-secret-key
   DEBUG=False
   ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

   # Database
   DATABASE_URL=postgresql://user:password@localhost:5432/documind_prod

   # CORS
   CORS_ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

   # Logging
   LOG_LEVEL=INFO

Database Configuration
~~~~~~~~~~~~~~~~~~~~~~

For production, use PostgreSQL:

.. code-block:: bash

   # Create database
   createdb documind_prod

   # Run migrations
   python manage.py migrate

   # Collect static files
   python manage.py collectstatic

Web Server Configuration
~~~~~~~~~~~~~~~~~~~~~~~~

Use a production WSGI server like Gunicorn:

.. code-block:: bash

   # Install Gunicorn
   pip install gunicorn

   # Run with Gunicorn
   gunicorn documind.wsgi:application \
     --bind 0.0.0.0:8000 \
     --workers 4 \
     --worker-class gevent \
     --worker-connections 1000

Reverse Proxy
~~~~~~~~~~~~~

Configure Nginx as a reverse proxy:

.. code-block:: nginx

   server {
       listen 80;
       server_name yourdomain.com;

       location / {
           proxy_pass http://127.0.0.1:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }

       location /static/ {
           alias /path/to/documind/static/;
       }
   }

Kubernetes Deployment
----------------------

For Kubernetes deployment:

.. code-block:: bash

   # Create namespace
   kubectl create namespace documind

   # Create secrets
   kubectl create secret generic documind-secrets \
     --from-literal=SECRET_KEY=your-secret-key \
     --from-literal=OPENAI_API_KEY=your-openai-key \
     -n documind

   # Apply manifests
   kubectl apply -f k8s/ -n documind

   # Scale deployment
   kubectl scale deployment documind-api --replicas=3 -n documind

Verification
------------

After installation, verify the setup:

.. code-block:: bash

   # Test API health
   curl http://localhost:8000/api/v1/system/status/

   # Get authentication token
   curl -X POST http://localhost:8000/api/v1/auth/token/ \
     -H "Content-Type: application/json" \
     -d '{"username": "admin", "password": "your-password"}'

   # Test document processing (with valid token)
   curl -X POST http://localhost:8000/api/v1/documents/process/ \
     -H "Authorization: Bearer your-token" \
     -F "file=@test-document.pdf"

Troubleshooting
---------------

Common Issues
~~~~~~~~~~~~~

**Tesseract not found:**

.. code-block:: bash

   # Ubuntu/Debian
   sudo apt-get install tesseract-ocr

   # macOS
   brew install tesseract

   # Verify installation
   tesseract --version

**Redis connection failed:**

.. code-block:: bash

   # Start Redis service
   redis-server

   # Test connection
   redis-cli ping

**Database migration errors:**

.. code-block:: bash

   # Reset migrations (development only)
   python manage.py migrate --fake-initial

   # Check migration status
   python manage.py showmigrations

**ChromaDB permission errors:**

.. code-block:: bash

   # Ensure directory is writable
   chmod 755 chroma_db/

   # Check ChromaDB connection
   python -c "import chromadb; print('ChromaDB OK')"

**OpenAI API errors:**

.. code-block:: bash

   # Verify API key
   export OPENAI_API_KEY=your-key
   python -c "import openai; print(openai.Model.list())"

Support
-------

If you encounter issues:

1. Check the logs: ``docker-compose logs`` or ``python manage.py runserver --verbosity=2``
2. Verify environment variables are set correctly
3. Ensure all dependencies are installed
4. Check system requirements are met
5. Refer to the troubleshooting section above

For additional help:

* 📧 Email: support@documind.ai
* 🐛 Issues: `GitHub Issues <https://github.com/yourusername/documind/issues>`_
* 📚 Documentation: Full documentation available at the project repository