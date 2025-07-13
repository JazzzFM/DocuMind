Architecture
============

DocuMind is built with a modular, microservices-ready architecture that separates concerns and enables scalability.

System Overview
---------------

DocuMind follows a layered architecture pattern with clear separation between:

- **API Layer**: REST API endpoints using Django REST Framework
- **Processing Layer**: Document processing pipeline with OCR, classification, and extraction
- **Storage Layer**: Vector database (ChromaDB) and relational database (PostgreSQL)
- **Integration Layer**: External services (LLM providers, caching)

.. code-block:: text

   ┌─────────────────────────────────────────────────────────────┐
   │                        API Layer                            │
   │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
   │  │ Auth API    │  │ Document    │  │ System Management   │  │
   │  │ (JWT)       │  │ Processing  │  │ API                 │  │
   │  └─────────────┘  └─────────────┘  └─────────────────────┘  │
   └─────────────────────────────────────────────────────────────┘
   ┌─────────────────────────────────────────────────────────────┐
   │                    Processing Layer                         │
   │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
   │  │ OCR Engine  │  │ Document    │  │ Entity Extraction   │  │
   │  │ (Tesseract) │  │ Classifier  │  │ (LLM)               │  │
   │  └─────────────┘  └─────────────┘  └─────────────────────┘  │
   └─────────────────────────────────────────────────────────────┘
   ┌─────────────────────────────────────────────────────────────┐
   │                     Storage Layer                           │
   │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
   │  │ PostgreSQL  │  │ ChromaDB    │  │ Redis Cache         │  │
   │  │ (Metadata)  │  │ (Vectors)   │  │ (Sessions/Cache)    │  │
   │  └─────────────┘  └─────────────┘  └─────────────────────┘  │
   └─────────────────────────────────────────────────────────────┘

Core Components
---------------

Document Processing Pipeline
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The document processing pipeline is the heart of DocuMind:

.. code-block:: python

   class DocumentProcessor:
       def __init__(self):
           self.ocr_engine = OCRFactory().get_engine()
           self.classifier = HybridClassifier()
           self.extractor = get_llm_extractor()
           self.validator = EntityValidator()
       
       def process_document(self, file_content, filename):
           # 1. Extract text via OCR
           text = self.ocr_engine.extract_text(file_content)
           
           # 2. Classify document type
           doc_type, confidence = self.classifier.classify(text)
           
           # 3. Extract entities using LLM
           entities = self.extractor.extract_entities(doc_type, text)
           
           # 4. Validate extracted entities
           validated_entities = self.validator.validate_all(entities, doc_type)
           
           return {
               'document_type': doc_type,
               'confidence': confidence,
               'extracted_entities': validated_entities,
               'raw_text': text
           }

Factory Pattern Implementation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

DocuMind uses the Factory pattern for pluggable components:

**OCR Factory:**

.. code-block:: python

   class OCRFactory:
       @staticmethod
       def get_engine(engine_type: str = None) -> BaseOCREngine:
           engine_type = engine_type or settings.OCR_ENGINE
           
           if engine_type == 'tesseract':
               return TesseractEngine()
           elif engine_type == 'aws_textract':
               return AWSTextractEngine()
           else:
               raise ValueError(f"Unknown OCR engine: {engine_type}")

**LLM Factory:**

.. code-block:: python

   class LLMFactory:
       @staticmethod
       def get_provider(provider_type: str = None) -> BaseLLMProvider:
           provider_type = provider_type or settings.LLM_PROVIDER
           
           if provider_type == 'openai':
               return OpenAIProvider()
           elif provider_type == 'azure_openai':
               return AzureOpenAIProvider()
           else:
               raise ValueError(f"Unknown LLM provider: {provider_type}")

Data Flow Architecture
----------------------

Document Upload Flow
~~~~~~~~~~~~~~~~~~~~

.. code-block:: mermaid

   sequenceDiagram
       participant C as Client
       participant A as API
       participant P as Processor
       participant O as OCR
       participant CL as Classifier
       participant E as Extractor
       participant V as Validator
       participant DB as Database
       
       C->>A: POST /documents/process/
       A->>P: process_document()
       P->>O: extract_text()
       O-->>P: raw_text
       P->>CL: classify(text)
       CL-->>P: document_type, confidence
       P->>E: extract_entities()
       E-->>P: raw_entities
       P->>V: validate_entities()
       V-->>P: validated_entities
       P->>DB: store_results()
       P-->>A: processing_result
       A-->>C: JSON response

Search Flow
~~~~~~~~~~~

