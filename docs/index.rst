DocuMind Documentation
======================

.. image:: https://img.shields.io/badge/Python-3.9+-blue.svg
   :alt: Python

.. image:: https://img.shields.io/badge/Django-4.2+-green.svg
   :alt: Django

.. image:: https://img.shields.io/badge/License-MIT-yellow.svg
   :alt: License

**DocuMind** is an AI-powered document classification and entity extraction system that transforms unstructured documents into structured, actionable data using state-of-the-art OCR, vector embeddings, and LLMs.

Key Features
------------

* **Multi-Format OCR**: Processes PDF, PNG, JPG with advanced preprocessing
* **Intelligent Classification**: 90%+ accuracy using hybrid vector + keyword approach
* **Smart Entity Extraction**: LLM-powered extraction with 85%+ precision
* **High Performance**: ≤3 seconds end-to-end processing
* **Modular Architecture**: Extensible design for easy customization
* **Production Ready**: Docker, Kubernetes, comprehensive testing

Quick Start
-----------

.. code-block:: bash

   # Clone the repository
   git clone https://github.com/yourusername/documind.git
   cd documind

   # Start with Docker
   docker-compose -f docker-compose.prod.yml up -d

   # Access the API
   curl -X POST http://localhost:8000/api/v1/auth/token/ \
     -d '{"username": "admin", "password": "password"}'

System Architecture
-------------------

DocuMind follows a modular architecture with clear separation of concerns:

.. code-block:: text

   ┌─────────────────────────────────────────────────────────────┐
   │                        API Layer                            │
   │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
   │  │ Django REST │  │ JWT Auth    │  │ Rate Limiting       │  │
   │  │ Framework   │  │             │  │                     │  │
   │  └─────────────┘  └─────────────┘  └─────────────────────┘  │
   └─────────────────────────────────────────────────────────────┘
                                 │
   ┌─────────────────────────────────────────────────────────────┐
   │                    Processing Pipeline                      │
   │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
   │  │ OCR Engine  │  │ Document    │  │ Entity Extraction   │  │
   │  │ (Tesseract) │  │ Classifier  │  │ (LLM)               │  │
   │  └─────────────┘  └─────────────┘  └─────────────────────┘  │
   └─────────────────────────────────────────────────────────────┘
                                 │
   ┌─────────────────────────────────────────────────────────────┐
   │                     Data Layer                              │
   │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
   │  │ PostgreSQL  │  │ ChromaDB    │  │ Redis Cache         │  │
   │  │ (Metadata)  │  │ (Vectors)   │  │ (Sessions)          │  │
   │  └─────────────┘  └─────────────┘  └─────────────────────┘  │
   └─────────────────────────────────────────────────────────────┘

Table of Contents
-----------------

.. toctree::
   :maxdepth: 2
   :caption: User Guide

   installation
   quickstart
   configuration
   api_reference

.. toctree::
   :maxdepth: 2
   :caption: Developer Guide

   architecture
   modules/index
   contributing
   testing

.. toctree::
   :maxdepth: 2
   :caption: Deployment

   deployment/docker
   deployment/kubernetes
   deployment/monitoring

.. toctree::
   :maxdepth: 1
   :caption: API Reference

   api/authentication
   api/documents
   api/system

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`