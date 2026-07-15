"""
Document Chunker

Extracts text from uploaded documents (PDF, Word, plain text) and splits it
into overlapping chunks with source metadata preserved per chunk.

Why chunk documents?
- LLMs have finite context windows. A 50-page PDF won't fit in a single prompt.
- Embedding models produce better representations for short, focused passages
  than for entire documents (semantic similarity degrades with length).
- Retrieval works by finding the *most relevant* chunk, not the most relevant
  document — finer granularity means more precise answers.

Why overlap between chunks?
- A sentence that spans a chunk boundary would be split in half without overlap.
  50-token overlap means the tail of chunk N is the head of chunk N+1, so
  cross-boundary information is preserved in at least one chunk.

Each chunk carries metadata:
- document_id: links back to the Document ORM record
- document_name: human-readable filename
- page_number: for PDFs (null for Word/text)
- chunk_index: position within the document (for ordering in citations)
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from langchain.text_splitter import RecursiveCharacterTextSplitter


@dataclass
class DocumentChunk:
    """A single chunk of text with its source metadata."""
    text: str
    document_id: int
    document_name: str
    chunk_index: int
    page_number: Optional[int] = None
    metadata: dict = field(default_factory=dict)


# Default chunking parameters
CHUNK_SIZE = 500  # ~500 characters ≈ ~100-125 tokens
CHUNK_OVERLAP = 50  # Overlap to preserve cross-boundary context


def extract_and_chunk(
    file_path: Path,
    file_type: str,
    document_id: int,
    document_name: str,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
) -> list[DocumentChunk]:
    """
    Extract text from a file and split into overlapping chunks with metadata.

    Args:
        file_path: Path to the document on disk
        file_type: One of "pdf", "word", "text"
        document_id: The Document record ID (for linking chunks back)
        document_name: Human-readable filename
        chunk_size: Target size of each chunk in characters
        chunk_overlap: Overlap between consecutive chunks in characters

    Returns:
        List of DocumentChunk objects ready for embedding

    Raises:
        ValueError: If file type is not supported for text extraction
    """
    if file_type == "pdf":
        pages = _extract_pdf_pages(file_path)
        return _chunk_pages(pages, document_id, document_name, chunk_size, chunk_overlap)
    elif file_type == "word":
        text = _extract_word_text(file_path)
        return _chunk_plain_text(text, document_id, document_name, chunk_size, chunk_overlap)
    elif file_type == "text":
        text = _extract_plain_text(file_path)
        return _chunk_plain_text(text, document_id, document_name, chunk_size, chunk_overlap)
    else:
        raise ValueError(
            f"Cannot extract text from '{file_type}' files for RAG. "
            "Supported: pdf, word, text."
        )


def _extract_pdf_pages(file_path: Path) -> list[tuple[int, str]]:
    """
    Extract text per page from a PDF.

    Returns: List of (page_number, text) tuples.
    """
    from pypdf import PdfReader

    reader = PdfReader(str(file_path))
    pages = []
    for i, page in enumerate(reader.pages, start=1):
        text = page.extract_text()
        if text and text.strip():
            pages.append((i, text.strip()))
    return pages


def _extract_word_text(file_path: Path) -> str:
    """Extract all text from a Word (.docx) document."""
    from docx import Document as DocxDocument

    doc = DocxDocument(str(file_path))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n\n".join(paragraphs)


def _extract_plain_text(file_path: Path) -> str:
    """Read a plain text file."""
    try:
        return file_path.read_text(encoding="utf-8").strip()
    except UnicodeDecodeError:
        return file_path.read_text(encoding="latin-1").strip()


def _chunk_pages(
    pages: list[tuple[int, str]],
    document_id: int,
    document_name: str,
    chunk_size: int,
    chunk_overlap: int,
) -> list[DocumentChunk]:
    """
    Split PDF pages into chunks, preserving page number metadata.

    Each page is split independently so chunks don't span page boundaries.
    This makes citations more precise ("page 3" not "pages 3-4").
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunks: list[DocumentChunk] = []
    chunk_index = 0

    for page_num, page_text in pages:
        page_chunks = splitter.split_text(page_text)
        for text in page_chunks:
            if text.strip():
                chunks.append(DocumentChunk(
                    text=text.strip(),
                    document_id=document_id,
                    document_name=document_name,
                    chunk_index=chunk_index,
                    page_number=page_num,
                ))
                chunk_index += 1

    return chunks


def _chunk_plain_text(
    text: str,
    document_id: int,
    document_name: str,
    chunk_size: int,
    chunk_overlap: int,
) -> list[DocumentChunk]:
    """Split plain text (Word or .txt) into chunks."""
    if not text.strip():
        return []

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    text_chunks = splitter.split_text(text)
    chunks: list[DocumentChunk] = []

    for i, chunk_text in enumerate(text_chunks):
        if chunk_text.strip():
            chunks.append(DocumentChunk(
                text=chunk_text.strip(),
                document_id=document_id,
                document_name=document_name,
                chunk_index=i,
                page_number=None,
            ))

    return chunks
