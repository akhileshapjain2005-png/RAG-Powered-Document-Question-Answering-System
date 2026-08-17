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
        llm_provider: str = "ollama",
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
        self.llm_service = get_llm_service(
    provider="ollama",
    model="llama3.2",
    base_url="http://localhost:11434"
)
        
        # Store document metadata
        self.documents: Dict[str, Dict] = {}
    
    def process_and_store_document(
        self,
        file_content: bytes,
        filename: str,
        document_id: Optional[str] = None,
        owner_id: str = "anonymous",
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
                'owner_id': owner_id,
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
            'owner_id': owner_id,
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
        conversation_history: Optional[List[Dict[str, str]]] = None,
        owner_id: str = "anonymous",
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
        if document_ids:
            owned_doc_ids = [
                doc_id
                for doc_id in document_ids
                if doc_id in self.documents and self.documents[doc_id].get("owner_id") == owner_id
            ]
            if not owned_doc_ids:
                return {
                    'answer': "I couldn't find any relevant information in the documents to answer your question.",
                    'sources': [],
                    'metadata': {'chunks_retrieved': 0}
                }
            filter_metadata = {
                "$and": [
                    {"owner_id": owner_id},
                    {"document_id": {"$in": owned_doc_ids}},
                ]
            }
        else:
            owned_doc_ids = [
                doc_id
                for doc_id, doc in self.documents.items()
                if doc.get("owner_id") == owner_id
            ]
            if not owned_doc_ids:
                return {
                    'answer': "I couldn't find any relevant information in the documents to answer your question.",
                    'sources': [],
                    'metadata': {'chunks_retrieved': 0}
                }
            filter_metadata = {
                "$and": [
                    {"owner_id": owner_id},
                    {"document_id": {"$in": owned_doc_ids}},
                ]
            }
        
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
        conversation_history: Optional[List[Dict[str, str]]] = None,
        owner_id: str = "anonymous",
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
        if document_ids:
            owned_doc_ids = [
                doc_id
                for doc_id in document_ids
                if doc_id in self.documents and self.documents[doc_id].get("owner_id") == owner_id
            ]
            if not owned_doc_ids:
                yield "I couldn't find any relevant information in the documents to answer your question."
                return
            filter_metadata = {
                "$and": [
                    {"owner_id": owner_id},
                    {"document_id": {"$in": owned_doc_ids}},
                ]
            }
        else:
            owned_doc_ids = [
                doc_id
                for doc_id, doc in self.documents.items()
                if doc.get("owner_id") == owner_id
            ]
            if not owned_doc_ids:
                yield "I couldn't find any relevant information in the documents to answer your question."
                return
            filter_metadata = {
                "$and": [
                    {"owner_id": owner_id},
                    {"document_id": {"$in": owned_doc_ids}},
                ]
            }
        
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
    
    def get_documents(self, owner_id: str = "anonymous") -> List[Dict]:
        """Get list of all uploaded documents."""
        return [
            {k: v for k, v in doc.items() if k != "owner_id"}
            for doc in self.documents.values()
            if doc.get("owner_id") == owner_id
        ]
    
    def get_document(self, document_id: str, owner_id: str = "anonymous") -> Optional[Dict]:
        """Get a specific document by ID."""
        doc = self.documents.get(document_id)
        if not doc or doc.get("owner_id") != owner_id:
            return None
        return {k: v for k, v in doc.items() if k != "owner_id"}
    
    def delete_document(self, document_id: str, owner_id: str = "anonymous") -> bool:
        """
        Delete a document and all its chunks.
        
        Args:
            document_id: Document ID to delete
            
        Returns:
            True if deleted, False if not found
        """
        if document_id not in self.documents:
            return False
        if self.documents[document_id].get("owner_id") != owner_id:
            return False
        
        # Delete from vector store
        self.vector_store.delete_documents(
            filter_metadata={
                "$and": [
                    {"document_id": document_id},
                    {"owner_id": owner_id},
                ]
            }
        )
        
        # Remove from documents dict
        del self.documents[document_id]
        
        return True
    
    def get_stats(self, owner_id: str = "anonymous") -> Dict:
        """Get service statistics."""
        user_document_count = len(
            [doc for doc in self.documents.values() if doc.get("owner_id") == owner_id]
        )
        return {
            'total_documents': user_document_count,
            'vector_store_documents': user_document_count,
            'embedding_model': self.embedding_model.model_name,
            'embedding_dimension': self.embedding_model.embedding_dim
        }
