import os
import time
import logging
from typing import List, Union, Optional
import numpy as np
from sentence_transformers import SentenceTransformer
from django.core.cache import cache
import hashlib
from documents.exceptions import DocumentClassificationError

logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """
    Generates embeddings for text using sentence transformers with caching and optimization.
    """

    def __init__(self, model_name: Optional[str] = None, cache_embeddings: bool = True):
        """
        Initialize the embedding generator.
        
        Args:
            model_name: Name of the sentence transformer model to use
            cache_embeddings: Whether to cache embeddings for performance
        """
        if model_name is None:
            model_name = os.getenv('EMBEDDING_MODEL', 'all-MiniLM-L6-v2')
            
        self.model_name = model_name
        self.cache_embeddings = cache_embeddings
        self.cache_timeout = int(os.getenv('EMBEDDING_CACHE_TIMEOUT', 3600))  # 1 hour default
        
        try:
            logger.info(f"Loading sentence transformer model: {model_name}")
            self.model = SentenceTransformer(model_name)
            logger.info(f"Successfully loaded model: {model_name}")
        except Exception as e:
            logger.error(f"Failed to load sentence transformer model {model_name}: {e}")
            raise DocumentClassificationError(f"Failed to load embedding model: {e}")

    def _get_cache_key(self, text: str) -> str:
        """Generate cache key for text embedding."""
        text_hash = hashlib.md5(text.encode('utf-8')).hexdigest()
        return f"embedding:{self.model_name}:{text_hash}"

    def _normalize_text(self, text: str) -> str:
        """Normalize text for consistent embedding generation."""
        if not text:
            return ""
        
        # Remove excessive whitespace and normalize
        text = " ".join(text.split())
        
        # Truncate very long texts to avoid memory issues (typical limit ~512 tokens)
        max_chars = int(os.getenv('MAX_TEXT_LENGTH', 2000))
        if len(text) > max_chars:
            text = text[:max_chars] + "..."
            logger.warning(f"Text truncated to {max_chars} characters for embedding generation")
            
        return text.strip()

    def generate_embedding(self, text: str) -> np.ndarray:
        """
        Generate embedding for a single text.
        
        Args:
            text: Input text to generate embedding for
            
        Returns:
            Normalized embedding vector as numpy array
            
        Raises:
            DocumentClassificationError: If embedding generation fails
        """
        if not text or not text.strip():
            # Return zero vector for empty text
            return np.zeros(self.model.get_sentence_embedding_dimension())
        
        normalized_text = self._normalize_text(text)
        
        # Check cache first
        if self.cache_embeddings:
            cache_key = self._get_cache_key(normalized_text)
            cached_embedding = cache.get(cache_key)
            if cached_embedding is not None:
                logger.debug("Retrieved embedding from cache")
                return np.array(cached_embedding)
        
        try:
            start_time = time.time()
            
            # Generate embedding
            embedding = self.model.encode(normalized_text, normalize_embeddings=True)
            
            # Ensure embedding is numpy array
            if not isinstance(embedding, np.ndarray):
                embedding = np.array(embedding)
                
            generation_time = time.time() - start_time
            logger.debug(f"Generated embedding in {generation_time:.3f}s for text of length {len(normalized_text)}")
            
            # Cache the result
            if self.cache_embeddings:
                cache_key = self._get_cache_key(normalized_text)
                cache.set(cache_key, embedding.tolist(), timeout=self.cache_timeout)
                logger.debug("Cached embedding for future use")
            
            return embedding
            
        except Exception as e:
            logger.error(f"Failed to generate embedding for text: {e}")
            raise DocumentClassificationError(f"Failed to generate embedding: {e}")

    def generate_embeddings_batch(self, texts: List[str]) -> List[np.ndarray]:
        """
        Generate embeddings for multiple texts efficiently.
        
        Args:
            texts: List of input texts
            
        Returns:
            List of normalized embedding vectors
        """
        if not texts:
            return []
            
        # Normalize all texts
        normalized_texts = [self._normalize_text(text) for text in texts]
        
        # Check cache for each text
        embeddings = []
        texts_to_process = []
        cache_keys = []
        
        if self.cache_embeddings:
            for text in normalized_texts:
                cache_key = self._get_cache_key(text)
                cached_embedding = cache.get(cache_key)
                
                if cached_embedding is not None:
                    embeddings.append(np.array(cached_embedding))
                    cache_keys.append(None)  # Mark as cached
                else:
                    embeddings.append(None)  # Mark for processing
                    texts_to_process.append(text)
                    cache_keys.append(cache_key)
        else:
            texts_to_process = normalized_texts
            cache_keys = [None] * len(texts)
            embeddings = [None] * len(texts)
        
        # Process uncached texts in batch
        if texts_to_process:
            try:
                start_time = time.time()
                batch_embeddings = self.model.encode(
                    texts_to_process, 
                    normalize_embeddings=True,
                    batch_size=32,  # Process in smaller batches
                    show_progress_bar=len(texts_to_process) > 10
                )
                
                generation_time = time.time() - start_time
                logger.info(f"Generated {len(texts_to_process)} embeddings in batch in {generation_time:.3f}s")
                
                # Insert batch results and cache them
                batch_idx = 0
                for i, embedding in enumerate(embeddings):
                    if embedding is None:  # This was not cached
                        new_embedding = np.array(batch_embeddings[batch_idx])
                        embeddings[i] = new_embedding
                        
                        # Cache the result
                        if self.cache_embeddings and cache_keys[i]:
                            cache.set(cache_keys[i], new_embedding.tolist(), timeout=self.cache_timeout)
                        
                        batch_idx += 1
                        
            except Exception as e:
                logger.error(f"Failed to generate batch embeddings: {e}")
                raise DocumentClassificationError(f"Failed to generate batch embeddings: {e}")
        
        return embeddings

    def get_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Calculate cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Cosine similarity score between -1 and 1
        """
        try:
            # Ensure embeddings are numpy arrays
            emb1 = np.array(embedding1)
            emb2 = np.array(embedding2)
            
            # Calculate cosine similarity
            dot_product = np.dot(emb1, emb2)
            norm1 = np.linalg.norm(emb1)
            norm2 = np.linalg.norm(emb2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
                
            return dot_product / (norm1 * norm2)
            
        except Exception as e:
            logger.error(f"Failed to calculate similarity: {e}")
            return 0.0

    def get_model_info(self) -> dict:
        """Get information about the loaded model."""
        return {
            "model_name": self.model_name,
            "embedding_dimension": self.model.get_sentence_embedding_dimension(),
            "max_seq_length": getattr(self.model, 'max_seq_length', 'unknown'),
            "cache_enabled": self.cache_embeddings,
            "cache_timeout": self.cache_timeout
        }
