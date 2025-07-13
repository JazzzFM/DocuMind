from django.conf import settings
from documents.llm.openai_provider import OpenAIProvider

class LLMFactory:
    """Factory for creating LLM providers."""

    @staticmethod
    def get_provider():
        """Gets the LLM provider based on the settings."""
        provider_name = settings.LLM_PROVIDER
        if provider_name == "openai":
            return OpenAIProvider()
        # Add other providers here as they are implemented
        else:
            raise ValueError(f"Unknown LLM provider: {provider_name}")