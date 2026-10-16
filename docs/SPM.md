# NYAYAVARTA SOFTWARE PROJECT MANAGEMENT PLAN (SPM)

**24-week final-year project plan for an explainable multilingual Indian legal AI assistant**

## Document Control
* **Document Version:** 1.0 — Final Baseline
* **Date:** 03 October 2026

## 1. Project Charter
* **Project**: NyayaVarta — AI Legal Assistant for Case Reasoning
* **Duration**: 24 weeks
* **Primary outcome**: Working research prototype + benchmark + academic report
* **Core corpus**: Indian Supreme Court + selected High Courts + statutes
* **Primary research question**: Does hybrid, legal-structure-aware retrieval with reranking and a knowledge graph improve Indian legal RAG quality and explainability over simpler baselines?

## 2. Goals, Deliverables & Definition of Done
### 2.1 Deliverables
* PRD, TRD and SPM documents.
* Clean and versioned Indian legal corpus for the project scope.
* ETL and indexing pipeline.
* Hybrid retrieval engine with benchmark.
* Legal knowledge graph.
* Evidence-grounded RAG/reasoning engine.
* Multilingual text and voice interface.
* Evaluation dataset, scripts, results and ablation study.
* Working web demo, final report, presentation and deployment instructions.

### 2.2 Definition of Done
* Code runs from documented setup steps on a clean development environment.
* Corpus/index versions are reproducible from manifests.
* Every demo answer can be traced to source documents.
* Benchmark metrics are produced automatically.
* No core dependency requires a paid API.

## 3. Team & Responsibilities
* **Project Lead / PM**: Scope, schedule, integration, reviews
* **Data Engineer**: Dataset acquisition, normalization, dedup, provenance
* **NLP/IR Engineer**: NER, embeddings, BM25, reranking, benchmarks
* **Graph/RAG Engineer**: Knowledge graph, evidence builder, reasoning prompts
* **Full-stack/ML Ops**: FastAPI, UI, model serving, deployment, monitoring

## 4. Work Breakdown Structure
* **1.0 Project initiation**: Requirements, scope, legal/safety boundaries, environment setup
* **2.0 Data acquisition**: AWS SC, AWS HC, Kaggle bootstrap, HF supplements, statutes, licenses
* **3.0 Data engineering**: Extraction, normalization, deduplication, schema, version manifests
* **4.0 Legal NLP**: NER, section detection, legal-structure segmentation, glossary
* **5.0 Retrieval**: BM25, dense embeddings, ANN, fusion, reranker
* **6.0 Knowledge graph**: Entity mapping, relationship extraction, graph queries
* **7.0 RAG/reasoning**: Evidence builder, grounded prompts, citations, uncertainty
* **8.0 Multilingual/voice**: IndicTrans2, IndicConformer, IndicF5; optional BHASHINI adapter
* **9.0 Application**: FastAPI, web UI, upload/voice UX, source viewer
* **10.0 Evaluation**: Gold queries, retrieval metrics, RAG audits, ablations, latency benchmarks
* **11.0 Deployment**: Local packaging, reproducible setup
* **12.0 Academic delivery**: Report, poster, demo script, presentation, viva preparation

## 5. 24-Week Schedule
* **Weeks 1–2**: Initiation & architecture (Gate 1)
* **Weeks 3–4**: Dataset acquisition (Gate 2)
* **Weeks 5–6**: Data engineering (Gate 3)
* **Weeks 7–8**: Baseline retrieval (Gate 4)
* **Weeks 9–10**: Hybrid retrieval (Gate 5)
* **Weeks 11–12**: Reranker + segmentation (Gate 6)
* **Weeks 13–14**: Knowledge graph (Gate 7)
* **Weeks 15–16**: RAG/reasoning (Gate 8)
* **Weeks 17–18**: Multilingual text (Gate 9)
* **Weeks 19–20**: Voice + UI (Gate 10)
* **Weeks 21–22**: Evaluation & optimization (Gate 11)
* **Weeks 23**: Hardening (Gate 12)
* **Weeks 24**: Final delivery (Gate 13)

## 6. Milestones & Gate Reviews
* **G1**: PRD/TRD approved; success metrics fixed.
* **G2**: At least one canonical corpus + statutes + license records.
* **G3**: One-command/batch reproducible ETL on sample.
* **G4**: BM25/dense baseline benchmark exists.
* **G5**: Benchmark compares lexical/dense/hybrid.
* **G6**: Ablation result documented.
* **G7**: At least 3 supported graph query types.
* **G8**: Citation audit meets threshold.
* **G9**: Three-language text round trip succeeds.
* **G10**: Voice input/output demo succeeds in three languages.
* **G11**: Latency/memory benchmark documented.
* **G12**: Clean-machine setup walkthrough passes.
* **G13**: Demo, report, benchmark and limitations complete.

## 7. Effort & Resource Plan
* **Development PC**: 16–32 GB RAM, SSD 250–500+ GB free
* **Software**: Python, PyTorch, Hugging Face, FAISS, SQLite, DuckDB, Neo4j, FastAPI, React/Next.js

## 8. Risk Register
* **Dataset overlap**: Canonical source IDs + content hashes (Mitigation)
* **CPU latency**: Hierarchical retrieval, ANN, metadata filtering
* **LLM hallucination**: Evidence-only prompt + citation validator + audit
* **Translation drift**: Legal glossary + terminology tests
* **Scope creep**: Freeze scope at research assistant; defer advanced modules

## 9. Quality Management
* Every dataset addition has source, version, license and provenance metadata.
* Every release is rendered and manually tested across text/PDF/voice flows.

## 10. Research & Evaluation Plan
* E1 Retrieval: Hybrid BM25 + dense vs BM25
* E2 Chunking: Legal-structure chunks vs Fixed token chunks
* E3 Ranking: Hybrid + reranker vs Hybrid without reranker
* E4 Graph: RAG + KG evidence vs RAG only
* E5 Language: Indic input/output vs English only
* E6 Scale: 500K/1M corpus vs 100K corpus
