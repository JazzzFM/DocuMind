"""
Classification feedback and statistics tracking system.
Tracks user corrections and classification performance metrics.
"""

import logging
import time
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from django.core.cache import cache
from django.db import models, transaction
from documents.classification.classifier import DocumentClassifier
from documents.exceptions import DocumentClassificationError

logger = logging.getLogger(__name__)


@dataclass
class ClassificationFeedback:
    """Represents user feedback on a classification result."""
    document_id: str
    original_classification: str
    corrected_classification: str
    original_confidence: float
    user_id: Optional[str] = None
    feedback_timestamp: float = None
    notes: Optional[str] = None
    
    def __post_init__(self):
        if self.feedback_timestamp is None:
            self.feedback_timestamp = time.time()


@dataclass
class ClassificationStats:
    """Aggregated classification statistics."""
    total_classifications: int
    correct_classifications: int
    accuracy: float
    document_type_stats: Dict[str, Dict[str, Any]]
    confidence_distribution: Dict[str, int]
    processing_time_stats: Dict[str, float]
    last_updated: float


class ClassificationFeedbackTracker:
    """
    Tracks classification feedback and provides performance statistics.
    Supports automatic retraining signals and performance monitoring.
    """
    
    def __init__(self, classifier: Optional[DocumentClassifier] = None):
        """
        Initialize the feedback tracker.
        
        Args:
            classifier: Optional DocumentClassifier instance for retraining
        """
        self.classifier = classifier
        self.cache_timeout = 3600  # 1 hour cache timeout
        self.stats_cache_key = "classification_stats"
        self.feedback_cache_prefix = "classification_feedback"
        
    def submit_feedback(self, feedback: ClassificationFeedback) -> bool:
        """
        Submit user feedback on a classification result.
        
        Args:
            feedback: ClassificationFeedback instance
            
        Returns:
            True if feedback was recorded successfully
        """
        try:
            # Store feedback in cache for quick access
            feedback_key = f"{self.feedback_cache_prefix}:{feedback.document_id}"
            feedback_data = asdict(feedback)
            
            # Get existing feedback list or create new one
            existing_feedback = cache.get(feedback_key, [])
            existing_feedback.append(feedback_data)
            
            # Store updated feedback list
            cache.set(feedback_key, existing_feedback, timeout=self.cache_timeout * 24)  # 24 hours
            
            # Update global feedback statistics
            self._update_feedback_stats(feedback)
            
            # If classifier is available, trigger reindex with correct classification
            if self.classifier and feedback.corrected_classification != "unknown":
                self._update_document_index(feedback)
            
            logger.info(
                f"Feedback recorded for document {feedback.document_id}: "
                f"{feedback.original_classification} -> {feedback.corrected_classification}"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to submit feedback: {e}")
            return False
    
    def _update_feedback_stats(self, feedback: ClassificationFeedback):
        """Update aggregated feedback statistics."""
        try:
            stats_key = f"{self.stats_cache_key}_feedback"
            feedback_stats = cache.get(stats_key, {
                "total_feedback": 0,
                "corrections_by_type": {},
                "accuracy_by_type": {},
                "common_misclassifications": {}
            })
            
            # Update total feedback count
            feedback_stats["total_feedback"] += 1
            
            # Track corrections by document type
            original_type = feedback.original_classification
            corrected_type = feedback.corrected_classification
            
            if original_type not in feedback_stats["corrections_by_type"]:
                feedback_stats["corrections_by_type"][original_type] = {}
            
            if corrected_type not in feedback_stats["corrections_by_type"][original_type]:
                feedback_stats["corrections_by_type"][original_type][corrected_type] = 0
            
            feedback_stats["corrections_by_type"][original_type][corrected_type] += 1
            
            # Track common misclassifications
            if original_type != corrected_type:
                misclass_key = f"{original_type}_as_{corrected_type}"
                if misclass_key not in feedback_stats["common_misclassifications"]:
                    feedback_stats["common_misclassifications"][misclass_key] = 0
                feedback_stats["common_misclassifications"][misclass_key] += 1
            
            # Update cache
            cache.set(stats_key, feedback_stats, timeout=self.cache_timeout * 24)
            
        except Exception as e:
            logger.warning(f"Failed to update feedback stats: {e}")
    
    def _update_document_index(self, feedback: ClassificationFeedback):
        """Update document index with corrected classification."""
        try:
            if not self.classifier:
                return
                
            # Get document from vector store
            document = self.classifier.vector_search.get_document(feedback.document_id)
            
            if document and document.get('document'):
                # Re-index with correct classification
                success = self.classifier.add_document_to_index(
                    feedback.document_id,
                    document['document'],
                    feedback.corrected_classification,
                    document.get('metadata', {})
                )
                
                if success:
                    logger.info(f"Updated index for document {feedback.document_id} with correct classification")
                else:
                    logger.warning(f"Failed to update index for document {feedback.document_id}")
                    
        except Exception as e:
            logger.warning(f"Failed to update document index: {e}")
    
    def get_document_feedback(self, document_id: str) -> List[ClassificationFeedback]:
        """
        Get all feedback for a specific document.
        
        Args:
            document_id: Document identifier
            
        Returns:
            List of ClassificationFeedback instances
        """
        try:
            feedback_key = f"{self.feedback_cache_prefix}:{document_id}"
            feedback_data = cache.get(feedback_key, [])
            
            return [ClassificationFeedback(**data) for data in feedback_data]
            
        except Exception as e:
            logger.error(f"Failed to get feedback for document {document_id}: {e}")
            return []
    
    def get_feedback_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive feedback statistics.
        
        Returns:
            Dictionary with feedback statistics
        """
        try:
            stats_key = f"{self.stats_cache_key}_feedback"
            feedback_stats = cache.get(stats_key, {})
            
            if not feedback_stats:
                return {
                    "total_feedback": 0,
                    "corrections_by_type": {},
                    "accuracy_by_type": {},
                    "common_misclassifications": {},
                    "last_updated": None
                }
            
            # Calculate accuracy by type
            accuracy_by_type = {}
            for doc_type, corrections in feedback_stats.get("corrections_by_type", {}).items():
                total_for_type = sum(corrections.values())
                correct_for_type = corrections.get(doc_type, 0)  # Same type = correct
                
                if total_for_type > 0:
                    accuracy_by_type[doc_type] = correct_for_type / total_for_type
                else:
                    accuracy_by_type[doc_type] = 0.0
            
            feedback_stats["accuracy_by_type"] = accuracy_by_type
            feedback_stats["last_updated"] = time.time()
            
            return feedback_stats
            
        except Exception as e:
            logger.error(f"Failed to get feedback statistics: {e}")
            return {"error": str(e)}
    
    def get_classification_performance(self, days: int = 7) -> Dict[str, Any]:
        """
        Get classification performance metrics over a time period.
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Performance metrics dictionary
        """
        try:
            # This would typically query a database for classification logs
            # For now, we'll return cached statistics
            feedback_stats = self.get_feedback_statistics()
            
            if self.classifier:
                system_stats = self.classifier.get_classification_statistics()
            else:
                system_stats = {}
            
            return {
                "time_period_days": days,
                "feedback_metrics": feedback_stats,
                "system_metrics": system_stats,
                "recommendations": self._generate_recommendations(feedback_stats)
            }
            
        except Exception as e:
            logger.error(f"Failed to get classification performance: {e}")
            return {"error": str(e)}
    
    def _generate_recommendations(self, feedback_stats: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on feedback statistics."""
        recommendations = []
        
        try:
            total_feedback = feedback_stats.get("total_feedback", 0)
            accuracy_by_type = feedback_stats.get("accuracy_by_type", {})
            common_misclassifications = feedback_stats.get("common_misclassifications", {})
            
            # Recommend action if we have enough feedback
            if total_feedback < 10:
                recommendations.append("Collect more user feedback to improve classification accuracy")
            
            # Identify document types with low accuracy
            for doc_type, accuracy in accuracy_by_type.items():
                if accuracy < 0.8 and total_feedback > 5:
                    recommendations.append(
                        f"Consider reviewing and expanding keywords for '{doc_type}' "
                        f"document type (current accuracy: {accuracy:.1%})"
                    )
            
            # Identify common misclassifications
            if common_misclassifications:
                most_common = max(common_misclassifications.items(), key=lambda x: x[1])
                if most_common[1] > 2:  # More than 2 occurrences
                    recommendations.append(
                        f"Common misclassification: {most_common[0]} "
                        f"({most_common[1]} occurrences). Consider refining classification rules."
                    )
            
            # Recommend retraining if accuracy is consistently low
            overall_accuracy = sum(accuracy_by_type.values()) / len(accuracy_by_type) if accuracy_by_type else 1.0
            if overall_accuracy < 0.85 and total_feedback > 20:
                recommendations.append(
                    "Overall classification accuracy is below 85%. "
                    "Consider retraining the model with feedback data."
                )
            
        except Exception as e:
            logger.warning(f"Failed to generate recommendations: {e}")
            recommendations.append("Unable to generate recommendations due to insufficient data")
        
        return recommendations
    
    def clear_feedback_data(self, days_old: Optional[int] = None) -> bool:
        """
        Clear old feedback data.
        
        Args:
            days_old: Clear feedback older than this many days. If None, clear all.
            
        Returns:
            True if successful
        """
        try:
            if days_old is None:
                # Clear all feedback statistics
                stats_key = f"{self.stats_cache_key}_feedback"
                cache.delete(stats_key)
                
                # Note: Individual document feedback would need database cleanup
                # This is a simplified implementation using cache
                
                logger.info("Cleared all feedback data")
            else:
                # This would require database implementation for proper time-based cleanup
                logger.warning("Time-based feedback cleanup not implemented with cache-only storage")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to clear feedback data: {e}")
            return False
    
    def export_feedback_data(self) -> Dict[str, Any]:
        """
        Export feedback data for analysis or backup.
        
        Returns:
            Dictionary containing all feedback data
        """
        try:
            feedback_stats = self.get_feedback_statistics()
            performance_metrics = self.get_classification_performance()
            
            return {
                "export_timestamp": time.time(),
                "feedback_statistics": feedback_stats,
                "performance_metrics": performance_metrics,
                "data_format_version": "1.0"
            }
            
        except Exception as e:
            logger.error(f"Failed to export feedback data: {e}")
            return {"error": str(e)}


# Global feedback tracker instance
_feedback_tracker = None

def get_feedback_tracker(classifier: Optional[DocumentClassifier] = None) -> ClassificationFeedbackTracker:
    """Get or create global feedback tracker instance."""
    global _feedback_tracker
    
    if _feedback_tracker is None:
        _feedback_tracker = ClassificationFeedbackTracker(classifier)
    
    return _feedback_tracker