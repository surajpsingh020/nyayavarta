# NyayaVarta Architecture

This document describes the high-level architecture of NyayaVarta, an explainable multilingual AI assistant for Indian legal case retrieval.

## System Overview
- **Frontend (Web):** A React/Next.js application providing the user interface for text, PDF, and voice inputs.
- **API Gateway:** A FastAPI service handling requests and orchestrating underlying services.
- **Services:**
  - `input`: Processes text, PDFs, OCR, and voice ASR.
  - `retrieval`: Orchestrates candidate generation via BM25 (SQLite FTS5) and dense embeddings (FAISS), followed by cross-encoder reranking.
  - `graph`: Manages legal knowledge relationships (citations, outcomes) via Neo4j.
  - `reasoning`: Prepares evidence for LLMs and formulates RAG prompts.
  - `language`: Handles translation to/from Indian languages via IndicTrans2/IndicConformer.
- **Data & Storage:** Organized into raw, processed, and index forms using Parquet, SQLite, FAISS, and Neo4j.

## Core Principles
- Local-first and CPU-first for retrieval.
- Modular adapter-based external integrations.
- Evidence-grounded generation.
