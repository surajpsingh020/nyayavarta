# NYAYAVARTA TECHNICAL REQUIREMENTS & DESIGN DOCUMENT

**Freeware-first CPU retrieval, local legal corpus, graph-enhanced RAG and multilingual input/output**

## Document Control
* **Document Version:** 1.0 — Final Baseline
* **Date:** 03 October 2026
* **Project Type:** College Major Project / Research Prototype

## 1. Technical Goals & Design Principles
* **Local-first**: the core system must operate without commercial APIs.
* **CPU-first retrieval**: disk-resident corpus and ANN/full-text indexes; no full-corpus scan per query.
* **Evidence-first generation**: retrieval and source traceability precede LLM generation.
* **Modularity**: ASR, translation, TTS, embeddings, LLM and external services are adapters behind stable interfaces.
* **Legal structure-aware**: preserve facts, issues, arguments, provisions, precedent discussion and holding/decision sections.
* **Reproducible research**: version every corpus, preprocessing pipeline, index and model configuration.

## 2. System Architecture
```text
CLIENTS
 Web UI / Mobile Web / CLI
 |
 v
API GATEWAY (FastAPI)
 |
 +--> Input Service ----> PDF/OCR / ASR / Language ID / Translation
 |
 +--> Query Analyzer --> legal entities + issue + jurisdiction + date
 |
 +--> Retrieval Orchestrator
 |    |--> SQLite FTS5 / BM25
 |    |--> FAISS / ANN
 |    |--> Metadata filter (DuckDB/SQLite)
 |    |--> Reranker
 |
 +--> Evidence Builder
 |    |--> Neo4j knowledge graph
 |    |--> legal passage store
 |
 +--> RAG / Reasoning Engine --> local LLM
 |
 +--> Output Service --> translation --> TTS
 |
 +--> Observability / evaluation

STORAGE
 Raw archives | Parquet | SQLite | FAISS | Neo4j | model cache
```

## 3. Input Processing
* **Text**: Language ID -> IndicTrans2 if non-English -> normalized English query
* **PDF with text**: PyMuPDF -> page-aware text extraction -> language ID -> translation if needed
* **Scanned PDF**: PDF -> OCRmyPDF/Tesseract or transformer OCR -> text -> language ID -> translation
* **Voice**: IndicConformer ASR -> text -> language ID -> IndicTrans2

## 4. Legal Data Engineering
### 4.1 Canonical document schema
```
document_id, source_id, court, court_level, case_title,
case_number, citation, decision_date, judges, parties,
legal_domain, language, source_url, license,
full_text, facts, issues, petitioner_arguments,
respondent_arguments, evidence, legal_provisions,
precedents, court_reasoning, decision, disposition,
content_hash, ingestion_version, index_version
```

### 4.2 Ingestion pipeline
```text
RAW -> extract -> normalize -> de-duplicate -> metadata validate
    -> legal-structure segment -> chunk -> persist -> embed -> index
```

## 5. Retrieval Architecture
### 5.1 Candidate generation
```text
QUERY
 -> metadata filter (court/year/domain where known)
 -> BM25 candidate set (e.g. top 200–500)
 -> dense ANN candidate set (e.g. top 100–200)
 -> score fusion
 -> cross-encoder reranking of top 30–50
 -> evidence selection top 5–10 cases / passages
```

### 5.2 Vector indexing strategy
* Use document-level embeddings for broad case retrieval; avoid creating vectors for every paragraph across the full corpus in V1.
* After top cases are identified, perform passage-level retrieval inside those cases or in a smaller passage index.
* Use FAISS CPU ANN (HNSW/IVF-style approach as benchmarked) for the dense index.
* Start with a compact 384-dimension embedding model.

## 6. Knowledge Graph
### 6.1 Nodes
* Case, Court, Judge, Party, Statute, Section, Article, Legal concept, Issue

### 6.2 Edges
* `CASE -[:CITES]-> CASE`
* `CASE -[:FOLLOWS]-> CASE`
* `CASE -[:DISTINGUISHES]-> CASE`
* `CASE -[:OVERRULES]-> CASE`
* `CASE -[:APPLIES]-> PROVISION`
* `CASE -[:INTERPRETS]-> PROVISION`
* `CASE -[:DECIDED_BY]-> JUDGE`
* `CASE -[:HAS_ISSUE]-> ISSUE`

## 7. RAG & Reasoning
* SYSTEM PROMPT (conceptual):
  1. Use only retrieved evidence for factual legal claims.
  2. Cite every material legal proposition.
  3. Separate facts, law, precedent, reasoning and uncertainty.
  4. If evidence is missing or conflicting, say so.
  5. Do not invent quotations, sections, case names or citations.
  6. Present as legal research assistance, not legal advice.

## 8. Multilingual & Voice Stack
* **Language identification**: fastText / compact Indic language ID
* **Indian-language -> English**: IndicTrans2
* **Speech -> text**: IndicConformer
* **English -> Indian language**: IndicTrans2
* **Text -> speech**: IndicF5 / Indic-TTS

## 9. Storage, Indexing & Compute Strategy
* Recommended storage: `data/raw/`, `data/parquet/`, `data/sqlite/`, `data/faiss/`, `data/neo4j/`, `models/`, `evaluation/`, `manifests/`.
* CPU: retrieval, metadata filtering, BM25, index persistence, Neo4j and most ETL.
* GPU optional: translation/ASR/TTS/embeddings/LLM when faster inference is needed.

## 10. API & Service Contracts
* `POST /v1/input/text` - Normalize text query
* `POST /v1/input/pdf` - Extract and normalize PDF
* `POST /v1/input/voice` - ASR + normalization
* `POST /v1/retrieve` - Hybrid legal retrieval
* `POST /v1/analyze` - Grounded reasoning
* `POST /v1/respond` - Full user response
* `GET /v1/cases/{id}` - Source retrieval
* `GET /v1/health` - Service health

## 11. Security & Privacy
* Treat uploaded PDFs and audio as untrusted files; sandbox parsing and enforce file-size/type/time limits.
* Do not send uploaded documents to external APIs by default.
* Store session identifiers separately from content; apply configurable retention.

## 12. Recommended Repository Layout
```text
nyayavarta/
 apps/
  web/
  api/
 services/
  input/
  retrieval/
  graph/
  reasoning/
  language/
 data/
  raw/
  processed/
  indexes/
 models/
 evaluation/
  queries/
  gold/
  reports/
 scripts/
  ingest/
  index/
  benchmark/
 docs/
```
