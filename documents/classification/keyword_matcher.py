import re
from typing import Dict
from documents.config_loader import get_document_types


class KeywordMatcher:
    """Matches keywords for a given text using fuzzy matching and weighting."""

    def __init__(self):
        self.document_types = get_document_types()
        self._compile_patterns()

    def _compile_patterns(self):
        """Compile regex patterns for efficient keyword matching."""
        self.patterns = {}
        for doc_type, config in self.document_types.items():
            patterns = []
            for keyword in config.keywords:
                # Create word boundary pattern for exact matches
                pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
                patterns.append(pattern)
            self.patterns[doc_type] = re.compile('|'.join(patterns), re.IGNORECASE)

    def match(self, text: str) -> Dict[str, float]:
        """
        Matches keywords in the text and returns normalized scores for each document type.
        
        Args:
            text: Input text to analyze
            
        Returns:
            Dictionary mapping document types to normalized scores (0.0 to 1.0)
        """
        if not text or not text.strip():
            return {doc_type: 0.0 for doc_type in self.document_types}

        text_lower = text.lower()
        word_count = len(text.split())
        scores = {}

        for doc_type, config in self.document_types.items():
            matches = self.patterns[doc_type].findall(text_lower)
            keyword_count = len(matches)
            
            if keyword_count == 0:
                scores[doc_type] = 0.0
            else:
                # Calculate score based on keyword density and total keywords for this type
                total_keywords = len(config.keywords)
                unique_matches = len(set(matches))
                
                # Density score: how many keywords found relative to text length
                density_score = keyword_count / max(word_count, 1)
                
                # Coverage score: how many different keywords found relative to total keywords
                coverage_score = unique_matches / total_keywords
                
                # Combine density and coverage with equal weight
                raw_score = (density_score + coverage_score) / 2
                
                # Apply confidence threshold scaling
                threshold = config.confidence_threshold
                scores[doc_type] = min(raw_score / threshold, 1.0)

        return scores

    def get_keyword_matches(self, text: str, doc_type: str) -> list:
        """
        Get list of actual keyword matches for a specific document type.
        
        Args:
            text: Input text to analyze
            doc_type: Document type to check
            
        Returns:
            List of matched keywords
        """
        if doc_type not in self.patterns:
            return []
            
        text_lower = text.lower()
        matches = self.patterns[doc_type].findall(text_lower)
        return list(set(matches))  # Remove duplicates

    def explain_match(self, text: str, doc_type: str) -> Dict[str, any]:
        """
        Provide detailed explanation of keyword matching for a document type.
        
        Args:
            text: Input text to analyze
            doc_type: Document type to explain
            
        Returns:
            Dictionary with match details
        """
        if doc_type not in self.document_types:
            return {"error": f"Unknown document type: {doc_type}"}
            
        config = self.document_types[doc_type]
        matches = self.get_keyword_matches(text, doc_type)
        score = self.match(text).get(doc_type, 0.0)
        
        return {
            "document_type": doc_type,
            "score": score,
            "matched_keywords": matches,
            "total_keywords": len(config.keywords),
            "available_keywords": config.keywords,
            "coverage": len(matches) / len(config.keywords) if config.keywords else 0.0,
            "confidence_threshold": config.confidence_threshold
        }
