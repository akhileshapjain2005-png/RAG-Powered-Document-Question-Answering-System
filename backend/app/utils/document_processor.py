
"""Document processing utilities for extracting and chunking documents."""

import os
import re
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List

import docx
import markdown
from pypdf import PdfReader


MAX_PDF_PAGES = int(os.getenv("MAX_PDF_PAGES", "500"))
MAX_EXTRACTED_TEXT_CHARS = int(
    os.getenv("MAX_EXTRACTED_TEXT_CHARS", "5000000")
)


class DocumentProcessor:
    """Extract text from supported document formats and split it into chunks."""

    SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".md", ".txt", ".markdown"}

    @staticmethod
    def is_supported(filename: str) -> bool:
        return Path(filename).suffix.lower() in DocumentProcessor.SUPPORTED_EXTENSIONS

    @staticmethod
    def extract_text(file_content: bytes, filename: str) -> str:
        ext = Path(filename).suffix.lower()

        if ext == ".pdf":
            return DocumentProcessor._extract_from_pdf(file_content)
        if ext == ".docx":
            return DocumentProcessor._extract_from_docx(file_content)
        if ext in {".md", ".markdown"}:
            return DocumentProcessor._extract_from_markdown(file_content)
        if ext == ".txt":
            return file_content.decode("utf-8", errors="replace")[
                :MAX_EXTRACTED_TEXT_CHARS
            ]

        raise ValueError(f"Unsupported file type: {ext}")

    @staticmethod
    def _extract_from_pdf(content: bytes) -> str:
        pdf_reader = PdfReader(BytesIO(content))
        n_pages = len(pdf_reader.pages)

        if n_pages > MAX_PDF_PAGES:
            raise ValueError(
                f"PDF has too many pages ({n_pages}); "
                f"maximum allowed is {MAX_PDF_PAGES}"
            )

        text_parts = []
        total_chars = 0

        for page in pdf_reader.pages:
            page_text = page.extract_text() or ""
            remaining = MAX_EXTRACTED_TEXT_CHARS - total_chars

            if remaining <= 0:
                break

            text_parts.append(page_text[:remaining])
            total_chars += min(len(page_text), remaining)

            if len(page_text) > remaining:
                break

        return "\n".join(text_parts)

    @staticmethod
    def _extract_from_docx(content: bytes) -> str:
        document = docx.Document(BytesIO(content))
        text = "\n".join(paragraph.text for paragraph in document.paragraphs)
        return text[:MAX_EXTRACTED_TEXT_CHARS]

    @staticmethod
    def _extract_from_markdown(content: bytes) -> str:
        md_text = content.decode("utf-8", errors="replace")
        md_text = md_text[:MAX_EXTRACTED_TEXT_CHARS]
        html = markdown.markdown(md_text)
        return re.sub(r"<[^>]+>", "", html)

    @staticmethod
    def chunk_text(
        text: str,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ) -> List[Dict[str, Any]]:
        """Split text into overlapping chunks with guaranteed forward progress."""

        if chunk_size <= 0:
            raise ValueError("chunk_size must be greater than zero")

        if chunk_overlap < 0 or chunk_overlap >= chunk_size:
            raise ValueError(
                "chunk_overlap must be non-negative and smaller than chunk_size"
            )

        if not text:
            return []

        chunks = []
        text_length = len(text)
        start = 0
        chunk_index = 0
        step = chunk_size - chunk_overlap

        while start < text_length:
            end = min(start + chunk_size, text_length)
            boundary = end

            # Prefer a nearby sentence or newline boundary, but never
            # allow boundary selection to prevent forward progress.
            if end < text_length:
                window = text[start:end]
                last_period = window.rfind(".")
                last_newline = window.rfind("\n")
                break_point = max(last_period, last_newline)

                if break_point > chunk_size // 2:
                    boundary = start + break_point + 1

            # Ensure this chunk always advances the input position.
            if boundary <= start:
                boundary = min(start + chunk_size, text_length)

            chunk = text[start:boundary].strip()

            if chunk:
                chunks.append(
                    {
                        "text": chunk,
                        "metadata": {
                            "chunk_index": chunk_index,
                            "start": start,
                            "end": boundary,
                        },
                    }
                )
                chunk_index += 1

            if boundary >= text_length:
                break

            # Always advance by at least one character, while retaining
            # the configured overlap relative to the selected boundary.
            next_start = boundary - chunk_overlap
            if next_start <= start:
                next_start = start + step

            start = next_start

        return chunks
