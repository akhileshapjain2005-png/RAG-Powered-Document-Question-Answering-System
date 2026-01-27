"""RAG (Retrieval-Augmented Generation) service that combines vector search and LLM."""

from typing import List, Dict, Optional, AsyncIterator
import uuid
from datetime import datetime

from app.models.embedding_model import EmbeddingModel
from app.services.vector_store import VectorStore
from app.services.llm_service import LLMService, get_llm_service
from app.utils.document_processor import DocumentProcessor


class RAGService:
    """Main RAG service that orchestrates document processing, embedding, and Q&A."""
    
    def __init__(
        self,
        embedding_model_name: str = "all-MiniLM-L6-v2",
        vector_store_path: str = "./chroma_db",
        llm_provider: str = "openai",
        llm_kwargs: Optional[Dict] = None
    ):
        """
        Initialize RAG service.
        
        Args:
            embedding_model_name: Name of the embedding model
            vector_store_path: Path to persist vector database
            llm_provider: LLM provider ("openai" or "local")
            llm_kwargs: Additional kwargs for LLM service
        """
        self.embedding_model = EmbeddingModel(model_name=embedding_model_name)
        self.vector_store = VectorStore(persist_directory=vector_store_path)
        self.document_processor = DocumentProcessor()
        
        llm_kwargs = llm_kwargs or {}
        self.llm_service = get_llm_service(provider=llm_provider, **llm_kwargs)
        
        # Store document metadata
        self.documents: Dict[str, Dict] = {}
    
    def process_and_store_document(
        self,
        file_content: bytes,
        filename: str,
        document_id: Optional[str] = None
    ) -> Dict:
        """
        Process a document and store it in the vector database.
        
        Args:
            file_content: Raw file content
            filename: Original filename
            document_id: Optional document ID (auto-generated if not provided)
            
        Returns:
            Dictionary with document info including ID and chunk count
        """
        if not self.document_processor.is_supported(filename):
            raise ValueError(f"Unsupported file type: {filename}")
        
        # Generate document ID
        if document_id is None:
            document_id = str(uuid.uuid4())
        
        # Extract text
        text = self.document_processor.extract_text(file_content, filename)
        
        # Chunk text
        chunks = self.document_processor.chunk_text(text)
        
        # Generate embeddings
        chunk_texts = [chunk['text'] for chunk in chunks]
        embeddings = self.embedding_model.encode(chunk_texts)
        
        # Prepare metadata
        metadatas = []
        ids = []
        for i, chunk in enumerate(chunks):
            metadata = chunk['metadata'].copy()
            metadata.update({
                'document_id': document_id,
                'filename': filename,
                'uploaded_at': datetime.utcnow().isoformat()
            })
            metadatas.append(metadata)
            ids.append(f"{document_id}_chunk_{i}")
        
        # Store in vector database
        self.vector_store.add_documents(
            texts=chunk_texts,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )
        
        # Store document metadata
        self.documents[document_id] = {
            'id': document_id,
            'filename': filename,
            'uploaded_at': datetime.utcnow().isoformat(),
            'chunk_count': len(chunks),
            'text_length': len(text)
        }
        
        return self.documents[document_id]
    
    async def answer_question(
        self,
        question: str,
        document_ids: Optional[List[str]] = None,
        top_k: int = 5,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict:
        """
        Answer a question using RAG.
        
        Args:
            question: User's question
            document_ids: Optional list of document IDs to search within
            top_k: Number of relevant chunks to retrieve
            conversation_history: Optional conversation history
            
        Returns:
            Dictionary with answer, sources, and metadata
        """
        # Generate query embedding
        query_embedding = self.embedding_model.encode(question)
        
        # Build filter if document_ids provided
        filter_metadata = None
        if document_ids:
            filter_metadata = {"document_id": {"$in": document_ids}}
        
        # Search for relevant chunks
        relevant_chunks = self.vector_store.search(
            query_embedding=query_embedding,
            n_results=top_k,
            filter_metadata=filter_metadata
        )
        
        if not relevant_chunks:
            return {
                'answer': "I couldn't find any relevant information in the documents to answer your question.",
                'sources': [],
                'metadata': {
                    'chunks_retrieved': 0
                }
            }
        
        # Prepare context for LLM
        context = [
            {
                'text': chunk['text'],
                'metadata': chunk['metadata'],
                'id': chunk['id']
            }
            for chunk in relevant_chunks
        ]
        
        # Generate answer using LLM
        answer = await self.llm_service.generate_response(
            query=question,
            context=context,
            conversation_history=conversation_history
        )
        
        # Extract source documents
        source_docs = {}
        for chunk in relevant_chunks:
            doc_id = chunk['metadata'].get('document_id')
            filename = chunk['metadata'].get('filename', 'Unknown')
            if doc_id not in source_docs:
                source_docs[doc_id] = {
                    'document_id': doc_id,
                    'filename': filename,
                    'chunks': []
                }
            source_docs[doc_id]['chunks'].append({
                'chunk_id': chunk['id'],
                'text': chunk['text'][:200] + '...' if len(chunk['text']) > 200 else chunk['text'],
                'distance': chunk.get('distance')
            })
        
        return {
            'answer': answer,
            'sources': list(source_docs.values()),
            'metadata': {
                'chunks_retrieved': len(relevant_chunks),
                'question': question
            }
        }
    
    async def stream_answer(
        self,
        question: str,
        document_ids: Optional[List[str]] = None,
        top_k: int = 5,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> AsyncIterator[str]:
        """
        Stream answer tokens.
        
        Args:
            question: User's question
            document_ids: Optional list of document IDs to search within
            top_k: Number of relevant chunks to retrieve
            conversation_history: Optional conversation history
            
        Yields:
            Answer tokens as strings
        """
        # Generate query embedding
        query_embedding = self.embedding_model.encode(question)
        
        # Build filter if document_ids provided
        filter_metadata = None
        if document_ids:
            filter_metadata = {"document_id": {"$in": document_ids}}
        
        # Search for relevant chunks
        relevant_chunks = self.vector_store.search(
            query_embedding=query_embedding,
            n_results=top_k,
            filter_metadata=filter_metadata
        )
        
        if not relevant_chunks:
            yield "I couldn't find any relevant information in the documents to answer your question."
            return
        
        # Prepare context
        context = [
            {
                'text': chunk['text'],
                'metadata': chunk['metadata'],
                'id': chunk['id']
            }
            for chunk in relevant_chunks
        ]
        
        # Stream answer
        async for token in self.llm_service.stream_response(
            query=question,
            context=context,
            conversation_history=conversation_history
        ):
            yield token
    
    def get_documents(self) -> List[Dict]:
        """Get list of all uploaded documents."""
        return list(self.documents.values())
    
    def get_document(self, document_id: str) -> Optional[Dict]:
        """Get a specific document by ID."""
        return self.documents.get(document_id)
    
    def delete_document(self, document_id: str) -> bool:
        """
        Delete a document and all its chunks.
        
        Args:
            document_id: Document ID to delete
            
        Returns:
            True if deleted, False if not found
        """
        if document_id not in self.documents:
            return False
        
        # Delete from vector store
        self.vector_store.delete_documents(filter_metadata={"document_id": document_id})
        
        # Remove from documents dict
        del self.documents[document_id]
        
        return True
    
    def get_stats(self) -> Dict:
        """Get service statistics."""
        vector_stats = self.vector_store.get_collection_stats()
        return {
            'total_documents': len(self.documents),
            'vector_store_documents': vector_stats['total_documents'],
            'embedding_model': self.embedding_model.model_name,
            'embedding_dimension': self.embedding_model.embedding_dim
        }
