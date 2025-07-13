import json
from django.conf import settings
from documents.llm.factory import LLMFactory
from documents.extraction.base import BaseEntityExtractor
from documents.extraction.entity_validator import EntityValidator
from pathlib import Path
from django.core.cache import cache
import hashlib
from documents.exceptions import EntityExtractionError

class LLMExtractor(BaseEntityExtractor):
    """Extracts entities from text using an LLM."""

    def __init__(self):
        self.llm_provider = LLMFactory.get_provider()
        self.validator = EntityValidator()

    def extract_entities(self, document_type: str, text: str) -> dict:
        """Extracts entities based on the document type and text."""
        cache_key = f"llm_extraction:{document_type}:{hashlib.sha256(text.encode()).hexdigest()}"
        cached_entities = cache.get(cache_key)
        if cached_entities:
            return cached_entities

        prompt_path = Path(settings.BASE_DIR).parent / f"config/prompts/{document_type}.txt"
        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt template for {document_type} not found.")

        with open(prompt_path, 'r') as f:
            prompt_template = f.read()

        # Get expected entities from document_types.yaml
        expected_entities = settings.DOCUMENT_TYPES.get(document_type, {}).get('entities', [])

        # Replace placeholders in the prompt template
        prompt = prompt_template.format(text=text)

        try:
            response = self.llm_provider.get_completion(prompt)
            raw_entities = json.loads(response)
            validated_entities = self.validator.validate(raw_entities, expected_entities)
            cache.set(cache_key, validated_entities, timeout=settings.LLM_CACHE_TIMEOUT) # Cache for configurable time
            return validated_entities
        except json.JSONDecodeError as e:
            raise EntityExtractionError(f"LLM response is not valid JSON: {e}") from e
        except Exception as e:
            raise EntityExtractionError(f"An unexpected error occurred during entity extraction: {e}") from e