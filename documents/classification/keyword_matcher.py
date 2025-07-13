from django.conf import settings

class KeywordMatcher:
    """Matches keywords for a given text."""

    def __init__(self):
        self.document_types = settings.DOCUMENT_TYPES

    def match(self, text: str) -> dict:
        """Matches keywords in the text and returns scores for each document type."""
        scores = {doc_type: 0 for doc_type in self.document_types}
        text = text.lower()

        for doc_type, config in self.document_types.items():
            for keyword in config.get('keywords', []):
                if keyword.lower() in text:
                    scores[doc_type] += 1
        
        return scores
