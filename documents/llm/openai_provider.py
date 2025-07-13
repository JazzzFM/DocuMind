import os
import time
import logging
from typing import Dict, Any, Optional
from openai import OpenAI
from openai.types.chat import ChatCompletion
from decouple import config
from documents.llm.base import BaseLLMProvider, LLMRequest, LLMResponse
from documents.exceptions import DocumentClassificationError

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseLLMProvider):
    """
    OpenAI LLM provider implementation with enhanced error handling and retry logic.
    """

    def __init__(self, model_name: Optional[str] = None):
        """
        Initialize OpenAI provider.
        
        Args:
            model_name: Optional model name override
        """
        # Initialize base class
        super().__init__("openai", model_name)
        
        # Load configuration
        self.api_key = config('OPENAI_API_KEY', default=None)
        self.model_name = model_name or config('LLM_MODEL', default='gpt-4-turbo-preview')
        self.default_temperature = config('LLM_TEMPERATURE', default=0.1, cast=float)
        self.max_retries = config('LLM_MAX_RETRIES', default=3, cast=int)
        self.retry_delay = config('LLM_RETRY_DELAY', default=1.0, cast=float)
        
        # Initialize client
        try:
            if self.api_key:
                self.client = OpenAI(api_key=self.api_key)
                logger.info(f"OpenAI provider initialized with model: {self.model_name}")
            else:
                self.client = None
                logger.warning("OpenAI API key not provided - provider will not be available")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
            self.client = None

    def get_completion(self, request: LLMRequest) -> LLMResponse:
        """
        Get completion from OpenAI with retry logic and comprehensive error handling.
        
        Args:
            request: LLMRequest containing prompt and parameters
            
        Returns:
            LLMResponse with generated content and metadata
        """
        if not self.is_available():
            return LLMResponse(
                content="",
                usage={},
                model=self.model_name,
                provider=self.provider_name,
                response_time_ms=0.0,
                success=False,
                error_message="OpenAI provider not available or not configured"
            )
        
        start_time = time.time()
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                # Prepare messages
                messages = []
                
                if request.system_message:
                    messages.append({"role": "system", "content": request.system_message})
                
                messages.append({"role": "user", "content": request.prompt})
                
                # Prepare API call parameters
                api_params = {
                    "model": self.model_name,
                    "messages": messages,
                    "max_tokens": request.max_tokens,
                    "temperature": request.temperature,
                }
                
                # Add stop sequences if provided
                if request.stop_sequences:
                    api_params["stop"] = request.stop_sequences
                
                # Add any additional model parameters
                if request.model_params:
                    api_params.update(request.model_params)
                
                # Make API call
                response: ChatCompletion = self.client.chat.completions.create(**api_params)
                
                # Calculate response time
                response_time_ms = (time.time() - start_time) * 1000
                
                # Extract content and usage information
                content = response.choices[0].message.content or ""
                usage = {
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                    "total_tokens": response.usage.total_tokens if response.usage else 0
                }
                
                # Create successful response
                llm_response = LLMResponse(
                    content=content,
                    usage=usage,
                    model=self.model_name,
                    provider=self.provider_name,
                    response_time_ms=response_time_ms,
                    success=True
                )
                
                # Update usage statistics
                self._update_usage_stats(llm_response)
                
                logger.debug(f"OpenAI completion successful (attempt {attempt + 1}): "
                           f"{usage['total_tokens']} tokens, {response_time_ms:.1f}ms")
                
                return llm_response
                
            except Exception as e:
                last_error = e
                logger.warning(f"OpenAI API attempt {attempt + 1} failed: {e}")
                
                # Check if this is a rate limit or temporary error
                if attempt < self.max_retries - 1:
                    if "rate limit" in str(e).lower() or "429" in str(e):
                        # Exponential backoff for rate limits
                        delay = self.retry_delay * (2 ** attempt)
                        logger.info(f"Rate limit detected, retrying in {delay}s")
                        time.sleep(delay)
                    elif "503" in str(e) or "502" in str(e) or "timeout" in str(e).lower():
                        # Server errors - shorter delay
                        time.sleep(self.retry_delay)
                    else:
                        # Other errors - don't retry
                        break
        
        # All retries failed
        response_time_ms = (time.time() - start_time) * 1000
        error_message = f"OpenAI API failed after {self.max_retries} attempts: {last_error}"
        
        logger.error(error_message)
        
        return LLMResponse(
            content="",
            usage={},
            model=self.model_name,
            provider=self.provider_name,
            response_time_ms=response_time_ms,
            success=False,
            error_message=error_message
        )

    def is_available(self) -> bool:
        """
        Check if the OpenAI provider is available and configured properly.
        
        Returns:
            True if provider is ready to use
        """
        if not self.api_key or not self.client:
            return False
        
        try:
            # Simple test call to verify API key works
            # This could be cached to avoid repeated API calls
            return True  # For now, assume it's available if we have an API key
        except Exception as e:
            logger.warning(f"OpenAI availability check failed: {e}")
            return False

    def get_provider_info(self) -> Dict[str, Any]:
        """
        Get information about the OpenAI provider and its configuration.
        
        Returns:
            Dictionary with provider information
        """
        return {
            "provider_name": self.provider_name,
            "model_name": self.model_name,
            "default_temperature": self.default_temperature,
            "max_retries": self.max_retries,
            "retry_delay": self.retry_delay,
            "is_available": self.is_available(),
            "has_api_key": bool(self.api_key),
            "usage_stats": self.get_usage_statistics()
        }
    
    def _create_entity_extraction_prompt(self, text: str, document_type: str, 
                                       entity_schema: Dict[str, Any]) -> str:
        """
        Create an optimized prompt for OpenAI entity extraction.
        
        Args:
            text: Document text to extract entities from
            document_type: Type of document
            entity_schema: Schema defining expected entities
            
        Returns:
            Formatted prompt string
        """
        # Build entity descriptions with examples
        entity_descriptions = []
        for entity_name, entity_config in entity_schema.items():
            required = "REQUIRED" if entity_config.get('required', False) else "OPTIONAL"
            entity_type = entity_config.get('type', 'string')
            description = entity_config.get('description', '')
            
            # Add type-specific guidance
            type_guidance = ""
            if entity_type == 'date':
                type_guidance = " (format: YYYY-MM-DD)"
            elif entity_type == 'amount':
                type_guidance = " (include currency symbol if present)"
            elif entity_type == 'array':
                type_guidance = " (return as array of strings)"
            
            entity_descriptions.append(
                f"- {entity_name} ({entity_type}, {required}): {description}{type_guidance}"
            )
        
        entities_text = "\n".join(entity_descriptions)
        
        return f"""You are an expert at extracting structured information from {document_type} documents.

Extract the following entities from the document text:

{entities_text}

Document text:
{text}

Instructions:
1. Return ONLY a valid JSON object with the extracted entities
2. Use null for missing values (do not omit keys)
3. Be precise and extract exactly what's written in the document
4. For dates, use YYYY-MM-DD format when possible
5. For amounts, include currency symbols if present
6. If you cannot find a required entity, still include it with null value

JSON:
"""

    def test_connection(self) -> Dict[str, Any]:
        """
        Test the OpenAI connection with a simple API call.
        
        Returns:
            Dictionary with test results
        """
        if not self.is_available():
            return {
                "success": False,
                "error": "Provider not available or not configured",
                "response_time_ms": 0
            }
        
        try:
            start_time = time.time()
            
            # Simple test prompt
            test_request = LLMRequest(
                prompt="Respond with just the word 'OK'",
                max_tokens=10,
                temperature=0.0
            )
            
            response = self.get_completion(test_request)
            response_time_ms = (time.time() - start_time) * 1000
            
            return {
                "success": response.success,
                "response": response.content.strip() if response.success else None,
                "response_time_ms": response_time_ms,
                "error": response.error_message if not response.success else None,
                "usage": response.usage if response.success else {}
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "response_time_ms": (time.time() - start_time) * 1000 if 'start_time' in locals() else 0
            }