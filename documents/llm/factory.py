import os
import logging
from typing import Optional, Dict, Any, List
from django.conf import settings
from decouple import config
from documents.llm.base import BaseLLMProvider
from documents.llm.openai_provider import OpenAIProvider
from documents.exceptions import DocumentClassificationError

logger = logging.getLogger(__name__)


class LLMProviderRegistry:
    """Registry for managing multiple LLM providers."""
    
    def __init__(self):
        self._providers: Dict[str, BaseLLMProvider] = {}
        self._default_provider: Optional[str] = None
    
    def register_provider(self, name: str, provider: BaseLLMProvider):
        """Register a new LLM provider."""
        self._providers[name] = provider
        logger.info(f"Registered LLM provider: {name}")
    
    def get_provider(self, name: Optional[str] = None) -> Optional[BaseLLMProvider]:
        """Get a specific provider by name or the default provider."""
        if name:
            return self._providers.get(name)
        elif self._default_provider:
            return self._providers.get(self._default_provider)
        elif self._providers:
            # Return the first available provider
            for provider in self._providers.values():
                if provider.is_available():
                    return provider
        return None
    
    def get_available_providers(self) -> List[str]:
        """Get list of available provider names."""
        return [
            name for name, provider in self._providers.items() 
            if provider.is_available()
        ]
    
    def set_default_provider(self, name: str):
        """Set the default provider."""
        if name in self._providers:
            self._default_provider = name
            logger.info(f"Set default LLM provider to: {name}")
        else:
            raise ValueError(f"Provider '{name}' not registered")
    
    def get_all_providers_info(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all registered providers."""
        return {
            name: provider.get_provider_info() 
            for name, provider in self._providers.items()
        }


class LLMFactory:
    """
    Enhanced factory for creating and managing LLM providers with fallback support.
    """
    
    _registry = LLMProviderRegistry()
    _initialized = False
    
    @classmethod
    def initialize(cls):
        """Initialize the factory with available providers."""
        if cls._initialized:
            return
        
        try:
            # Register OpenAI provider
            try:
                openai_provider = OpenAIProvider()
                cls._registry.register_provider("openai", openai_provider)
                
                if openai_provider.is_available():
                    logger.info("OpenAI provider is available")
                else:
                    logger.warning("OpenAI provider registered but not available (likely missing API key)")
            except Exception as e:
                logger.warning(f"Failed to register OpenAI provider: {e}")
            
            # TODO: Register other providers (Anthropic, Hugging Face, etc.)
            # try:
            #     anthropic_provider = AnthropicProvider()
            #     cls._registry.register_provider("anthropic", anthropic_provider)
            # except Exception as e:
            #     logger.warning(f"Failed to register Anthropic provider: {e}")
            
            # Set default provider based on configuration
            default_provider = config('LLM_PROVIDER', default='openai')
            available_providers = cls._registry.get_available_providers()
            
            if default_provider in available_providers:
                cls._registry.set_default_provider(default_provider)
                logger.info(f"Using configured default provider: {default_provider}")
            elif available_providers:
                # Fallback to first available provider
                fallback_provider = available_providers[0]
                cls._registry.set_default_provider(fallback_provider)
                logger.warning(
                    f"Configured provider '{default_provider}' not available. "
                    f"Using fallback: {fallback_provider}"
                )
            else:
                logger.error("No LLM providers are available!")
            
            cls._initialized = True
            
        except Exception as e:
            logger.error(f"Failed to initialize LLM factory: {e}")
            raise DocumentClassificationError(f"LLM factory initialization failed: {e}")
    
    @classmethod
    def get_provider(cls, provider_name: Optional[str] = None) -> BaseLLMProvider:
        """
        Get an LLM provider instance.
        
        Args:
            provider_name: Optional specific provider name. If None, returns default.
            
        Returns:
            LLM provider instance
            
        Raises:
            DocumentClassificationError: If no providers are available
        """
        cls.initialize()
        
        provider = cls._registry.get_provider(provider_name)
        
        if provider is None:
            available = cls._registry.get_available_providers()
            if provider_name:
                raise DocumentClassificationError(
                    f"LLM provider '{provider_name}' not available. "
                    f"Available providers: {available}"
                )
            else:
                raise DocumentClassificationError(
                    f"No LLM providers available. Available providers: {available}"
                )
        
        if not provider.is_available():
            raise DocumentClassificationError(
                f"LLM provider '{provider.provider_name}' is not available"
            )
        
        return provider
    
    @classmethod
    def get_best_provider(cls) -> BaseLLMProvider:
        """
        Get the best available provider based on performance and availability.
        
        Returns:
            Best available LLM provider
        """
        cls.initialize()
        
        available_providers = cls._registry.get_available_providers()
        
        if not available_providers:
            raise DocumentClassificationError("No LLM providers are available")
        
        # For now, just return the default provider
        # In the future, this could implement more sophisticated selection logic
        # based on performance metrics, cost, etc.
        return cls.get_provider()
    
    @classmethod
    def get_provider_for_task(cls, task: str) -> BaseLLMProvider:
        """
        Get the best provider for a specific task.
        
        Args:
            task: Task type (e.g., 'entity_extraction', 'classification', 'summarization')
            
        Returns:
            Best provider for the task
        """
        cls.initialize()
        
        # For now, all tasks use the same provider
        # In the future, this could route different tasks to different providers
        # based on their strengths
        return cls.get_provider()
    
    @classmethod
    def list_providers(cls) -> List[str]:
        """Get list of all available provider names."""
        cls.initialize()
        return cls._registry.get_available_providers()
    
    @classmethod
    def get_providers_info(cls) -> Dict[str, Dict[str, Any]]:
        """Get detailed information about all providers."""
        cls.initialize()
        return cls._registry.get_all_providers_info()
    
    @classmethod
    def test_provider(cls, provider_name: str) -> Dict[str, Any]:
        """
        Test a specific provider's connectivity and functionality.
        
        Args:
            provider_name: Name of the provider to test
            
        Returns:
            Test results dictionary
        """
        cls.initialize()
        
        try:
            provider = cls._registry.get_provider(provider_name)
            if provider is None:
                return {
                    "provider": provider_name,
                    "success": False,
                    "error": "Provider not found or not registered"
                }
            
            # Test basic connectivity
            if hasattr(provider, 'test_connection'):
                return provider.test_connection()
            else:
                # Fallback test
                return {
                    "provider": provider_name,
                    "success": provider.is_available(),
                    "error": None if provider.is_available() else "Provider not available"
                }
                
        except Exception as e:
            return {
                "provider": provider_name,
                "success": False,
                "error": str(e)
            }
    
    @classmethod
    def test_all_providers(cls) -> Dict[str, Dict[str, Any]]:
        """Test all registered providers."""
        cls.initialize()
        
        all_providers = list(cls._registry._providers.keys())
        results = {}
        
        for provider_name in all_providers:
            results[provider_name] = cls.test_provider(provider_name)
        
        return results