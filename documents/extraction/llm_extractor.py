import json
import logging
from typing import Dict, Any, Optional, List
from django.conf import settings
from django.core.cache import cache
import hashlib

from documents.llm.factory import LLMFactory
from documents.llm.base import LLMRequest
from documents.extraction.base import BaseEntityExtractor
from documents.extraction.entity_validator import EntityValidator, ValidationResult
from documents.extraction.prompt_manager import get_prompt_manager
from documents.config_loader import get_document_type
from documents.exceptions import EntityExtractionError, DocumentClassificationError

logger = logging.getLogger(__name__)

class LLMExtractor(BaseEntityExtractor):
    """
    Advanced LLM-based entity extractor with comprehensive validation and prompt management.
    
    Integrates LLM providers, prompt templates, and entity validation for robust
    entity extraction from documents.
    """

    def __init__(self, provider_name: Optional[str] = None, use_cache: bool = True):
        """
        Initialize the LLM extractor.
        
        Args:
            provider_name: Specific LLM provider to use (defaults to configured provider)
            use_cache: Whether to cache extraction results
        """
        self.llm_factory = LLMFactory()
        self.provider_name = provider_name
        self.use_cache = use_cache
        self.validator = EntityValidator()
        self.prompt_manager = get_prompt_manager()
        
        # Extraction statistics
        self.extraction_stats = {
            "total_extractions": 0,
            "successful_extractions": 0,
            "failed_extractions": 0,
            "cached_extractions": 0,
            "validation_failures": 0,
            "llm_errors": 0
        }
        
        logger.info(f"Initialized LLMExtractor with provider: {provider_name or 'default'}")

    def extract_entities(self, document_type: str, text: str, **kwargs) -> Dict[str, Any]:
        """
        Extract entities from document text using LLM with comprehensive validation.
        
        Args:
            document_type: Type of document being processed
            text: Document text content
            **kwargs: Additional parameters for extraction
            
        Returns:
            Dictionary containing extracted and validated entities
            
        Raises:
            EntityExtractionError: If extraction fails
            DocumentClassificationError: If document type configuration issues
        """
        try:
            self.extraction_stats["total_extractions"] += 1
            
            # Check cache first
            if self.use_cache:
                cached_result = self._get_cached_extraction(document_type, text)
                if cached_result:
                    self.extraction_stats["cached_extractions"] += 1
                    logger.debug(f"Using cached extraction for {document_type}")
                    return cached_result
            
            # Get LLM provider
            provider = self.llm_factory.get_provider(self.provider_name)
            
            # Create extraction prompt
            prompt = self.prompt_manager.create_extraction_prompt(text, document_type)
            
            # Create LLM request
            llm_request = LLMRequest(
                prompt=prompt,
                max_tokens=kwargs.get('max_tokens', 2000),
                temperature=kwargs.get('temperature', 0.1),
                metadata={
                    "document_type": document_type,
                    "extraction_task": True,
                    "text_length": len(text)
                }
            )
            
            # Get LLM response
            logger.debug(f"Sending extraction request to LLM for {document_type}")
            llm_response = provider.extract_entities(llm_request)
            
            if not llm_response.success:
                self.extraction_stats["llm_errors"] += 1
                raise EntityExtractionError(
                    f"LLM extraction failed: {llm_response.error_message}"
                )
            
            # Parse extracted entities
            try:
                raw_entities = json.loads(llm_response.content)
                if not isinstance(raw_entities, dict):
                    raise ValueError("LLM response is not a JSON object")
            except (json.JSONDecodeError, ValueError) as e:
                self.extraction_stats["llm_errors"] += 1
                logger.error(f"Invalid LLM response format: {e}")
                logger.debug(f"Raw LLM response: {llm_response.content[:500]}...")
                raise EntityExtractionError(f"Invalid LLM response format: {e}")
            
            # Validate entities
            validation_results = self.validator.validate_entities(raw_entities, document_type)
            
            # Check validation success
            invalid_entities = [
                name for name, result in validation_results.items() 
                if not result.is_valid
            ]
            
            if invalid_entities:
                self.extraction_stats["validation_failures"] += 1
                logger.warning(f"Validation failed for entities: {invalid_entities}")
            
            # Prepare final result
            extraction_result = {
                "entities": {name: result.value for name, result in validation_results.items()},
                "validation_results": validation_results,
                "validation_summary": self.validator.get_validation_summary(validation_results),
                "raw_entities": raw_entities,
                "llm_usage": llm_response.usage_stats,
                "document_type": document_type,
                "extraction_metadata": {
                    "prompt_length": len(prompt),
                    "text_length": len(text),
                    "provider_used": provider.get_provider_name(),
                    "extraction_time": llm_response.usage_stats.get("processing_time", 0)
                }
            }
            
            # Cache the result
            if self.use_cache:
                self._cache_extraction_result(document_type, text, extraction_result)
            
            self.extraction_stats["successful_extractions"] += 1
            logger.info(f"Successfully extracted entities for {document_type}")
            
            return extraction_result
            
        except Exception as e:
            self.extraction_stats["failed_extractions"] += 1
            logger.error(f"Entity extraction failed for {document_type}: {e}")
            
            if isinstance(e, (EntityExtractionError, DocumentClassificationError)):
                raise
            else:
                raise EntityExtractionError(f"Unexpected extraction error: {e}")
    
    def extract_entities_batch(self, documents: List[Dict[str, str]], 
                              **kwargs) -> List[Dict[str, Any]]:
        """
        Extract entities from multiple documents in batch.
        
        Args:
            documents: List of dicts with 'document_type' and 'text' keys
            **kwargs: Additional parameters for extraction
            
        Returns:
            List of extraction results
        """
        results = []
        
        for i, doc in enumerate(documents):
            try:
                result = self.extract_entities(
                    document_type=doc['document_type'],
                    text=doc['text'],
                    **kwargs
                )
                result['batch_index'] = i
                results.append(result)
                
            except Exception as e:
                logger.error(f"Batch extraction failed for document {i}: {e}")
                results.append({
                    "batch_index": i,
                    "error": str(e),
                    "document_type": doc.get('document_type', 'unknown'),
                    "extraction_failed": True
                })
        
        logger.info(f"Completed batch extraction for {len(documents)} documents")
        return results
    
    def _get_cached_extraction(self, document_type: str, text: str) -> Optional[Dict[str, Any]]:
        """Get cached extraction result if available."""
        try:
            text_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()[:16]
            cache_key = f"llm_extraction:{document_type}:{text_hash}"
            
            cached_result = cache.get(cache_key)
            if cached_result:
                # Verify cache structure
                if isinstance(cached_result, dict) and 'entities' in cached_result:
                    return cached_result
                else:
                    # Invalid cache format, remove it
                    cache.delete(cache_key)
            
            return None
            
        except Exception as e:
            logger.warning(f"Cache retrieval failed: {e}")
            return None
    
    def _cache_extraction_result(self, document_type: str, text: str, 
                               result: Dict[str, Any]):
        """Cache extraction result."""
        try:
            text_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()[:16]
            cache_key = f"llm_extraction:{document_type}:{text_hash}"
            
            # Cache timeout from settings or default to 1 hour
            timeout = getattr(settings, 'LLM_CACHE_TIMEOUT', 3600)
            
            cache.set(cache_key, result, timeout=timeout)
            logger.debug(f"Cached extraction result for {document_type}")
            
        except Exception as e:
            logger.warning(f"Failed to cache extraction result: {e}")
    
    def clear_cache(self, document_type: Optional[str] = None):
        """
        Clear extraction cache.
        
        Args:
            document_type: If specified, only clear cache for this document type
        """
        try:
            if document_type:
                # This is a simplified approach - in practice you'd need to track keys
                logger.info(f"Cache clearing for specific document type not fully implemented")
            else:
                # Clear all extraction cache (simplified)
                logger.info("Full cache clearing not implemented - use Django's cache.clear()")
                
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
    
    def get_extraction_statistics(self) -> Dict[str, Any]:
        """
        Get extraction performance statistics.
        
        Returns:
            Dictionary with extraction statistics
        """
        total = self.extraction_stats["total_extractions"]
        
        return {
            **self.extraction_stats,
            "success_rate": (
                self.extraction_stats["successful_extractions"] / total * 100
                if total > 0 else 0
            ),
            "cache_hit_rate": (
                self.extraction_stats["cached_extractions"] / total * 100
                if total > 0 else 0
            ),
            "validation_statistics": self.validator.get_statistics()
        }
    
    def reset_statistics(self):
        """Reset extraction statistics."""
        self.extraction_stats = {
            "total_extractions": 0,
            "successful_extractions": 0,
            "failed_extractions": 0,
            "cached_extractions": 0,
            "validation_failures": 0,
            "llm_errors": 0
        }
        self.validator.reset_statistics()
        logger.info("Reset extraction statistics")
    
    def test_extraction(self, document_type: str, sample_text: str) -> Dict[str, Any]:
        """
        Test extraction functionality with sample text.
        
        Args:
            document_type: Document type to test
            sample_text: Sample text to extract from
            
        Returns:
            Test results including timing and validation info
        """
        import time
        
        start_time = time.time()
        
        try:
            result = self.extract_entities(document_type, sample_text)
            extraction_time = time.time() - start_time
            
            return {
                "success": True,
                "extraction_time": extraction_time,
                "entities_extracted": len(result["entities"]),
                "validation_summary": result["validation_summary"],
                "provider_used": result["extraction_metadata"]["provider_used"],
                "prompt_length": result["extraction_metadata"]["prompt_length"],
                "sample_entities": {k: v for k, v in list(result["entities"].items())[:3]}  # Show first 3
            }
            
        except Exception as e:
            extraction_time = time.time() - start_time
            return {
                "success": False,
                "extraction_time": extraction_time,
                "error": str(e),
                "error_type": type(e).__name__
            }


# Global extractor instance
_llm_extractor = None

def get_llm_extractor() -> LLMExtractor:
    """Get or create global LLM extractor instance."""
    global _llm_extractor
    
    if _llm_extractor is None:
        _llm_extractor = LLMExtractor()
    
    return _llm_extractor