"""API routes for the document Q&A system."""

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import StreamingResponse
from typing import List, Optional
from pydantic import BaseModel
import os

from app.services.rag_service import RAGService


# Initialize RAG service
rag_service = RAGService(
    embedding_model_name=os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2"),
    vector_store_path=os.getenv("VECTOR_STORE_PATH", "./chroma_db"),
    llm_provider=os.getenv("LLM_PROVIDER", "openai"),
    llm_kwargs={
        "api_key": os.getenv("OPENAI_API_KEY"),
        "model": os.getenv("LLM_MODEL", "gpt-3.5-turbo")
    } if os.getenv("LLM_PROVIDER", "openai") == "openai" else {}
)

router = APIRouter()


# Request/Response models
class QuestionRequest(BaseModel):
    question: str
    document_ids: Optional[List[str]] = None
    top_k: int = 5


class QuestionResponse(BaseModel):
    answer: str
    sources: List[dict]
    metadata: dict


class DocumentResponse(BaseModel):
    id: str
    filename: str
    uploaded_at: str
    chunk_count: int
    text_length: int


class StatsResponse(BaseModel):
    total_documents: int
    vector_store_documents: int
    embedding_model: str
    embedding_dimension: int


@router.post("/documents/upload", response_model=DocumentResponse)
async def upload_document(file: UploadFile = File(...)):
    """
    Upload and process a document.
    
    Supported formats: PDF, DOCX, Markdown, TXT
    """
    try:
        file_content = await file.read()
        document_info = rag_service.process_and_store_document(
            file_content=file_content,
            filename=file.filename
        )
        return DocumentResponse(**document_info)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")


@router.get("/documents", response_model=List[DocumentResponse])
async def list_documents():
    """Get list of all uploaded documents."""
    documents = rag_service.get_documents()
    return [DocumentResponse(**doc) for doc in documents]


@router.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: str):
    """Get a specific document by ID."""
    document = rag_service.get_document(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentResponse(**document)


@router.delete("/documents/{document_id}")
async def delete_document(document_id: str):
    """Delete a document and all its chunks."""
    success = rag_service.delete_document(document_id)
    if not success:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"message": "Document deleted successfully"}


@router.post("/ask", response_model=QuestionResponse)
async def ask_question(request: QuestionRequest):
    """
    Ask a question about the uploaded documents.
    
    The system will search for relevant information and generate an answer.
    """
    try:
        result = await rag_service.answer_question(
            question=request.question,
            document_ids=request.document_ids,
            top_k=request.top_k
        )
        return QuestionResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating answer: {str(e)}")


@router.post("/ask/stream")
async def ask_question_stream(request: QuestionRequest):
    """
    Ask a question and stream the response.
    
    Returns a streaming response with answer tokens.
    """
    async def generate():
        try:
            async for token in rag_service.stream_answer(
                question=request.question,
                document_ids=request.document_ids,
                top_k=request.top_k
            ):
                yield f"data: {token}\n\n"
        except Exception as e:
            yield f"data: Error: {str(e)}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/stats", response_model=StatsResponse)
async def get_stats():
    """Get service statistics."""
    stats = rag_service.get_stats()
    return StatsResponse(**stats)


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "rag-docqa"}
