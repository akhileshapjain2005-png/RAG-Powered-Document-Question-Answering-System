
"""API routes for the document Q&A system."""

import logging
import os
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator
from starlette.concurrency import run_in_threadpool

from app.services.rag_service import RAGService
from app.limiter import limiter
from app.security.auth import (
    SecurityContext,
    get_security_context,
    require_stats_role,
)
from app.security.audit import audit_event
from app.utils.safe_filename import sanitize_upload_filename

logger = logging.getLogger(__name__)

MAX_UPLOAD_BYTES = int(
    os.getenv("MAX_UPLOAD_BYTES", 10 * 1024 * 1024)
)
AUDIT_ASK = os.getenv("AUDIT_LOG_ASK", "false").lower() == "true"
RATE_LIMIT_UPLOAD = os.getenv("RATE_LIMIT_UPLOAD", "20/hour")
RATE_LIMIT_ASK = os.getenv("RATE_LIMIT_ASK", "120/hour")
RATE_LIMIT_READ = os.getenv("RATE_LIMIT_READ", "600/hour")

# Initialize RAG service
rag_service = RAGService(
    embedding_model_name=os.getenv(
        "EMBEDDING_MODEL", "all-MiniLM-L6-v2"
    ),
  vector_store_path=os.getenv(
    "VECTOR_STORE_PATH",
    r"C:\RAG-DocQA-Chroma",
),
    llm_provider=os.getenv("LLM_PROVIDER", "ollama"),
    llm_kwargs={
        "model": os.getenv("LLM_MODEL", "llama3.2"),
        "base_url": os.getenv(
            "OLLAMA_BASE_URL", "http://localhost:11434"
        ),
    },
)

router = APIRouter()


# Request/Response models
class QuestionRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    document_ids: Optional[List[str]] = Field(
        default=None, max_length=100
    )
    top_k: int = Field(default=5, ge=1, le=20)

    @field_validator("document_ids")
    @classmethod
    def validate_document_ids(
        cls, value: Optional[List[str]]
    ) -> Optional[List[str]]:
        if value is None:
            return value

        for doc_id in value:
            try:
                UUID(doc_id)
            except ValueError as exc:
                raise ValueError(
                    f"Invalid document_id: {doc_id}"
                ) from exc

        return value


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


def _request_id(request: Request) -> Optional[str]:
    return getattr(request.state, "request_id", None)


def _public_error_message(exc: Exception) -> str:
    if isinstance(exc, ValueError):
        return str(exc)
    return "An internal server error occurred."


# Document upload
@router.post("/documents/upload", response_model=DocumentResponse)
# @limiter.limit(RATE_LIMIT_UPLOAD)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    ctx: SecurityContext = Depends(get_security_context),
):
    """Upload and process a document.

    Supported formats depend on DocumentProcessor.
    """
    owner_id = ctx.owner_id

    try:
        logger.info(
            "Document upload started: filename=%s request_id=%s",
            file.filename,
            _request_id(request),
        )

        # Validate Content-Length when provided.
        content_length_header = request.headers.get("content-length")
        if content_length_header:
            try:
                content_length = int(content_length_header)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid Content-Length",
                ) from None

            # Content-Length includes multipart overhead.
            if content_length > MAX_UPLOAD_BYTES + 1024 * 1024:
                raise HTTPException(
                    status_code=413,
                    detail="File too large",
                )

        # Read the uploaded file asynchronously.
        file_content = await file.read()

        if len(file_content) > MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=413,
                detail="File too large",
            )

        safe_name = sanitize_upload_filename(file.filename or "")

        logger.info(
            "Upload received: filename=%s size_bytes=%d request_id=%s",
            safe_name,
            len(file_content),
            _request_id(request),
        )

        # Run blocking PDF extraction, embedding, and vector-store work
        # outside FastAPI's event loop.
        processing_started = __import__("time").perf_counter()

        document_info = await run_in_threadpool(
            rag_service.process_and_store_document,
            file_content=file_content,
            filename=safe_name,
            owner_id=owner_id,
        )

        logger.info(
            "Document processed: filename=%s chunks=%s elapsed_seconds=%.2f request_id=%s",
            safe_name,
            document_info.get("chunk_count"),
            __import__("time").perf_counter() - processing_started,
            _request_id(request),
        )

        audit_event(
            "document.upload",
            subject=ctx.subject,
            tenant_id=ctx.tenant_id,
            auth_method=ctx.auth_method,
            resource_type="document",
            resource_id=document_info.get("id"),
            request_id=_request_id(request),
            extra={
                "filename": safe_name,
                "chunk_count": document_info.get("chunk_count"),
            },
        )

        return DocumentResponse(**document_info)

    except HTTPException:
        raise

    except Exception as exc:
        logger.exception(
            "Failed to process uploaded document; request_id=%s",
            _request_id(request),
        )

        audit_event(
            "document.upload",
            subject=ctx.subject,
            tenant_id=ctx.tenant_id,
            auth_method=ctx.auth_method,
            resource_type="document",
            outcome="failure",
            request_id=_request_id(request),
            extra={"error": type(exc).__name__},
        )

        status_code = 400 if isinstance(exc, ValueError) else 500
        raise HTTPException(
            status_code=status_code,
            detail=_public_error_message(exc),
        ) from exc

    finally:
        await file.close()


