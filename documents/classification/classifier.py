import logging
from typing import Dict, Any, Optional, List, Tuple
import time
from documents.classification.embedding_generator import EmbeddingGenerator
from documents.classification.keyword_matcher import KeywordMatcher
from documents.classification.vector_search import VectorSearch
from documents.config_loader import get_document_types, get_document_type
from documents.exceptions import DocumentClassificationError

logger = logging.getLogger(__name__)


class DocumentClassifier:
    """
    Classifies documents using a hybrid approach combining embeddings and keyword matching.
    Supports configurable confidence thresholds per document type.
    """

    def __init__(self, embedding_weight: float = 0.6, keyword_weight: float = 0.4):
        """
        Initialize the document classifier.
        
        Args:
            embedding_weight: Weight for embedding similarity scores (0.0 to 1.0)
            keyword_weight: Weight for keyword matching scores (0.0 to 1.0)
        """
        if not (0.0 <= embedding_weight <= 1.0 and 0.0 <= keyword_weight <= 1.0):
            raise ValueError("Weights must be between 0.0 and 1.0")
        
        if abs(embedding_weight + keyword_weight - 1.0) > 1e-6:
            logger.warning(f"Weights sum to {embedding_weight + keyword_weight}, not 1.0. They will be normalized.")
            total = embedding_weight + keyword_weight
            embedding_weight = embedding_weight / total
            keyword_weight = keyword_weight / total
        
        self.embedding_weight = embedding_weight
        self.keyword_weight = keyword_weight
        
        # Initialize components
        try:
            self.embedding_generator = EmbeddingGenerator()
            self.keyword_matcher = KeywordMatcher()
            self.vector_search = VectorSearch()
            
            # Load document type configurations
            self.document_types = get_document_types()
            
            logger.info(f"DocumentClassifier initialized with {len(self.document_types)} document types")
            logger.info(f"Weights: embedding={self.embedding_weight:.2f}, keyword={self.keyword_weight:.2f}")
            
        except Exception as e:
            logger.error(f"Failed to initialize DocumentClassifier: {e}")
            raise DocumentClassificationError(f"Failed to initialize classifier: {e}")

    def classify(self, text: str, confidence_threshold: Optional[float] = None, 
                include_scores: bool = False) -> Tuple[str, float, Optional[Dict[str, Any]]]:
        """
        Classify the given text using hybrid approach.
        
        Args:
            text: Input text to classify
            confidence_threshold: Override default confidence threshold
            include_scores: Whether to include detailed scoring information
            
        Returns:
            Tuple of (document_type, confidence, optional_details)
        """
        if not text or not text.strip():
            return "unknown", 0.0, None
        
        start_time = time.time()
        
        try:
            # Generate embedding
            embedding = self.embedding_generator.generate_embedding(text)
            
            # Get keyword matching scores
            keyword_scores = self.keyword_matcher.match(text)
            
            # Get embedding similarity scores
            embedding_scores = self._get_embedding_scores(embedding, keyword_scores.keys())
            
            # Combine scores using weighted approach
            combined_scores = self._combine_scores(keyword_scores, embedding_scores)
            
            # Determine best classification
            best_doc_type, final_confidence = self._select_best_classification(
                combined_scores, confidence_threshold
            )
            
            processing_time = time.time() - start_time
            logger.debug(f"Classification completed in {processing_time:.3f}s: {best_doc_type} ({final_confidence:.3f})")
            
            # Prepare detailed results if requested
            details = None
            if include_scores:
                details = {
                    "keyword_scores": keyword_scores,
                    "embedding_scores": embedding_scores,
                    "combined_scores": combined_scores,
                    "processing_time_ms": processing_time * 1000,
                    "embedding_weight": self.embedding_weight,
                    "keyword_weight": self.keyword_weight,
                    "confidence_threshold_used": confidence_threshold or self._get_confidence_threshold(best_doc_type)
                }
            
            return best_doc_type, final_confidence, details
            
        except Exception as e:
            logger.error(f"Classification failed: {e}")
            raise DocumentClassificationError(f"Error during document classification: {e}") from e

    def _get_embedding_scores(self, embedding, document_types: List[str]) -> Dict[str, float]:
        """Get embedding similarity scores for each document type."""
        try:
            # Search for similar documents in vector store
            search_results = self.vector_search.search_by_document_type(
                embedding, list(document_types), n_results_per_type=5
            )
            
            embedding_scores = {}
            
            for doc_type in document_types:
                type_results = search_results.get(doc_type, {})
                distances = type_results.get('distances', [[]])
                
                if distances and distances[0]:
                    # Convert distances to similarities and average them
                    similarities = [1 - dist for dist in distances[0] if dist <= 1.0]
                    if similarities:
                        # Use weighted average with higher weight for more similar documents
                        weights = [1 / (i + 1) for i in range(len(similarities))]  # 1, 0.5, 0.33, ...
                        weighted_sum = sum(sim * weight for sim, weight in zip(similarities, weights))
                        weight_sum = sum(weights)
                        embedding_scores[doc_type] = weighted_sum / weight_sum
                    else:
                        embedding_scores[doc_type] = 0.0
                else:
                    embedding_scores[doc_type] = 0.0
            
            return embedding_scores
            
        except Exception as e:
            logger.warning(f"Failed to get embedding scores: {e}")
            return {doc_type: 0.0 for doc_type in document_types}

    def _combine_scores(self, keyword_scores: Dict[str, float], 
                       embedding_scores: Dict[str, float]) -> Dict[str, float]:
        """Combine keyword and embedding scores using weighted approach."""
        combined_scores = {}
        
        for doc_type in keyword_scores.keys():
            keyword_score = keyword_scores.get(doc_type, 0.0)
            embedding_score = embedding_scores.get(doc_type, 0.0)
            
            combined_score = (
                self.embedding_weight * embedding_score + 
                self.keyword_weight * keyword_score
            )
            
            combined_scores[doc_type] = combined_score
        
        return combined_scores

    def _get_confidence_threshold(self, doc_type: str) -> float:
        """Get confidence threshold for a specific document type."""
        doc_config = get_document_type(doc_type)
        if doc_config:
            return doc_config.confidence_threshold
        return 0.7  # Default threshold

    def _select_best_classification(self, combined_scores: Dict[str, float], 
                                  confidence_threshold: Optional[float] = None) -> Tuple[str, float]:
        """Select the best classification based on scores and thresholds."""
        if not any(combined_scores.values()):
            return "unknown", 0.0
        
        # Get the document type with highest score
        best_doc_type = max(combined_scores, key=combined_scores.get)
        best_score = combined_scores[best_doc_type]
        
        # Use provided threshold or document-specific threshold
        threshold = confidence_threshold or self._get_confidence_threshold(best_doc_type)
        
        if best_score < threshold:
            return "unknown", best_score
        
        return best_doc_type, best_score

    def add_document_to_index(self, document_id: str, text: str, document_type: str, 
                            extracted_entities: Optional[Dict[str, Any]] = None) -> bool:
        """
        Add a document to the search index.
        
        Args:
            document_id: Unique identifier for the document
            text: Document text content
            document_type: Classified document type
            extracted_entities: Optional extracted entities
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Generate embedding
            embedding = self.embedding_generator.generate_embedding(text)
            
            # Prepare metadata
            metadata = {
                'document_type': document_type,
                'text_length': len(text),
                'indexed_at': time.time()
            }
            
            if extracted_entities:
                # Add extracted entities to metadata (flatten if needed)
                for key, value in extracted_entities.items():
                    if isinstance(value, (str, int, float, bool)):
                        metadata[f'entity_{key}'] = value
                    else:
                        metadata[f'entity_{key}'] = str(value)
            
            # Add to vector search index
            success = self.vector_search.upsert(embedding, metadata, document_id, text)
            
            if success:
                logger.info(f"Successfully indexed document {document_id} as {document_type}")
            else:
                logger.error(f"Failed to index document {document_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error adding document {document_id} to index: {e}")
            return False

    def batch_classify(self, texts: List[str], include_scores: bool = False) -> List[Tuple[str, float, Optional[Dict[str, Any]]]]:
        """
        Classify multiple texts efficiently.
        
        Args:
            texts: List of texts to classify
            include_scores: Whether to include detailed scoring information
            
        Returns:
            List of classification results
        """
        if not texts:
            return []
        
        try:
            start_time = time.time()
            
            # Generate embeddings in batch for efficiency
            embeddings = self.embedding_generator.generate_embeddings_batch(texts)
            
            results = []
            for i, (text, embedding) in enumerate(zip(texts, embeddings)):
                try:
                    # Get keyword scores
                    keyword_scores = self.keyword_matcher.match(text)
                    
                    # Get embedding scores
                    embedding_scores = self._get_embedding_scores(embedding, keyword_scores.keys())
                    
                    # Combine and classify
                    combined_scores = self._combine_scores(keyword_scores, embedding_scores)
                    best_doc_type, confidence = self._select_best_classification(combined_scores)
                    
                    # Prepare details if requested
                    details = None
                    if include_scores:
                        details = {
                            "keyword_scores": keyword_scores,
                            "embedding_scores": embedding_scores,
                            "combined_scores": combined_scores
                        }
                    
                    results.append((best_doc_type, confidence, details))
                    
                except Exception as e:
                    logger.error(f"Failed to classify text {i}: {e}")
                    results.append(("unknown", 0.0, None))
            
            total_time = time.time() - start_time
            logger.info(f"Batch classified {len(texts)} documents in {total_time:.3f}s")
            
            return results
            
        except Exception as e:
            logger.error(f"Batch classification failed: {e}")
            raise DocumentClassificationError(f"Batch classification failed: {e}")

    def get_classification_statistics(self) -> Dict[str, Any]:
        """Get statistics about the classification system."""
        try:
            vector_stats = self.vector_search.get_collection_stats()
            embedding_info = self.embedding_generator.get_model_info()
            
            return {
                "document_types": len(self.document_types),
                "supported_types": list(self.document_types.keys()),
                "vector_store": vector_stats,
                "embedding_model": embedding_info,
                "weights": {
                    "embedding": self.embedding_weight,
                    "keyword": self.keyword_weight
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get classification statistics: {e}")
            return {"error": str(e)}