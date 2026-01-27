"""Document processing utilities for extracting text from various file formats."""

import os
from typing import List, Dict, Optional
from pathlib import Path
import PyPDF2
import docx
import markdown
from io import BytesIO


class DocumentProcessor:
    """Processes documents in various formats and extracts text."""
    
    SUPPORTED_EXTENSIONS = {'.pdf', '.docx', '.doc', '.md', '.txt', '.markdown'}
    
    @staticmethod
    def is_supported(filename: str) -> bool:
        """Check if file extension is supported."""
        ext = Path(filename).suffix.lower()
        return ext in DocumentProcessor.SUPPORTED_EXTENSIONS
    
    @staticmethod
    def extract_text(file_content: bytes, filename: str) -> str:
        """Extract text from file content based on file extension."""
        ext = Path(filename).suffix.lower()
        
        if ext == '.pdf':
            return DocumentProcessor._extract_from_pdf(file_content)
        elif ext in ['.docx', '.doc']:
            return DocumentProcessor._extract_from_docx(file_content)
        elif ext in ['.md', '.markdown']:
            return DocumentProcessor._extract_from_markdown(file_content)
        elif ext == '.txt':
            return file_content.decode('utf-8')
        else:
            raise ValueError(f"Unsupported file type: {ext}")
    
    @staticmethod
    def _extract_from_pdf(content: bytes) -> str:
        """Extract text from PDF file."""
        pdf_file = BytesIO(content)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = []
        for page in pdf_reader.pages:
            text.append(page.extract_text())
        return '\n'.join(text)
    
    @staticmethod
    def _extract_from_docx(content: bytes) -> str:
        """Extract text from DOCX file."""
        doc_file = BytesIO(content)
        doc = docx.Document(doc_file)
        paragraphs = [para.text for para in doc.paragraphs]
        return '\n'.join(paragraphs)
    
    @staticmethod
    def _extract_from_markdown(content: bytes) -> str:
        """Extract text from Markdown file."""
        md_text = content.decode('utf-8')
        # Convert markdown to plain text (remove formatting)
        html = markdown.markdown(md_text)
        # Simple HTML tag removal (for basic markdown)
        import re
        text = re.sub(r'<[^>]+>', '', html)
        return text
    
    @staticmethod
    def chunk_text(text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> List[Dict[str, any]]:
        """
        Split text into chunks with overlap.
        
        Args:
            text: Text to chunk
            chunk_size: Maximum size of each chunk in characters
            chunk_overlap: Number of characters to overlap between chunks
            
        Returns:
            List of dictionaries with 'text' and 'metadata' keys
        """
        if len(text) <= chunk_size:
            return [{'text': text, 'metadata': {'chunk_index': 0, 'start': 0, 'end': len(text)}}]
        
        chunks = []
        start = 0
        chunk_index = 0
        
        while start < len(text):
            end = start + chunk_size
            chunk_text = text[start:end]
            
            # Try to break at sentence boundary
            if end < len(text):
                # Look for sentence endings
                last_period = chunk_text.rfind('.')
                last_newline = chunk_text.rfind('\n')
                break_point = max(last_period, last_newline)
                
                if break_point > chunk_size * 0.5:  # Only break if we're past halfway
                    chunk_text = chunk_text[:break_point + 1]
                    end = start + break_point + 1
            
            chunks.append({
                'text': chunk_text.strip(),
                'metadata': {
                    'chunk_index': chunk_index,
                    'start': start,
                    'end': end
                }
            })
            
            start = end - chunk_overlap
            chunk_index += 1
        
        return chunks