# List documents
@router.get("/documents", response_model=List[DocumentResponse])
# @limiter.limit(RATE_LIMIT_READ)
async def list_documents(
    _request: Request,
    ctx: SecurityContext = Depends(get_security_context),
):
    """Get the current user's uploaded documents."""
    documents = await run_in_threadpool(
        rag_service.get_documents,
        owner_id=ctx.owner_id,
    )
    return [DocumentResponse(**doc) for doc in documents]


# Get one document
@router.get("/documents/{document_id}", response_model=DocumentResponse)
# @limiter.limit(RATE_LIMIT_READ)
async def get_document(
    _request: Request,
    document_id: str,
    ctx: SecurityContext = Depends(get_security_context),
):
    """Get a specific document by ID."""
    document = await run_in_threadpool(
        rag_service.get_document,
        document_id,
        owner_id=ctx.owner_id,
    )

    if not document:
        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

    return DocumentResponse(**document)


# Delete document
@router.delete("/documents/{document_id}")
# @limiter.limit(RATE_LIMIT_READ)
async def delete_document(
    request: Request,
    document_id: str,
    ctx: SecurityContext = Depends(get_security_context),
):
    """Delete a document and its chunks."""
    success = await run_in_threadpool(
        rag_service.delete_document,
        document_id,
        owner_id=ctx.owner_id,
    )

    if not success:
        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

    audit_event(
        "document.delete",
        subject=ctx.subject,
        tenant_id=ctx.tenant_id,
        auth_method=ctx.auth_method,
        resource_type="document",
        resource_id=document_id,
        request_id=_request_id(request),
    )

    return {"message": "Document deleted successfully"}


# Ask a question
@router.post("/ask", response_model=QuestionResponse)
@limiter.limit(RATE_LIMIT_ASK)
async def ask_question(
    request: Request,
    body: QuestionRequest,
    ctx: SecurityContext = Depends(get_security_context),
):
    """Search uploaded documents and generate an answer."""
    try:
        if AUDIT_ASK:
            audit_event(
                "qa.ask",
                subject=ctx.subject,
                tenant_id=ctx.tenant_id,
                auth_method=ctx.auth_method,
                request_id=_request_id(request),
                extra={
                    "top_k": body.top_k,
                    "scoped_docs": bool(body.document_ids),
                },
            )

        result = await rag_service.answer_question(
            question=body.question,
            document_ids=body.document_ids,
            top_k=body.top_k,
            owner_id=ctx.owner_id,
        )

        return QuestionResponse(**result)

    except Exception as exc:
        logger.exception("Failed to generate answer")
        raise HTTPException(
            status_code=500,
            detail=_public_error_message(exc),
        ) from exc


# Stream an answer
@router.post("/ask/stream")
# @limiter.limit(RATE_LIMIT_ASK)
async def ask_question_stream(
    request: Request,
    body: QuestionRequest,
    ctx: SecurityContext = Depends(get_security_context),
):
    """Stream an answer as server-sent events."""
    if AUDIT_ASK:
        audit_event(
            "qa.ask_stream",
            subject=ctx.subject,
            tenant_id=ctx.tenant_id,
            auth_method=ctx.auth_method,
            request_id=_request_id(request),
            extra={
                "top_k": body.top_k,
                "scoped_docs": bool(body.document_ids),
            },
        )

    async def generate():
        try:
            async for token in rag_service.stream_answer(
                question=body.question,
                document_ids=body.document_ids,
                top_k=body.top_k,
                owner_id=ctx.owner_id,
            ):
                yield f"data: {token}\n\n"

        except Exception:
            logger.exception("Failed to stream answer")
            yield "data: Error: Unable to generate streaming response\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# Statistics
@router.get("/stats", response_model=StatsResponse)
# @limiter.limit(RATE_LIMIT_READ)
async def get_stats(
    request: Request,
    ctx: SecurityContext = Depends(require_stats_role),
):
    """Get service statistics."""
    stats = await run_in_threadpool(
        rag_service.get_stats,
        owner_id=ctx.owner_id,
    )

    audit_event(
        "stats.read",
        subject=ctx.subject,
        tenant_id=ctx.tenant_id,
        auth_method=ctx.auth_method,
        request_id=_request_id(request),
    )

    return StatsResponse(**stats)


# Health check
@router.get("/health")
async def health_check():
    """Check service health."""
    return {"status": "healthy", "service": "rag-docqa"}
