# NyayaVarta (न्यायवार्ता)

**An Explainable, Evidence-Grounded Legal Research and Reasoning Assistant for Indian Supreme Court Judgments**

[![Test Suite](https://img.shields.io/badge/Tests-386%20Passed-brightgreen)](tests/)
[![Legal Review Status](https://img.shields.io/badge/Release%20Gate-HOLD%20(Pending%20Review)-orange)](docs/FINAL_PROJECT_READINESS.md)
[![Academic Status](https://img.shields.io/badge/College%20Demo-READY-blue)](docs/FINAL_PROJECT_READINESS.md)

---

## 1. Overview

NyayaVarta is an artificial intelligence research platform developed to investigate evidence-grounded legal question answering over the Supreme Court of India judgments (2024 SCR corpus). 

The platform addresses the critical risks of large language models in legal research—namely hallucinated citations, inverted doctrinal holdings, and false acceptance of ungrounded legal claims—through a multi-layered verification architecture, fail-closed abstention gating, and an answer-level safety contract.

> [!IMPORTANT]
> **Formal Legal Release Gate: HOLD (PENDING_EXTERNAL_REVIEW)**  
> NyayaVarta is technically validated for educational and academic college project demonstration. It has not received independent certification from qualified legal practitioners and is **NOT AUTHORIZED FOR REAL-WORLD LEGAL PRACTICE OR CLIENT ADVICE**.

> [!NOTE]
> **Implementation Scope & Roadmap**:  
> The current repository implements the complete FastAPI backend, hybrid retrieval engine, verified RAG answer pipeline, and React + TypeScript legal research web client.
> - **Frontend (`apps/web`)**: Fully implemented React 18 + TypeScript + Vite legal research interface (Phase 2A); provides interactive query execution, audit presets, verification badge rendering, and clickable citation linking.
> - **Roadmap Features**: PDF document upload (FR-02), voice transcription/ASR (FR-03), multilingual translation (FR-01/FR-04), and text-to-speech (FR-12) are roadmap items specified in [`docs/PRD.md`](docs/PRD.md) and are not yet implemented.

---

## 2. Key Capabilities & Safety Invariants

1. **Hybrid Retrieval**: Dense vector embeddings (BGE-Base-en-v1.5) combined with lexical BM25 over 782 Supreme Court judgments.
2. **Proposition Grounding Gate**: Rejects unanswerable or out-of-corpus queries prior to LLM generation, ensuring clean system abstentions.
3. **Exact Offset Evidence Verification**: Validates all cited passages against exact character boundaries `[start_char:end_char]` of the raw judgment corpus (`data/processed/aws_sc/`).
4. **Hardened Claim Verification (Policy 3)**:
   - Polarity and negation contradiction checks.
   - Procedural submission vs. operative holding discrimination.
   - Auxiliary ONNX NLI contradiction veto (`cross-encoder/nli-deberta-v3-small` running on CPU).
5. **Centralized Answer-Level Safety Badges**:
   - `verified_supported`: Every assertion verified by direct judicial authority.
   - `qualified_answer`: Claims verified with noted statutory exceptions or provisos.
   - `unverified_answer`: Valid syntax/citations, but unverified legal semantics.
   - `rejected_answer`: Contradicted, ungrounded, or hallucinated claims suppressed.
   - `insufficient_evidence`: Clean system abstention.

---

## 3. Architecture

```
nyayavarta/
├── apps/
│   ├── api/                  # FastAPI REST service (/v1/rag/query, /v1/health)
│   └── web/                  # Next.js/React research UI skeleton & safety contract
├── services/
│   ├── retrieval/            # BM25, Dense Retriever, Reranker
│   ├── extraction/           # Citation extractor, entity resolver, statute parser
│   ├── graph/                # Knowledge graph construction & retrieval
│   └── rag/                  # Core RAG pipeline, evidence assembler, claim verifier
├── data/
│   ├── processed/aws_sc/     # 782 canonical 2024 Supreme Court judgments (42 MB)
│   └── indexes/              # BM25 and FAISS dense indexes (rebuilt locally)
├── evaluation/
│   └── rag/                  # Frozen benchmarks (M6–M25), audit manifests
├── docs/                     # Technical specifications, PRD, milestone reports
├── scripts/
│   └── benchmark/            # Verification, audit, and benchmark scripts
└── tests/                    # 386 passing automated unit, integration, and safety tests
```

---

## 4. Quick Start & Setup

### Prerequisites
- Python 3.10–3.13 (Tested on Python 3.13)
- [Ollama](https://ollama.com/) (Optional: required only for live LLM generation; mock provider requires 0 downloads)

### 1. Virtual Environment Setup
```bash
# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\activate      # Windows
source venv/bin/activate    # Linux / macOS

# Install all backend, testing, and indexing dependencies
pip install -r requirements.txt
```

### 2. Initialize Search Indexes
```bash
# Build local BM25 and FAISS search indexes from canonical corpus
python scripts/index/index_bm25.py
python scripts/index/index_dense.py
```

### 3. Run the Complete Test Suite
```bash
# Execute all 386 regression and safety tests (100% passing)
pytest tests/ -q
```

### 4. Run the Safety Audit Benchmark
```bash
# Verify 22 adversarial cases and non-mutation of all historical benchmarks
python scripts/benchmark/run_milestone24_safety_audit.py
```

### 5. Run the 5 Canonical End-to-End Demo Queries
```bash
# Executes 5 canonical queries across both mock and live local Ollama models
python scripts/benchmark/verify_e2e_demo_queries.py
```

### 6. Launch the REST API Server
```bash
uvicorn apps.api.main:app --host 127.0.0.1 --port 8000 --reload
```
Interactive API documentation will be available at `http://127.0.0.1:8000/docs`.

### 7. Launch the Web Frontend Client
```bash
cd apps/web
npm install
npm run dev
```
Open `http://localhost:5173` in your browser. (To run frontend test suite: `npm test`; to build for production: `npm run build`).

---

## 5. College Project Demonstration Guide

For technical evaluation and project demonstration, five canonical query classes showcase the system's capabilities:

| Scenario | Query | Expected System Outcome |
|:---|:---|:---|
| **1. Supported Holding** | *Can selection criteria be altered after recruitment has commenced under High Court rules?* | Grounds on *Tej Prakash Pathak* (`2024_12_28_67`). Badge: `verified_supported`. |
| **2. Missing Proviso** | *Can the authorized officer extend the 15-day balance deposit without borrower consent under SARFAESI?* | Detects missing consent condition. Badge: `qualified_answer` (`answered_with_qualification`). |
| **3. Contradicted Rule** | *Are seeds and biological processes patentable under Section 3(j) Patents Act?* | Direct statutory contradiction. Badge: `rejected_answer` / `insufficient_evidence`. |
| **4. Out-of-Corpus** | *What is the limitation period for admiralty arrest under Admiralty Act, 2017?* | Clean grounding gate abstention: `insufficient_evidence`. Zero hallucinations. |
| **5. Fail-Closed Error** | *Provider timeout / HTTP 504 simulation* | Fail-closed exception handling. Badge: `system_error`. Zero ungrounded text leaks. |

> [!TIP]
> **Demo Latency Recommendation**:  
> - Use `provider_type="mock"` or `provider_type="mock_partial"` for instantaneous (<500ms) UI demonstration of grounding, citation linking, and badge generation.  
> - Use `provider_type="ollama"` (`llama3.2:1b`) to showcase real local autoregressive generation on CPU and witness the hallucination filter in action.

---

## 6. Audit & Readiness Artifacts

- [GITHUB_PREPARATION_AUDIT.md](docs/GITHUB_PREPARATION_AUDIT.md) — Pre-cleanup repository inventory, sizing, and GitHub staging review.
- [FINAL_PROJECT_READINESS.md](docs/FINAL_PROJECT_READINESS.md) — Comprehensive technical audit and release gate certification.
- [FINAL_REVIEW_PACK_AUDIT.md](docs/FINAL_REVIEW_PACK_AUDIT.md) — Provenance analysis of all 30 Milestone 25 review pack cases and V2 corrections.
- [MILESTONE_25_REVIEW_PROTOCOL.md](docs/MILESTONE_25_REVIEW_PROTOCOL.md) — Protocol and guidelines for independent human legal evaluation.
- [MILESTONE_24_SINGLE_CLAIM_SAFETY.md](docs/MILESTONE_24_SINGLE_CLAIM_SAFETY.md) — Single-claim vulnerability mitigation and adversarial fail-closed audit.

---

## 7. License & Disclaimer

NyayaVarta is released under the MIT License for educational and academic research purposes. The judgments analyzed are public records of the Supreme Court of India.