.. code-block:: mermaid

   sequenceDiagram
       participant C as Client
       participant A as API
       participant S as Search Engine
       participant V as Vector DB
       participant R as Relational DB
       
       C->>A: GET /documents/search/
       A->>S: search(query)
       S->>V: similarity_search()
       V-->>S: similar_documents
       S->>R: get_metadata()
       R-->>S: document_metadata
       S-->>A: search_results
       A-->>C: JSON response

Storage Architecture
--------------------

Multi-Database Strategy
~~~~~~~~~~~~~~~~~~~~~~~

DocuMind uses multiple storage systems optimized for different data types:

**PostgreSQL (Relational Data):**
- User authentication and sessions
- Document metadata and processing history
- System configuration and audit logs
- Structured relationships between entities

**ChromaDB (Vector Data):**
- Document embeddings for similarity search
- Semantic search capabilities
- High-dimensional vector storage
- Fast similarity queries

**Redis (Cache):**
- Session storage
- Processing result caching
- Rate limiting counters
- Temporary data storage

Database Schema
~~~~~~~~~~~~~~~

**PostgreSQL Tables:**

.. code-block:: sql

   -- Users and authentication
   CREATE TABLE auth_user (
       id SERIAL PRIMARY KEY,
       username VARCHAR(150) UNIQUE NOT NULL,
       email VARCHAR(254),
       date_joined TIMESTAMP DEFAULT NOW()
   );
   
   -- Document processing history
   CREATE TABLE documents_processing_log (
       id SERIAL PRIMARY KEY,
       user_id INTEGER REFERENCES auth_user(id),
       filename VARCHAR(255) NOT NULL,
       document_type VARCHAR(50),
       confidence DECIMAL(5,4),
       processing_time_ms INTEGER,
       created_at TIMESTAMP DEFAULT NOW()
   );
   
   -- Extracted entities
   CREATE TABLE documents_extracted_entity (
       id SERIAL PRIMARY KEY,
       processing_log_id INTEGER REFERENCES documents_processing_log(id),
       entity_name VARCHAR(100) NOT NULL,
       entity_value TEXT,
       entity_type VARCHAR(50),
       confidence DECIMAL(5,4),
       is_valid BOOLEAN DEFAULT TRUE
   );

**ChromaDB Collections:**

.. code-block:: python

   # Document embeddings collection
   collection = chroma_client.create_collection(
       name="documents",
       metadata={"description": "Document text embeddings"}
   )
   
   # Store document embedding
   collection.add(
       documents=[document_text],
       metadatas=[{
           "document_id": doc_id,
           "document_type": doc_type,
           "filename": filename,
           "processed_at": timestamp
       }],
       ids=[doc_id]
   )

Scalability Architecture
------------------------

Horizontal Scaling
~~~~~~~~~~~~~~~~~~

DocuMind is designed for horizontal scaling:

**API Layer Scaling:**
- Stateless Django applications
- Load balancer distribution
- Auto-scaling based on CPU/memory usage

**Processing Layer Scaling:**
- Asynchronous task processing with Celery
- Distributed task queues
- Worker node auto-scaling

**Storage Layer Scaling:**
- PostgreSQL read replicas
- ChromaDB distributed deployment
- Redis clustering

Kubernetes Deployment
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   # API Deployment
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: documind-api
   spec:
     replicas: 3
     selector:
       matchLabels:
         app: documind-api
     template:
       spec:
         containers:
         - name: api
           image: documind:latest
           resources:
             requests:
               memory: "512Mi"
               cpu: "250m"
             limits:
               memory: "1Gi"
               cpu: "500m"

Performance Optimization
------------------------

Caching Strategy
~~~~~~~~~~~~~~~~

Multi-level caching for optimal performance:

**Level 1 - Application Cache:**
- In-memory caching of configuration
- Frequently accessed document types
- User session data

**Level 2 - Redis Cache:**
- OCR processing results
- Classification outcomes
- LLM extraction responses

**Level 3 - Database Query Cache:**
- PostgreSQL query result caching
- ChromaDB search result caching

Processing Optimization
~~~~~~~~~~~~~~~~~~~~~~~

**Asynchronous Processing:**

.. code-block:: python

   from celery import shared_task
   
   @shared_task
   def process_document_async(file_path, user_id):
       """Asynchronous document processing"""
       processor = DocumentProcessor()
       result = processor.process_document(file_path)
       
       # Store results
       ProcessingLog.objects.create(
           user_id=user_id,
           filename=file_path,
           document_type=result['document_type'],
           confidence=result['confidence']
       )
       
       return result

