"""Vector store service for managing document embeddings and similarity search."""

from typing import List, Dict, Optional, Tuple
import chromadb
from chromadb.config import Settings
import numpy as np
from pathlib import Path


class VectorStore:
    """Manages vector database for document embeddings."""
    
    def __init__(self, persist_directory: str = "./chroma_db", collection_name: str = "documents"):
        """
        Initialize the vector store.
        
        Args:
            persist_directory: Directory to persist the database
            collection_name: Name of the collection to use
        """
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        
        # Create directory if it doesn't exist
        Path(persist_directory).mkdir(parents=True, exist_ok=True)
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )
    
    def add_documents(
        self,
        texts: List[str],
        embeddings: np.ndarray,
        metadatas: List[Dict],
        ids: Optional[List[str]] = None
    ) -> List[str]:
        """
        Add documents to the vector store.
        
        Args:
            texts: List of text chunks
            embeddings: Numpy array of embeddings (2D)
            metadatas: List of metadata dictionaries for each chunk
            ids: Optional list of IDs. If None, will be auto-generated
            
        Returns:
            List of document IDs
        """
        if ids is None:
            ids = [f"doc_{i}_{metadatas[i].get('chunk_index', i)}" for i in range(len(texts))]
        
        # Convert numpy array to list of lists
        embeddings_list = embeddings.tolist()
        
        self.collection.add(
            embeddings=embeddings_list,
            documents=texts,
            metadatas=metadatas,
            ids=ids
        )
        
        return ids
    
    def search(
        self,
        query_embedding: np.ndarray,
        n_results: int = 5,
        filter_metadata: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Search for similar documents.
        
        Args:
            query_embedding: Query embedding vector (1D or 2D)
            n_results: Number of results to return
            filter_metadata: Optional metadata filter
            
        Returns:
            List of dictionaries with 'text', 'metadata', 'distance', and 'id' keys
        """
        # Ensure query_embedding is 2D
        if query_embedding.ndim == 1:
            query_embedding = query_embedding.reshape(1, -1)
        
        query_embedding_list = query_embedding.tolist()
        
        where = filter_metadata if filter_metadata else None
        
        results = self.collection.query(
            query_embeddings=query_embedding_list,
            n_results=n_results,
            where=where
        )
        
        # Format results
        formatted_results = []
        if results['ids'] and len(results['ids'][0]) > 0:
            for i in range(len(results['ids'][0])):
                formatted_results.append({
                    'id': results['ids'][0][i],
                    'text': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'distance': results['distances'][0][i] if 'distances' in results else None
                })
        
        return formatted_results
    
    def delete_documents(self, document_id: Optional[str] = None, filter_metadata: Optional[Dict] = None):
        """
        Delete documents from the vector store.
        
        Args:
            document_id: Specific document ID to delete
            filter_metadata: Metadata filter to delete matching documents
        """
        if document_id:
            self.collection.delete(ids=[document_id])
        elif filter_metadata:
            self.collection.delete(where=filter_metadata)
    
    def get_collection_stats(self) -> Dict:
        """Get statistics about the collection."""
        count = self.collection.count()
        return {
            'total_documents': count,
            'collection_name': self.collection_name
        }
