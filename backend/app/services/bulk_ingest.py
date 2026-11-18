"""
Automated Bulk Legal Ingestion Pipeline for Nyayavarta
Ingests court judgments, FIR reports, statutes, and legal PDFs/JSONs in bulk
directly into Neo4j Knowledge Graph and RAG index with zero manual Cypher queries.

Usage:
    python -m app.services.bulk_ingest --dir /path/to/legal_documents
    python -m app.services.bulk_ingest --json /path/to/statutes_or_cases.json
"""

import argparse
import json
import logging
import os
import re
import sys
import time
from typing import List, Tuple, Dict, Any

from app.config import get_settings
from app.services.rag_pipeline import RAGPipeline, extract_section_numbers

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("bulk_ingest")


def extract_text_from_pdf(file_path: str) -> List[Tuple[str, int]]:
    """Extract page text from a PDF file using PyMuPDF."""
    pages = []
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(file_path)
        for page_idx, page in enumerate(doc):
            text = page.get_text("text").strip()
            if text:
                pages.append((text, page_idx + 1))
        doc.close()
    except Exception as e:
        logger.error(f"PyMuPDF error reading {file_path}: {e}")
    return pages


def extract_text_from_docx(file_path: str) -> List[Tuple[str, int]]:
    """Extract text from DOCX file."""
    try:
        import docx
        doc = docx.Document(file_path)
        text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        return [(text.strip(), 1)] if text.strip() else []
    except Exception as e:
        logger.error(f"DOCX error reading {file_path}: {e}")
        return []


def extract_text_from_txt(file_path: str) -> List[Tuple[str, int]]:
    """Extract text from TXT file."""
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read().strip()
        return [(text, 1)] if text else []
    except Exception as e:
        logger.error(f"TXT error reading {file_path}: {e}")
        return []


def chunk_document_text(text: str, chunk_size: int = 500, chunk_overlap: int = 100) -> List[str]:
    """Break text into overlapping chunks respecting paragraph and sentence boundaries."""
    if not text or not text.strip():
        return []
    cleaned = re.sub(r"\r\n", "\n", text.strip())
    paragraphs = [p.strip() for p in cleaned.split("\n\n") if p.strip()]
    chunks = []
    current_chunk = []
    current_len = 0

    for para in paragraphs:
        if len(para) > chunk_size:
            sentences = re.split(r"(?<=[.!?।])\s+", para)
            for s in sentences:
                s_strip = s.strip()
                if not s_strip:
                    continue
                if current_len + len(s_strip) + 1 > chunk_size and current_chunk:
                    chunk_str = " ".join(current_chunk)
                    chunks.append(chunk_str)
                    overlap = chunk_str[-chunk_overlap:] if chunk_overlap > 0 else ""
                    current_chunk = [overlap, s_strip] if overlap else [s_strip]
                    current_len = sum(len(x) for x in current_chunk) + len(current_chunk) - 1
                else:
                    current_chunk.append(s_strip)
                    current_len += len(s_strip) + 1
        else:
            if current_len + len(para) + 2 > chunk_size and current_chunk:
                chunk_str = "\n".join(current_chunk)
                chunks.append(chunk_str)
                overlap = chunk_str[-chunk_overlap:] if chunk_overlap > 0 else ""
                current_chunk = [overlap, para] if overlap else [para]
                current_len = sum(len(x) for x in current_chunk) + len(current_chunk) - 1
            else:
                current_chunk.append(para)
                current_len += len(para) + 2

    if current_chunk:
        chunks.append("\n".join(current_chunk))
    return chunks


def ingest_directory(dir_path: str, rag: RAGPipeline, batch_size: int = 50) -> Dict[str, Any]:
    """Scan and ingest all PDF, DOCX, and TXT files in a directory."""
    if not os.path.exists(dir_path):
        logger.error(f"Directory not found: {dir_path}")
        return {"status": "error", "message": f"Directory not found: {dir_path}"}

    supported_exts = {".pdf", ".docx", ".doc", ".txt"}
    files_to_process = []
    for root, _, files in os.walk(dir_path):
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in supported_exts:
                files_to_process.append(os.path.join(root, f))

    logger.info(f"Found {len(files_to_process)} supported legal documents in '{dir_path}'.")

    total_chunks = 0
    total_files = 0
    start_time = time.time()

    for file_path in files_to_process:
        fname = os.path.basename(file_path)
        ext = os.path.splitext(fname)[1].lower()
        if ext == ".pdf":
            pages = extract_text_from_pdf(file_path)
        elif ext in [".docx", ".doc"]:
            pages = extract_text_from_docx(file_path)
        else:
            pages = extract_text_from_txt(file_path)

        if not pages:
            logger.warning(f"No extractable text in {fname}. Skipping.")
            continue

        file_chunks = []
        file_metas = []
        for page_text, page_num in pages:
            chunks = chunk_document_text(page_text)
            for c_idx, c_text in enumerate(chunks):
                file_chunks.append(c_text)
                file_metas.append({
                    "filename": fname,
                    "page": page_num,
                    "chunk_index": c_idx,
                    "source": "bulk_ingest",
                    "type": "user_document",
                })

        if file_chunks:
            rag.add_documents(file_chunks, file_metas)
            total_chunks += len(file_chunks)
            total_files += 1
            logger.info(f"Ingested '{fname}': {len(file_chunks)} chunks.")

    elapsed = round(time.time() - start_time, 2)
    logger.info(f"Bulk ingestion complete: {total_files} files, {total_chunks} chunks in {elapsed}s.")
    return {
        "status": "success",
        "files_processed": total_files,
        "chunks_indexed": total_chunks,
        "elapsed_seconds": elapsed,
    }


