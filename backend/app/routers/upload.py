"""Document Ingestion Router (/api/upload) for Nyayavarta.

Extracts text from uploaded legal documents (PDF, DOCX, TXT),
chunks the content with overlap, and dynamically indexes chunks
into the hybrid RAG pipeline.
"""

import io
import logging
import os
import re
from typing import List, Tuple
from fastapi import APIRouter, File, HTTPException, Request, UploadFile, status

from app.models.schemas import UploadResponse

logger = logging.getLogger(__name__)

router = APIRouter()

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt"}


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent directory traversal and special character issues."""
    basename = os.path.basename(filename)
    clean_name = re.sub(r"[^\w\.-]", "_", basename)
    return clean_name or "uploaded_document"


def chunk_text(text: str, chunk_size: int = 500, chunk_overlap: int = 100) -> List[str]:
    """Split text into overlapping chunks respecting sentence/paragraph boundaries when possible."""
    if not text or not text.strip():
        return []

    cleaned_text = re.sub(r"\r\n", "\n", text.strip())
    cleaned_text = re.sub(r"\n{3,}", "\n\n", cleaned_text)

    # First attempt paragraph splitting
    paragraphs = [p.strip() for p in cleaned_text.split("\n\n") if p.strip()]
    chunks = []
    current_chunk = []
    current_len = 0

    for para in paragraphs:
        para_len = len(para)

        # If a single paragraph exceeds chunk size, split it into smaller sentences
        if para_len > chunk_size:
            sentences = re.split(r"(?<=[.!?।])\s+", para)
            for s in sentences:
                s_strip = s.strip()
                if not s_strip:
                    continue
                if current_len + len(s_strip) + 1 > chunk_size and current_chunk:
                    chunk_str = " ".join(current_chunk)
                    chunks.append(chunk_str)
                    # Keep overlap from previous sentences
                    overlap_tokens = chunk_str[-chunk_overlap:] if chunk_overlap > 0 else ""
                    current_chunk = [overlap_tokens, s_strip] if overlap_tokens else [s_strip]
                    current_len = sum(len(x) for x in current_chunk) + len(current_chunk) - 1
                else:
                    current_chunk.append(s_strip)
                    current_len += len(s_strip) + 1
        else:
            if current_len + para_len + 2 > chunk_size and current_chunk:
                chunk_str = "\n".join(current_chunk)
                chunks.append(chunk_str)
                # Overlap
                overlap_text = chunk_str[-chunk_overlap:] if chunk_overlap > 0 else ""
                current_chunk = [overlap_text, para] if overlap_text else [para]
                current_len = sum(len(x) for x in current_chunk) + len(current_chunk) - 1
            else:
                current_chunk.append(para)
                current_len += para_len + 2

    if current_chunk:
        chunk_str = "\n".join([c for c in current_chunk if c.strip()])
        if chunk_str.strip():
            chunks.append(chunk_str.strip())

    return chunks if chunks else [cleaned_text]


def extract_text_from_pdf(content: bytes, filename: str) -> List[Tuple[str, int]]:
    """Extract text from PDF byte content page by page using PyMuPDF (fitz).

    Returns a list of (page_text, page_number) tuples.
    """
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(stream=content, filetype="pdf")
        pages_text = []
        for page_idx in range(len(doc)):
            page = doc[page_idx]
            text = page.get_text()
            if text and text.strip():
                pages_text.append((text.strip(), page_idx + 1))
        doc.close()
        return pages_text
    except Exception as e:
        logger.error(f"PyMuPDF extraction failed for {filename}: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to parse PDF document: {str(e)}"
        )


def extract_text_from_docx(content: bytes, filename: str) -> List[Tuple[str, int]]:
    """Extract text from DOCX byte content using python-docx.

    Returns a list of (text, page_number) tuples (single pseudo-page for docx).
    """
    try:
        import docx
        doc = docx.Document(io.BytesIO(content))
        full_text = []

        for para in doc.paragraphs:
            if para.text.strip():
                full_text.append(para.text.strip())

        for table in doc.tables:
            for row in table.rows:
                row_text = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                if row_text:
                    full_text.append(" | ".join(row_text))

        combined_text = "\n\n".join(full_text)
        if not combined_text.strip():
            return []
        return [(combined_text, 1)]
    except Exception as e:
        logger.error(f"python-docx extraction failed for {filename}: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to parse Word document: {str(e)}"
        )


def extract_text_from_txt(content: bytes) -> List[Tuple[str, int]]:
    """Extract text from plain text byte content."""
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        text = content.decode("latin-1", errors="replace")
    return [(text.strip(), 1)] if text.strip() else []


@router.post("/upload", response_model=UploadResponse, summary="Ingest legal document into RAG knowledge base")
async def upload_document(request: Request, file: UploadFile = File(...)):
    """Upload legal document (PDF, DOCX, TXT), extract text, chunk, and index into Hybrid RAG."""
    # 1. Validate file extension
    orig_filename = file.filename or "uploaded_file"
    ext = os.path.splitext(orig_filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{ext}'. Allowed formats: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    # 2. Read and validate file size
    settings = getattr(request.app.state, "settings", None)
    max_mb = getattr(settings, "MAX_FILE_SIZE_MB", 20) if settings else 20
    max_bytes = max_mb * 1024 * 1024

    content = await file.read()
    if not content or len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty."
        )

    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum allowed size of {max_mb} MB."
        )

    safe_name = sanitize_filename(orig_filename)

    # 3. Save copy to upload directory
    upload_dir = getattr(settings, "UPLOAD_DIR", "uploads") if settings else "uploads"
    os.makedirs(upload_dir, exist_ok=True)
    save_path = os.path.join(upload_dir, safe_name)
    try:
        with open(save_path, "wb") as f:
            f.write(content)
    except Exception as e:
        logger.warning(f"Could not write file to {save_path}: {e}")

    # 4. Extract text per page
    if ext == ".pdf":
        pages = extract_text_from_pdf(content, safe_name)
    elif ext in [".docx", ".doc"]:
        pages = extract_text_from_docx(content, safe_name)
    else:
        pages = extract_text_from_txt(content)

    if not pages:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No readable text found in document."
        )

    # 5. Chunk text
    chunk_size = getattr(settings, "CHUNK_SIZE", 500) if settings else 500
    chunk_overlap = getattr(settings, "CHUNK_OVERLAP", 100) if settings else 100

    all_chunks: List[str] = []
    all_metadatas: List[dict] = []

    for page_text, page_num in pages:
        page_chunks = chunk_text(page_text, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        for chunk_idx, chunk in enumerate(page_chunks):
            if chunk.strip():
                all_chunks.append(chunk.strip())
                all_metadatas.append({
                    "filename": safe_name,
                    "page": page_num,
                    "chunk_index": chunk_idx,
                    "source": "upload",
                    "type": "user_document"
                })

    if not all_chunks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document text was too short to produce valid search chunks."
        )

    # 6. Index into RAG pipeline
    rag_pipeline = getattr(request.app.state, "rag_pipeline", None)
    if rag_pipeline:
        try:
            rag_pipeline.add_documents(all_chunks, all_metadatas)
            logger.info(f"Indexed {len(all_chunks)} chunks from {safe_name} into RAG pipeline.")
        except Exception as e:
            logger.error(f"Error indexing chunks into RAG pipeline: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to index document chunks into RAG pipeline: {str(e)}"
            )

    return UploadResponse(
        filename=safe_name,
        chunks_created=len(all_chunks),
        message=f"Successfully extracted and indexed {len(all_chunks)} chunks from '{safe_name}'."
    )
