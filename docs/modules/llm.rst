LLM Module
==========

The LLM (Large Language Model) module provides a pluggable architecture for integrating various LLM providers.

Base Provider
-------------

.. automodule:: documents.llm.base
   :members:
   :undoc-members:
   :show-inheritance:

Factory
-------

.. automodule:: documents.llm.factory
   :members:
   :undoc-members:
   :show-inheritance:

OpenAI Provider
---------------

.. automodule:: documents.llm.openai_provider
   :members:
   :undoc-members:
   :show-inheritance:

Usage Example
-------------

.. code-block:: python

   from documents.llm.factory import LLMFactory
   from documents.llm.base import LLMRequest
   
   # Get the configured LLM provider
   factory = LLMFactory()
   provider = factory.get_provider()
   
   # Create a request
   request = LLMRequest(
       prompt="Extract entities from this invoice: ...",
       max_tokens=1000,
       temperature=0.1,
       metadata={"document_type": "invoice"}
   )
   
   # Get response
   response = provider.extract_entities(request)
   
   if response.success:
       print(f"Extracted entities: {response.content}")
       print(f"Usage: {response.usage_stats}")
   else:
       print(f"Error: {response.error_message}")

Provider Configuration
----------------------

LLM providers are configured via environment variables:

OpenAI Configuration
~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   LLM_PROVIDER=openai
   OPENAI_API_KEY=your_api_key_here
   LLM_MODEL=gpt-4-turbo-preview
   LLM_TEMPERATURE=0.1

Request Structure
-----------------

LLM requests are structured using the ``LLMRequest`` dataclass:

.. code-block:: python

   @dataclass
   class LLMRequest:
       prompt: str
       max_tokens: int = 1000
       temperature: float = 0.1
       metadata: Optional[Dict[str, Any]] = None

Response Structure
------------------

LLM responses are structured using the ``LLMResponse`` dataclass:

.. code-block:: python

   @dataclass
   class LLMResponse:
       content: str
       success: bool = True
       error_message: Optional[str] = None
       usage_stats: Optional[Dict[str, Any]] = None
       processing_time: float = 0.0
       metadata: Optional[Dict[str, Any]] = None

Error Handling
--------------

The LLM module implements comprehensive error handling:

* **Rate Limiting**: Automatic retry with exponential backoff
* **Network Errors**: Connection timeout and retry logic
* **API Errors**: Proper error parsing and user-friendly messages
* **Validation Errors**: Input validation before API calls

Rate Limiting and Retries
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # OpenAI provider implements rate limiting
   provider = OpenAIProvider()
   
   # Automatic retries with exponential backoff
   response = provider.extract_entities(request)
   
   # Rate limit handling is transparent to the user

Performance Monitoring
----------------------

The LLM module tracks various performance metrics:

* **Response Times**: Average and percentile response times
* **Success Rates**: Successful vs failed requests
* **Token Usage**: Input and output token consumption
* **Error Rates**: Breakdown of error types
* **Cache Performance**: Cache hit rates and effectiveness

Usage Statistics Example
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Get provider statistics
   stats = provider.get_usage_statistics()
   
   print(f"Total requests: {stats['total_requests']}")
   print(f"Success rate: {stats['success_rate']:.2%}")
   print(f"Average response time: {stats['avg_response_time']:.2f}s")
   print(f"Total tokens used: {stats['total_tokens']}")

Adding New Providers
--------------------

To add a new LLM provider:

1. **Create Provider Class**: Inherit from ``BaseLLMProvider``
2. **Implement Methods**: Implement required abstract methods
3. **Register Provider**: Add to the LLM factory
4. **Add Configuration**: Add environment variables

Example Custom Provider
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from documents.llm.base import BaseLLMProvider, LLMRequest, LLMResponse
   
   class CustomLLMProvider(BaseLLMProvider):
       def __init__(self):
           super().__init__()
           self.api_key = os.getenv('CUSTOM_API_KEY')
           self.base_url = os.getenv('CUSTOM_BASE_URL')
       
       def extract_entities(self, request: LLMRequest) -> LLMResponse:
           # Implement custom LLM integration
           try:
               # Make API call to custom LLM
               response_data = self._make_api_call(request)
               
               return LLMResponse(
                   content=response_data['text'],
                   success=True,
                   usage_stats=response_data['usage']
               )
           except Exception as e:
               return LLMResponse(
                   content="",
                   success=False,
                   error_message=str(e)
               )
       
       def get_provider_name(self) -> str:
           return "custom_llm"
       
       def test_connection(self) -> bool:
           # Test provider connectivity
           return True

Caching
-------

The LLM module supports response caching to improve performance and reduce costs:

* **Redis Backend**: Uses Redis for distributed caching
* **TTL Configuration**: Configurable cache expiration
* **Cache Keys**: Based on prompt hash and model parameters
* **Cache Invalidation**: Automatic cleanup of stale entries

Cache Configuration
~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Cache settings
   LLM_CACHE_TIMEOUT=3600  # 1 hour
   REDIS_URL=redis://localhost:6379/1