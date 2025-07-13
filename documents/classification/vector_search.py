import chromadb
from django.conf import settings

class VectorSearch:
    """Handles vector search in ChromaDB."""

    def __init__(self):
        self.client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIRECTORY)
        self.collection = self.client.get_or_create_collection(name=settings.CHROMA_COLLECTION_NAME)

    def search(self, embedding, n_results: int = 5):
        """Searches for similar embeddings in ChromaDB."""
        return self.collection.query(query_embeddings=[embedding.tolist()], n_results=n_results)

    def upsert(self, embedding, metadata, doc_id):
        """Upserts a document into ChromaDB."""
        self.collection.upsert(embeddings=[embedding.tolist()], metadatas=[metadata], ids=[doc_id])
