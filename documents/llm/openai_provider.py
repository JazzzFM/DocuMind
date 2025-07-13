import os
from openai import OpenAI
from documents.llm.base import BaseLLMProvider
from decouple import config

class OpenAIProvider(BaseLLMProvider):
    """OpenAI LLM provider implementation."""

    def __init__(self):
        self.api_key = config('OPENAI_API_KEY', default=None)
        self.model = config('LLM_MODEL', default='gpt-4-turbo-preview')
        self.temperature = config('LLM_TEMPERATURE', default=0.1, cast=float)
        self.client = OpenAI(api_key=self.api_key)

    def get_completion(self, prompt: str, max_tokens: int = 150) -> str:
        """Gets a completion from the OpenAI LLM."""
        if not self.is_available():
            raise ValueError("OpenAI API key not configured.")

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens,
            temperature=self.temperature,
        )
        return response.choices[0].message.content

    def is_available(self) -> bool:
        """Checks if the OpenAI provider is available and configured."""
        return self.api_key is not None