def ingest_json_data(json_path: str, rag: RAGPipeline) -> Dict[str, Any]:
    """Ingest structured statutory or case law data from a JSON file into Neo4j."""
    if not os.path.exists(json_path):
        logger.error(f"JSON file not found: {json_path}")
        return {"status": "error", "message": f"File not found: {json_path}"}

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    start_time = time.time()
    laws = data.get("laws", [])
    cases = data.get("cases", [])
    laws_ingested = 0
    cases_ingested = 0

    if laws:
        from app.services.rag_pipeline import parse_law_identifier, CYPHER_SEED_LAW
        for law in laws:
            old_id, old_act, old_sec = parse_law_identifier(law.get("old_law", ""))
            new_id, new_act, new_sec = parse_law_identifier(law.get("new_law", ""))
            rag.in_memory_graph.seed_law(
                old_id=old_id, old_sec_num=old_sec, old_act_code=old_act,
                new_id=new_id, new_sec_num=new_sec, new_act_code=new_act,
                subject=law.get("subject", ""),
                description=law.get("description", ""),
                key_changes=law.get("key_changes", "")
            )
            if rag.is_connected and rag.graph:
                try:
                    rag.graph.query(
                        CYPHER_SEED_LAW,
                        params={
                            "old_id": old_id, "old_sec_num": old_sec, "old_act_code": old_act,
                            "new_id": new_id, "new_sec_num": new_sec, "new_act_code": new_act,
                            "subject": law.get("subject", ""),
                            "description": law.get("description", ""),
                            "key_changes": law.get("key_changes", "")
                        }
                    )
                except Exception as e:
                    logger.debug(f"Law seed notice: {e}")
            laws_ingested += 1

    if cases and rag.is_connected and rag.graph:
        case_cypher = """
        UNWIND $cases AS c
        MERGE (court:Court {name: c.court})
        MERGE (case:CasePrecedent {citation: c.citation})
          SET case.neutral_citation = c.neutral_citation,
              case.title = c.title,
              case.year = c.year,
              case.bench = c.bench,
              case.headnote = c.headnote,
              case.ratio_decidendi = c.ratio_decidendi
        MERGE (case)-[:DECIDED_BY]->(court)
        FOREACH (sec_id IN c.applied_sections |
          MERGE (s:Section {id: sec_id})
          MERGE (case)-[:APPLIES_SECTION]->(s)
        )
        FOREACH (overruled_cit IN c.overruled_citations |
          MERGE (bad_case:CasePrecedent {citation: overruled_cit})
          MERGE (case)-[:OVERRULES]->(bad_case)
        )
        """
        try:
            rag.graph.query(case_cypher, params={"cases": cases})
            cases_ingested = len(cases)
        except Exception as e:
            logger.error(f"Error ingesting case precedents: {e}")

    elapsed = round(time.time() - start_time, 2)
    logger.info(f"JSON ingestion complete: {laws_ingested} laws, {cases_ingested} cases in {elapsed}s.")
    return {
        "status": "success",
        "laws_ingested": laws_ingested,
        "cases_ingested": cases_ingested,
        "elapsed_seconds": elapsed,
    }


def main():
    parser = argparse.ArgumentParser(description="Nyayavarta Automated Bulk Legal Ingestion Pipeline")
    parser.add_argument("--dir", help="Path to directory containing legal files (.pdf, .docx, .txt)")
    parser.add_argument("--json", help="Path to JSON file containing statutes or case law")
    args = parser.parse_args()

    if not args.dir and not args.json:
        parser.print_help()
        sys.exit(1)

    settings = get_settings()
    rag = RAGPipeline(settings)
    rag.initialize()

    if args.dir:
        ingest_directory(args.dir, rag)
    if args.json:
        ingest_json_data(args.json, rag)


if __name__ == "__main__":
    main()
