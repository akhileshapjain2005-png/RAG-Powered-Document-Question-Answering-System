
"""RAG service for document processing, vector search, and question answering."""

import logging
import time
import uuid

from datetime import datetime
from typing import AsyncIterator, Dict, List, Optional

from app.models.embedding_model import EmbeddingModel
from app.services.vector_store import VectorStore
from app.services.llm_service import get_llm_service
from app.utils.document_processor import DocumentProcessor


logger = logging.getLogger(__name__)


class RAGService:
    """Orchestrates document processing, embeddings, vector storage, and Q&A."""

    def __init__(
        self,
        embedding_model_name: str = "all-MiniLM-L6-v2",
        vector_store_path: str = r"C:\RAG-DocQA-Chroma",
        llm_provider: str = "ollama",
        llm_kwargs: Optional[Dict] = None,
    ):
        self.embedding_model = EmbeddingModel(
            model_name=embedding_model_name
        )

        self.vector_store = VectorStore(
            persist_directory=vector_store_path
        )

        self.document_processor = DocumentProcessor()

        llm_kwargs = dict(llm_kwargs or {})

        self.llm_service = get_llm_service(
            provider=llm_provider,
            **llm_kwargs,
        )

        # This dictionary is reconstructed from persistent ChromaDB
        # records whenever the backend starts.
        self.documents: Dict[str, Dict] = {}

        self._load_documents_from_vector_store()

        logger.info(
            "RAGService initialized: embedding_model=%s, "
            "vector_store=%s, llm_provider=%s",
            embedding_model_name,
            self.vector_store.persist_directory,
            llm_provider,
        )

    # ---------------------------------------------------------
    # Persistent document history
    # ---------------------------------------------------------

    def _load_documents_from_vector_store(self) -> None:
        """Rebuild document metadata from stored ChromaDB chunks."""

        self.documents = {}

        try:
            collection = self.vector_store.collection
            total = collection.count()

            if total == 0:
                logger.info("No stored document chunks found.")
                return

            offset = 0
            batch_size = 500

            while offset < total:
                batch = collection.get(
                    limit=batch_size,
                    offset=offset,
                    include=["metadatas", "documents"],
                )

                metadatas = batch.get("metadatas") or []
                texts = batch.get("documents") or []

                if not metadatas:
                    break

                for index, metadata in enumerate(metadatas):
                    if not metadata:
                        continue

                    document_id = metadata.get("document_id")

                    if not document_id:
                        continue

                    owner_id = metadata.get("owner_id", "anonymous")
                    filename = metadata.get("filename", "Unknown")
                    uploaded_at = metadata.get("uploaded_at", "")

                    if document_id not in self.documents:
                        self.documents[document_id] = {
                            "id": document_id,
                            "owner_id": owner_id,
                            "filename": filename,
                            "uploaded_at": uploaded_at,
                            "chunk_count": 0,
                            "text_length": 0,
                        }

                    document = self.documents[document_id]

                    document["chunk_count"] += 1

                    if index < len(texts) and texts[index]:
                        document["text_length"] += len(texts[index])

                    # Keep available metadata current.
                    if filename != "Unknown":
                        document["filename"] = filename

                    if uploaded_at:
                        document["uploaded_at"] = uploaded_at

                offset += len(metadatas)

            logger.info(
                "Restored %d documents from ChromaDB",
                len(self.documents),
            )

        except Exception:
            logger.exception(
                "Failed to restore document history from ChromaDB"
            )
            raise

    # ---------------------------------------------------------
    # Document ingestion
    # ---------------------------------------------------------

    def process_and_store_document(
        self,
        file_content: bytes,
        filename: str,
        document_id: Optional[str] = None,
        owner_id: str = "anonymous",
    ) -> Dict:
        """Extract, chunk, embed, and persist an uploaded document."""

        started = time.perf_counter()

        logger.info(
            "UPLOAD DEBUG: Processing started: filename=%s, bytes=%d",
            filename,
            len(file_content),
        )

        if not file_content:
            raise ValueError("The uploaded file is empty.")

        if not self.document_processor.is_supported(filename):
            raise ValueError(f"Unsupported file type: {filename}")

        if document_id is None:
            document_id = str(uuid.uuid4())

        # Stage 1: Extract text.
        stage_started = time.perf_counter()

        logger.info("UPLOAD DEBUG: Starting text extraction")

        try:
            text = self.document_processor.extract_text(
                file_content,
                filename,
            )
        except Exception:
            logger.exception(
                "UPLOAD DEBUG: Text extraction failed for %s",
                filename,
            )
            raise

        logger.info(
            "UPLOAD DEBUG: Text extraction completed in %.2fs; "
            "characters=%d",
            time.perf_counter() - stage_started,
            len(text or ""),
        )

        if not text or not text.strip():
            raise ValueError(
                "No readable text was extracted from this document. "
                "If the PDF contains scanned pages, OCR may be required."
            )

        # Stage 2: Chunk text.
        stage_started = time.perf_counter()

        logger.info("UPLOAD DEBUG: Starting text chunking")

        chunks = self.document_processor.chunk_text(text)

        logger.info(
            "UPLOAD DEBUG: Chunking completed in %.2fs; chunks=%d",
            time.perf_counter() - stage_started,
            len(chunks),
        )

        valid_chunks = [
            chunk
            for chunk in chunks
            if chunk.get("text") and chunk["text"].strip()
        ]

        if not valid_chunks:
            raise ValueError(
                "No usable text chunks were generated from the document."
            )

        chunk_texts = [
            chunk["text"] for chunk in valid_chunks
        ]

        # Stage 3: Generate embeddings.
        stage_started = time.perf_counter()

        logger.info(
            "UPLOAD DEBUG: Starting embedding generation; chunks=%d",
            len(chunk_texts),
        )

        try:
            embeddings = self.embedding_model.encode(chunk_texts)
        except Exception:
            logger.exception(
                "UPLOAD DEBUG: Embedding generation failed"
            )
            raise

        logger.info(
            "UPLOAD DEBUG: Embedding generation completed in %.2fs",
            time.perf_counter() - stage_started,
        )

        if len(embeddings) != len(chunk_texts):
            raise RuntimeError(
                "The embedding count does not match the number of chunks."
            )

        # Stage 4: Build metadata and stable chunk IDs.
        uploaded_at = datetime.utcnow().isoformat()

        metadatas = []
        ids = []

        for index, chunk in enumerate(valid_chunks):
            metadata = dict(chunk.get("metadata") or {})

            metadata.update(
                {
                    "document_id": document_id,
                    "owner_id": owner_id,
                    "filename": filename,
                    "uploaded_at": uploaded_at,
                    "chunk_index": index,
                }
            )

            metadatas.append(metadata)
            ids.append(f"{document_id}_chunk_{index}")

        # Stage 5: Persist the chunks and embeddings.
        stage_started = time.perf_counter()

        logger.info(
            "UPLOAD DEBUG: Starting vector-store write; chunks=%d",
            len(chunk_texts),
        )

        try:
            self.vector_store.add_documents(
                texts=chunk_texts,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids,
            )
        except Exception:
            logger.exception(
                "UPLOAD DEBUG: Vector-store write failed"
            )
            raise

        logger.info(
            "UPLOAD DEBUG: Vector-store write completed in %.2fs",
            time.perf_counter() - stage_started,
        )

        # Publish the in-memory metadata only after storage succeeds.
        document_info = {
            "id": document_id,
            "owner_id": owner_id,
            "filename": filename,
            "uploaded_at": uploaded_at,
            "chunk_count": len(chunk_texts),
            "text_length": len(text),
        }

        self.documents[document_id] = document_info

        logger.info(
            "UPLOAD DEBUG: Processing completed; filename=%s, "
            "chunks=%d, total_seconds=%.2f",
            filename,
            len(chunk_texts),
            time.perf_counter() - started,
        )

        return document_info

    # ---------------------------------------------------------
    # Document ownership and retrieval helpers
    # ---------------------------------------------------------

    def _get_owned_document_ids(
        self,
        owner_id: str,
        document_ids: Optional[List[str]] = None,
    ) -> List[str]:
        """Return document IDs belonging to the specified owner."""

        if document_ids is not None:
            return [
                doc_id
                for doc_id in document_ids
                if doc_id in self.documents
                and self.documents[doc_id].get("owner_id") == owner_id
            ]

        return [
            doc_id
            for doc_id, document in self.documents.items()
            if document.get("owner_id") == owner_id
        ]

    def _build_document_filter(
        self,
        owner_id: str,
        owned_doc_ids: List[str],
    ) -> Dict:
        """Build the metadata filter for vector searches."""

        return {
            "$and": [
                {"owner_id": owner_id},
                {"document_id": {"$in": owned_doc_ids}},
            ]
        }

    def _retrieve_chunks(
        self,
        question: str,
        owner_id: str,
        document_ids: Optional[List[str]],
        top_k: int,
    ) -> List[Dict]:
        """Embed a question and retrieve relevant document chunks."""

        owned_doc_ids = self._get_owned_document_ids(
            owner_id=owner_id,
            document_ids=document_ids,
        )

        if not owned_doc_ids:
            return []

        query_embedding = self.embedding_model.encode(question)

        return self.vector_store.search(
            query_embedding=query_embedding,
            n_results=top_k,
            filter_metadata=self._build_document_filter(
                owner_id,
                owned_doc_ids,
            ),
        )

    # ---------------------------------------------------------
    # Question answering
    # ---------------------------------------------------------

    async def answer_question(
        self,
        question: str,
        document_ids: Optional[List[str]] = None,
        top_k: int = 5,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        owner_id: str = "anonymous",
    ) -> Dict:
        """Retrieve relevant chunks and generate an answer."""

        relevant_chunks = self._retrieve_chunks(
            question=question,
            owner_id=owner_id,
            document_ids=document_ids,
            top_k=top_k,
        )

        if not relevant_chunks:
            return {
                "answer": (
                    "I couldn't find any relevant information in the "
                    "uploaded documents to answer your question."
                ),
                "sources": [],
                "metadata": {
                    "chunks_retrieved": 0,
                    "question": question,
                },
            }

        context = [
            {
                "text": chunk["text"],
                "metadata": chunk["metadata"],
                "id": chunk["id"],
            }
            for chunk in relevant_chunks
        ]

        answer = await self.llm_service.generate_response(
            query=question,
            context=context,
            conversation_history=conversation_history,
        )

        source_docs = {}

        for chunk in relevant_chunks:
            metadata = chunk.get("metadata") or {}
            doc_id = metadata.get("document_id")
            filename = metadata.get("filename", "Unknown")

            if doc_id not in source_docs:
                source_docs[doc_id] = {
                    "document_id": doc_id,
                    "filename": filename,
                    "chunks": [],
                }

            chunk_text = chunk.get("text", "")

            source_docs[doc_id]["chunks"].append(
                {
                    "chunk_id": chunk.get("id"),
                    "text": (
                        chunk_text[:200] + "..."
                        if len(chunk_text) > 200
                        else chunk_text
                    ),
                    "distance": chunk.get("distance"),
                }
            )

        return {
            "answer": answer,
            "sources": list(source_docs.values()),
            "metadata": {
                "chunks_retrieved": len(relevant_chunks),
                "question": question,
            },
        }

    # ---------------------------------------------------------
    # Streaming question answering
    # ---------------------------------------------------------

    async def stream_answer(
        self,
        question: str,
        document_ids: Optional[List[str]] = None,
        top_k: int = 5,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        owner_id: str = "anonymous",
    ) -> AsyncIterator[str]:
        """Retrieve document chunks and stream an answer."""

        relevant_chunks = self._retrieve_chunks(
            question=question,
            owner_id=owner_id,
            document_ids=document_ids,
            top_k=top_k,
        )

        if not relevant_chunks:
            yield (
                "I couldn't find any relevant information in the "
                "uploaded documents to answer your question."
            )
            return

        context = [
            {
                "text": chunk["text"],
                "metadata": chunk["metadata"],
                "id": chunk["id"],
            }
            for chunk in relevant_chunks
        ]

        async for token in self.llm_service.stream_response(
            query=question,
            context=context,
            conversation_history=conversation_history,
        ):
            yield token

    # ---------------------------------------------------------
    # Document metadata
    # ---------------------------------------------------------

    def get_documents(
        self,
        owner_id: str = "anonymous",
    ) -> List[Dict]:
        """Return persisted document metadata for an owner."""

        return [
            {
                key: value
                for key, value in document.items()
                if key != "owner_id"
            }
            for document in self.documents.values()
            if document.get("owner_id") == owner_id
        ]

    def get_document(
        self,
        document_id: str,
        owner_id: str = "anonymous",
    ) -> Optional[Dict]:
        """Return a document if it belongs to the specified owner."""

        document = self.documents.get(document_id)

        if not document or document.get("owner_id") != owner_id:
            return None

        return {
            key: value
            for key, value in document.items()
            if key != "owner_id"
        }

    def delete_document(
        self,
        document_id: str,
        owner_id: str = "anonymous",
    ) -> bool:
        """Delete all vector chunks belonging to a document."""

        document = self.documents.get(document_id)

        if not document or document.get("owner_id") != owner_id:
            return False

        self.vector_store.delete_documents(
            filter_metadata={
                "$and": [
                    {"document_id": document_id},
                    {"owner_id": owner_id},
                ]
            }
        )

        del self.documents[document_id]

        logger.info(
            "Deleted document: id=%s owner_id=%s",
            document_id,
            owner_id,
        )

        return True

    def get_stats(
        self,
        owner_id: str = "anonymous",
    ) -> Dict:
        """Return document and embedding statistics for an owner."""

        user_documents = [
            document
            for document in self.documents.values()
            if document.get("owner_id") == owner_id
        ]

        total_documents = len(user_documents)

        return {
            "total_documents": total_documents,
            "vector_store_documents": total_documents,
            "embedding_model": self.embedding_model.model_name,
            "embedding_dimension": self.embedding_model.embedding_dim,
        }
