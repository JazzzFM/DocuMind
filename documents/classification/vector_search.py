import os
import logging
from typing import List, Dict, Any, Optional, Union
import chromadb
from django.conf import settings
import numpy as np
from documents.exceptions import DocumentClassificationError

logger = logging.getLogger(__name__)


class VectorSearch:
    """
    Handles vector search operations in ChromaDB with improved error handling and features.
    """

    def __init__(self, collection_name: Optional[str] = None, persist_directory: Optional[str] = None):
        """
        Initialize ChromaDB client and collection.
        
        Args:
            collection_name: Name of the ChromaDB collection
            persist_directory: Directory to persist ChromaDB data
        """
        try:
            # Use provided values or fall back to settings/environment
            self.persist_directory = persist_directory or getattr(settings, 'CHROMA_PERSIST_DIRECTORY', './chroma_db')
            self.collection_name = collection_name or getattr(settings, 'CHROMA_COLLECTION_NAME', 'documents_collection')
            
            # Ensure persist directory exists
            os.makedirs(self.persist_directory, exist_ok=True)
            
            # Initialize ChromaDB client
            logger.info(f"Initializing ChromaDB client with persist directory: {self.persist_directory}")
            self.client = chromadb.PersistentClient(path=self.persist_directory)
            
            # Get or create collection
            logger.info(f"Getting or creating collection: {self.collection_name}")
            self.collection = self.client.get_or_create_collection(name=self.collection_name)
            
            logger.info(f"ChromaDB initialized successfully. Collection count: {self.collection.count()}")
            
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            raise DocumentClassificationError(f"Failed to initialize vector search: {e}")

    def search(self, embedding: Union[List[float], np.ndarray], n_results: int = 5, 
               document_type_filter: Optional[str] = None) -> Dict[str, Any]:
        """
        Search for similar embeddings in ChromaDB.
        
        Args:
            embedding: Query embedding vector
            n_results: Number of results to return
            document_type_filter: Optional filter by document type
            
        Returns:
            Dictionary containing search results with ids, metadatas, distances, and documents
        """
        try:
            # Convert numpy array to list if needed
            if isinstance(embedding, np.ndarray):
                embedding = embedding.tolist()
            
            # Prepare query parameters
            query_params = {
                "query_embeddings": [embedding],
                "n_results": n_results,
                "include": ["metadatas", "distances", "documents"]
            }
            
            # Add document type filter if specified
            if document_type_filter:
                query_params["where"] = {"document_type": document_type_filter}
            
            # Perform search
            results = self.collection.query(**query_params)
            
            logger.debug(f"Vector search returned {len(results['ids'][0]) if results['ids'] else 0} results")
            
            return results
            
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            raise DocumentClassificationError(f"Vector search failed: {e}")

    def search_by_document_type(self, embedding: Union[List[float], np.ndarray], 
                              document_types: List[str], n_results_per_type: int = 3) -> Dict[str, Dict[str, Any]]:
        """
        Search for similar embeddings grouped by document type.
        
        Args:
            embedding: Query embedding vector
            document_types: List of document types to search
            n_results_per_type: Number of results per document type
            
        Returns:
            Dictionary mapping document types to their search results
        """
        results_by_type = {}
        
        for doc_type in document_types:
            try:
                results = self.search(embedding, n_results_per_type, doc_type)
                results_by_type[doc_type] = results
            except Exception as e:
                logger.warning(f"Search failed for document type {doc_type}: {e}")
                results_by_type[doc_type] = {"ids": [[]], "metadatas": [[]], "distances": [[]], "documents": [[]]}
        
        return results_by_type

    def upsert(self, embedding: Union[List[float], np.ndarray], metadata: Dict[str, Any], 
               doc_id: str, document_text: Optional[str] = None) -> bool:
        """
        Upsert a document into ChromaDB.
        
        Args:
            embedding: Document embedding vector
            metadata: Document metadata
            doc_id: Unique document identifier
            document_text: Optional document text content
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Convert numpy array to list if needed
            if isinstance(embedding, np.ndarray):
                embedding = embedding.tolist()
            
            # Prepare upsert parameters
            upsert_params = {
                "embeddings": [embedding],
                "metadatas": [metadata],
                "ids": [doc_id]
            }
            
            # Add document text if provided
            if document_text:
                upsert_params["documents"] = [document_text]
            
            # Perform upsert
            self.collection.upsert(**upsert_params)
            
            logger.debug(f"Successfully upserted document {doc_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to upsert document {doc_id}: {e}")
            return False

    def batch_upsert(self, embeddings: List[Union[List[float], np.ndarray]], 
                    metadatas: List[Dict[str, Any]], doc_ids: List[str], 
                    documents: Optional[List[str]] = None) -> int:
        """
        Batch upsert multiple documents into ChromaDB.
        
        Args:
            embeddings: List of embedding vectors
            metadatas: List of metadata dictionaries
            doc_ids: List of document IDs
            documents: Optional list of document texts
            
        Returns:
            Number of successfully upserted documents
        """
        if not (len(embeddings) == len(metadatas) == len(doc_ids)):
            raise ValueError("All input lists must have the same length")
        
        try:
            # Convert numpy arrays to lists if needed
            processed_embeddings = []
            for emb in embeddings:
                if isinstance(emb, np.ndarray):
                    processed_embeddings.append(emb.tolist())
                else:
                    processed_embeddings.append(emb)
            
            # Prepare batch upsert parameters
            upsert_params = {
                "embeddings": processed_embeddings,
                "metadatas": metadatas,
                "ids": doc_ids
            }
            
            if documents:
                if len(documents) != len(doc_ids):
                    raise ValueError("Documents list must have same length as other parameters")
                upsert_params["documents"] = documents
            
            # Perform batch upsert
            self.collection.upsert(**upsert_params)
            
            logger.info(f"Successfully batch upserted {len(doc_ids)} documents")
            return len(doc_ids)
            
        except Exception as e:
            logger.error(f"Batch upsert failed: {e}")
            return 0

    def delete_document(self, doc_id: str) -> bool:
        """
        Delete a document from ChromaDB.
        
        Args:
            doc_id: Document ID to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.collection.delete(ids=[doc_id])
            logger.debug(f"Successfully deleted document {doc_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete document {doc_id}: {e}")
            return False

    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a specific document from ChromaDB.
        
        Args:
            doc_id: Document ID to retrieve
            
        Returns:
            Document data or None if not found
        """
        try:
            results = self.collection.get(ids=[doc_id], include=["metadatas", "documents", "embeddings"])
            
            if results['ids'] and len(results['ids']) > 0:
                return {
                    'id': results['ids'][0],
                    'metadata': results['metadatas'][0] if results['metadatas'] else None,
                    'document': results['documents'][0] if results['documents'] else None,
                    'embedding': results['embeddings'][0] if results['embeddings'] else None
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to retrieve document {doc_id}: {e}")
            return None

    def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the ChromaDB collection.
        
        Returns:
            Dictionary with collection statistics
        """
        try:
            count = self.collection.count()
            
            # Get sample of documents to analyze document types
            sample_results = self.collection.get(limit=min(100, count), include=["metadatas"])
            
            doc_type_counts = {}
            if sample_results['metadatas']:
                for metadata in sample_results['metadatas']:
                    doc_type = metadata.get('document_type', 'unknown')
                    doc_type_counts[doc_type] = doc_type_counts.get(doc_type, 0) + 1
            
            return {
                "total_documents": count,
                "collection_name": self.collection_name,
                "persist_directory": self.persist_directory,
                "document_type_distribution": doc_type_counts,
                "sample_size": len(sample_results['metadatas']) if sample_results['metadatas'] else 0
            }
            
        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            return {"error": str(e)}

    def reset_collection(self) -> bool:
        """
        Reset (clear) the ChromaDB collection.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Delete the collection and recreate it
            self.client.delete_collection(name=self.collection_name)
            self.collection = self.client.create_collection(name=self.collection_name)
            
            logger.info(f"Successfully reset collection {self.collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to reset collection: {e}")
            return False
