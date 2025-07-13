from sentence_transformers import SentenceTransformer

class EmbeddingGenerator:
    """Generates embeddings for a given text."""

    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        self.model = SentenceTransformer(model_name)

    def generate_embedding(self, text: str):
        """Generates an embedding for the given text."""
        return self.model.encode(text)