**Batch Processing:**

.. code-block:: python

   def process_documents_batch(file_list, batch_size=10):
       """Process documents in batches"""
       for i in range(0, len(file_list), batch_size):
           batch = file_list[i:i + batch_size]
           
           # Process batch in parallel
           with ThreadPoolExecutor(max_workers=batch_size) as executor:
               futures = [
                   executor.submit(process_document, file) 
                   for file in batch
               ]
               
               for future in as_completed(futures):
                   result = future.result()
                   yield result

Security Architecture
---------------------

Authentication & Authorization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**JWT-based Authentication:**
- Stateless token authentication
- Role-based access control
- Token refresh mechanism
- Secure token storage

**API Security:**
- Rate limiting per user/IP
- Input validation and sanitization
- CORS configuration
- HTTPS enforcement

Data Security
~~~~~~~~~~~~~

**Encryption:**
- Database encryption at rest
- TLS encryption in transit
- Secure file storage
- Encrypted backup systems

**Privacy:**
- Data anonymization options
- GDPR compliance features
- User data deletion
- Audit logging

Monitoring and Observability
----------------------------

Application Monitoring
~~~~~~~~~~~~~~~~~~~~~~

**Health Checks:**

.. code-block:: python

   def health_check():
       """System health check"""
       components = {
           'database': check_database_connection(),
           'redis': check_redis_connection(),
           'chromadb': check_vector_db_connection(),
           'llm_provider': check_llm_provider(),
           'ocr_engine': check_ocr_engine()
       }
       
       overall_status = 'healthy' if all(
           status['status'] == 'healthy' 
           for status in components.values()
       ) else 'unhealthy'
       
       return {
           'status': overall_status,
           'components': components,
           'timestamp': datetime.utcnow().isoformat()
       }

**Performance Metrics:**

.. code-block:: python

   class PerformanceTracker:
       def track_processing_time(self, operation, duration):
           """Track operation performance"""
           metrics.histogram(
               f'documind.processing.{operation}.duration',
               duration,
               tags={'operation': operation}
           )
       
       def track_success_rate(self, operation, success):
           """Track operation success rates"""
           metrics.increment(
               f'documind.processing.{operation}.count',
               tags={'operation': operation, 'success': success}
           )

Deployment Architecture
-----------------------

Production Deployment
~~~~~~~~~~~~~~~~~~~~~

**Container Orchestration:**

.. code-block:: yaml

   # docker-compose.prod.yml
   version: '3.8'
   services:
     web:
       image: documind-api:latest
       deploy:
         replicas: 3
         resources:
           limits:
             memory: 1G
             cpus: '0.5'
       environment:
         - DATABASE_URL=postgresql://user:pass@db:5432/documind
         - REDIS_URL=redis://redis:6379
   
     db:
       image: postgres:15
       volumes:
         - postgres_data:/var/lib/postgresql/data
       environment:
         - POSTGRES_DB=documind
         - POSTGRES_USER=documind
         - POSTGRES_PASSWORD=secure_password
   
     redis:
       image: redis:7-alpine
       volumes:
         - redis_data:/data
   
     nginx:
       image: nginx:alpine
       ports:
         - "80:80"
         - "443:443"
       volumes:
         - ./nginx.conf:/etc/nginx/nginx.conf

High Availability Setup
~~~~~~~~~~~~~~~~~~~~~~~

**Load Balancing:**
- Nginx reverse proxy
- Health check endpoints
- Automatic failover
- Session persistence

**Database High Availability:**
- PostgreSQL streaming replication
- Automatic backup systems
- Point-in-time recovery
- Connection pooling

**Disaster Recovery:**
- Multi-region deployment
- Automated backups
- Database replication
- Configuration backup

Development Architecture
------------------------

Local Development
~~~~~~~~~~~~~~~~~

**Docker Development Environment:**

.. code-block:: yaml

   # docker-compose.dev.yml
   version: '3.8'
   services:
     web:
       build: .
       volumes:
         - .:/app
       ports:
         - "8000:8000"
       environment:
         - DEBUG=True
         - DATABASE_URL=sqlite:///db.sqlite3
       command: python manage.py runserver 0.0.0.0:8000

**Testing Architecture:**
- Isolated test databases
- Mock external services
- Comprehensive test coverage
- CI/CD integration

This architecture provides a solid foundation for scaling DocuMind from a single-node deployment to a distributed, enterprise-grade system while maintaining performance, security, and reliability.