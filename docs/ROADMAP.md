# NyayaVarta Implementation Roadmap

This roadmap outlines the 24-week delivery plan defined in the SPM.

## Phase 1: Initiation & Data Foundation (Weeks 1-6)
- [x] **Milestone 0**: Repository setup, PRD/TRD/SPM, skeleton code, test infrastructure, Docker configs.
- [ ] **Milestone 1**: Dataset acquisition (AWS SC, Kaggle bootstrap, statutes).
- [ ] **Milestone 2**: Data engineering (canonical schema, deduplication pipeline, ETL scripts).

## Phase 2: Core Retrieval & Graph (Weeks 7-14)
- [ ] **Milestone 3**: Baseline BM25 retrieval.
- [ ] **Milestone 4**: Hybrid retrieval (BM25 + FAISS Dense).
- [ ] **Milestone 5**: Reranker + legal structure chunking.
- [ ] **Milestone 6**: Knowledge Graph construction (citations, precedents).

## Phase 3: Reasoning, Multilingual & UX (Weeks 15-20)
- [ ] **Milestone 7**: RAG/Reasoning engine (evidence-first generation).
- [ ] **Milestone 8**: Multilingual text (IndicTrans2) and Glossary.
- [ ] **Milestone 9**: Voice input/output (IndicConformer, IndicF5).
- [ ] **Milestone 10**: Frontend web application & API integration.

## Phase 4: Evaluation & Final Delivery (Weeks 21-24)
- [ ] **Milestone 11**: Evaluation, optimization, and ablations (Latency + Quality benchmarks).
- [ ] **Milestone 12**: Hardening, bug fixes, reproducibility testing.
- [ ] **Milestone 13**: Final academic delivery (Report, presentation, demo).
