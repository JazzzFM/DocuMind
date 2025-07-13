OCR Module
==========

The OCR (Optical Character Recognition) module provides a pluggable architecture for text extraction from documents.

Base Classes
------------

.. automodule:: documents.ocr.base
   :members:
   :undoc-members:
   :show-inheritance:

Factory
-------

.. automodule:: documents.ocr.factory
   :members:
   :undoc-members:
   :show-inheritance:

Tesseract Engine
----------------

.. automodule:: documents.ocr.tesseract_engine
   :members:
   :undoc-members:
   :show-inheritance:

Google Vision Engine
--------------------

.. automodule:: documents.ocr.google_vision_engine
   :members:
   :undoc-members:
   :show-inheritance:

Azure Engine
------------

.. automodule:: documents.ocr.azure_engine
   :members:
   :undoc-members:
   :show-inheritance:

Usage Example
-------------

.. code-block:: python

   from documents.ocr.factory import OCRFactory
   
   # Get the configured OCR engine
   ocr_engine = OCRFactory.get_engine()
   
   # Extract text from a document
   text = ocr_engine.extract_text('/path/to/document.pdf')
   print(f"Extracted text: {text}")

Configuration
-------------

OCR engines are configured via environment variables:

.. code-block:: bash

   # Use Tesseract (default)
   OCR_ENGINE=tesseract
   
   # Use Google Vision
   OCR_ENGINE=google_vision
   GOOGLE_VISION_API_KEY=your_api_key
   
   # Use Azure Form Recognizer
   OCR_ENGINE=azure_form_recognizer
   AZURE_FORM_RECOGNIZER_KEY=your_key
   AZURE_FORM_RECOGNIZER_ENDPOINT=your_endpoint