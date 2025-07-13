import time
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """Represents a response from an LLM provider."""
    content: str
    usage: Dict[str, int]
    model: str
    provider: str
    response_time_ms: float
    success: bool = True
    error_message: Optional[str] = None


@dataclass
class LLMRequest:
    """Represents a request to an LLM provider."""
    prompt: str
    max_tokens: int = 500
    temperature: float = 0.1
    system_message: Optional[str] = None
    stop_sequences: Optional[List[str]] = None
    model_params: Optional[Dict[str, Any]] = None


class BaseLLMProvider(ABC):
    """
    Abstract base class for LLM providers with enhanced features for entity extraction.
    """
    
    def __init__(self, provider_name: str, model_name: str = None):
        """
        Initialize the LLM provider.
        
        Args:
            provider_name: Name of the provider (e.g., 'openai', 'anthropic')
            model_name: Name of the model to use
        """
        self.provider_name = provider_name
        self.model_name = model_name
        self.request_count = 0
        self.total_tokens_used = 0
        self.total_response_time = 0.0
    
    @abstractmethod
    def get_completion(self, request: LLMRequest) -> LLMResponse:
        """
        Generate text using the LLM with enhanced request/response handling.
        
        Args:
            request: LLMRequest object containing prompt and parameters
            
        Returns:
            LLMResponse object with generated content and metadata
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if the provider is available and configured properly.
        
        Returns:
            True if the provider is ready to use
        """
        pass
    
    @abstractmethod
    def get_provider_info(self) -> Dict[str, Any]:
        """
        Get information about the provider and its configuration.
        
        Returns:
            Dictionary with provider information
        """
        pass
    
    def get_completion_simple(self, prompt: str, max_tokens: int = 500, 
                            temperature: float = 0.1) -> str:
        """
        Simplified interface for getting completions (backward compatibility).
        
        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            
        Returns:
            Generated text content
        """
        request = LLMRequest(
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature
        )
        
        response = self.get_completion(request)
        return response.content if response.success else ""
    
    def extract_entities_json(self, text: str, document_type: str, 
                            entity_schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract entities from text and return as structured JSON.
        
        Args:
            text: Input text to extract entities from
            document_type: Type of document being processed
            entity_schema: Schema defining expected entities
            
        Returns:
            Dictionary with extracted entities
        """
        try:
            # Create structured prompt for entity extraction
            prompt = self._create_entity_extraction_prompt(text, document_type, entity_schema)
            
            # Use low temperature for deterministic results
            request = LLMRequest(
                prompt=prompt,
                max_tokens=800,
                temperature=0.0,
                stop_sequences=["```", "---"]
            )
            
            response = self.get_completion(request)
            
            if not response.success:
                logger.error(f"LLM request failed: {response.error_message}")
                return {}
            
            # Parse JSON response
            return self._parse_entity_response(response.content, entity_schema)
            
        except Exception as e:
            logger.error(f"Entity extraction failed: {e}")
            return {}
    
    def _create_entity_extraction_prompt(self, text: str, document_type: str, 
                                       entity_schema: Dict[str, Any]) -> str:
        """Create a structured prompt for entity extraction."""
        # This will be overridden in subclasses with specific prompt templates
        entity_descriptions = []
        for entity_name, entity_config in entity_schema.items():
            required = "REQUIRED" if entity_config.get('required', False) else "OPTIONAL"
            entity_type = entity_config.get('type', 'string')
            description = entity_config.get('description', '')
            
            entity_descriptions.append(
                f"- {entity_name} ({entity_type}, {required}): {description}"
            )
        
        entities_text = "\n".join(entity_descriptions)
        
        return f"""
Extract the following entities from this {document_type} document:

{entities_text}

Document text:
{text}

Return ONLY a valid JSON object with the extracted entities. Use null for missing values.
If you cannot find a required entity, still include it with null value.

JSON:
"""
    
    def _parse_entity_response(self, response_text: str, 
                             entity_schema: Dict[str, Any]) -> Dict[str, Any]:
        """Parse and validate entity extraction response."""
        import json
        import re
        
        try:
            # Try to find JSON in the response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_text = json_match.group()
                entities = json.loads(json_text)
                
                # Validate and clean entities according to schema
                validated_entities = {}
                for entity_name, entity_config in entity_schema.items():
                    entity_type = entity_config.get('type', 'string')
                    raw_value = entities.get(entity_name)
                    
                    if raw_value is not None:
                        validated_entities[entity_name] = self._validate_entity_value(
                            raw_value, entity_type
                        )
                    elif entity_config.get('required', False):
                        # Required entity missing, set to null but log warning
                        logger.warning(f"Required entity '{entity_name}' not found in LLM response")
                        validated_entities[entity_name] = None
                
                return validated_entities
            else:
                logger.warning("No JSON found in LLM response")
                return {}
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from LLM response: {e}")
            return {}
        except Exception as e:
            logger.error(f"Error parsing entity response: {e}")
            return {}
    
    def _validate_entity_value(self, value: Any, entity_type: str) -> Any:
        """Validate and convert entity value based on type."""
        if value is None:
            return None
        
        try:
            if entity_type == 'string':
                return str(value).strip()
            elif entity_type == 'number':
                return float(value) if '.' in str(value) else int(value)
            elif entity_type == 'date':
                # Basic date validation - could be enhanced
                return str(value).strip()
            elif entity_type == 'amount':
                # Basic amount validation - could be enhanced
                return str(value).strip()
            elif entity_type == 'array':
                if isinstance(value, list):
                    return value
                elif isinstance(value, str):
                    # Try to parse comma-separated values
                    return [item.strip() for item in value.split(',')]
                else:
                    return [str(value)]
            elif entity_type == 'boolean':
                if isinstance(value, bool):
                    return value
                else:
                    return str(value).lower() in ('true', 'yes', '1', 'on')
            else:
                return str(value)
                
        except Exception as e:
            logger.warning(f"Failed to validate entity value '{value}' as {entity_type}: {e}")
            return str(value) if value is not None else None
    
    def get_usage_statistics(self) -> Dict[str, Any]:
        """Get usage statistics for this provider."""
        avg_response_time = (
            self.total_response_time / self.request_count 
            if self.request_count > 0 else 0.0
        )
        
        return {
            "provider": self.provider_name,
            "model": self.model_name,
            "total_requests": self.request_count,
            "total_tokens_used": self.total_tokens_used,
            "average_response_time_ms": avg_response_time,
            "is_available": self.is_available()
        }
    
    def _update_usage_stats(self, response: LLMResponse):
        """Update internal usage statistics."""
        self.request_count += 1
        self.total_tokens_used += response.usage.get('total_tokens', 0)
        self.total_response_time += response.response_time_ms