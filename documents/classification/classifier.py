from documents.classification.embedding_generator import EmbeddingGenerator
from documents.classification.keyword_matcher import KeywordMatcher
from documents.classification.vector_search import VectorSearch

class DocumentClassifier:
    """Classifies documents using a hybrid approach."""

    def __init__(self, embedding_weight: float = 0.6, keyword_weight: float = 0.4):
        self.embedding_generator = EmbeddingGenerator()
        self.keyword_matcher = KeywordMatcher()
        self.vector_search = VectorSearch()
        self.embedding_weight = embedding_weight
        self.keyword_weight = keyword_weight

    def classify(self, text: str, confidence_threshold: float = 0.7):
        """Classifies the given text."""
        embedding = self.embedding_generator.generate_embedding(text)
        
        # Keyword matching scores
        keyword_scores = self.keyword_matcher.match(text)

        # Embedding similarity scores
        search_results = self.vector_search.search(embedding)
        embedding_scores = {doc_type: 0 for doc_type in keyword_scores.keys()}
        if search_results and search_results['metadatas'] and search_results['distances']:
            for metadata, distance in zip(search_results['metadatas'][0], search_results['distances'][0]):
                doc_type = metadata.get('document_type')
                if doc_type in embedding_scores:
                    embedding_scores[doc_type] += 1 - distance # Similarity is 1 - distance

        # Combine scores
        combined_scores = {doc_type: (self.embedding_weight * embedding_scores.get(doc_type, 0)) + (self.keyword_weight * keyword_scores.get(doc_type, 0)) for doc_type in keyword_scores.keys()}

        # Get the document type with the highest score
        if not any(combined_scores.values()):
            return "unknown", 0.0
            
        best_doc_type = max(combined_scores, key=combined_scores.get)
        confidence = combined_scores[best_doc_type]

        if confidence < confidence_threshold:
            return "unknown", confidence

        return best_doc_type, confidence

    def add_document_to_index(self, document_id: str, text: str, document_type: str, extracted_entities: dict = None):
        """Adds a document to the search index."""
        embedding = self.embedding_generator.generate_embedding(text)
        metadata = {'document_type': document_type}
        if extracted_entities:
            metadata.update(extracted_entities)
        self.vector_search.upsert(embedding, metadata, document_id)