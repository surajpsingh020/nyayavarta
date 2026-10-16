# NYAYAVARTA PRODUCT REQUIREMENTS DOCUMENT

**An Explainable Multilingual AI Assistant for Indian Legal Case Retrieval, Analysis and Reasoning**

## Document Control
* **Document Version:** 1.0 — Final Baseline
* **Date:** 03 October 2026
* **Project Type:** College Major Project / Research Prototype
* **Architecture:** Freeware-first, CPU-first retrieval with optional GPU burst
* **Core Scope:** Indian judgments, statutes, explainable retrieval/reasoning, multilingual text + voice

*Academic-use notice: NyayaVarta is a legal research and information assistant. It is not a substitute for advice from a qualified legal professional and must surface sources and uncertainty.*

## 1. Product Vision & Objectives
NyayaVarta is a freeware-first Indian legal research assistant that converts user text, PDF and voice input into an evidence-grounded legal research response. Its core promise is not automated legal advice; it is fast retrieval, comparison and explanation of relevant Indian judgments and legal provisions with visible source citations.
* **Primary objective**: reduce the time required to discover and understand relevant Indian judgments and statutory provisions.
* **Research objective**: evaluate whether hybrid retrieval plus legal-structure-aware chunking, reranking and a citation-aware knowledge graph improves legal retrieval and answer faithfulness over baseline semantic RAG.
* **Accessibility objective**: accept Indian-language text/voice and return Indian-language text/voice using open Indic models where feasible.
* **Cost objective**: keep the core system runnable without paid APIs; optional cloud GPU/API services must be replaceable adapters, never hard dependencies.

## 2. Problem Statement
Legal professionals and students must read large collections of judgments, identify applicable provisions, locate similar precedents, compare arguments and understand court reasoning. Conventional keyword search can miss semantically similar cases, while generic chatbots can hallucinate statutes or citations. NyayaVarta addresses the discovery and synthesis problem by retrieving evidence first and asking the language model to explain only the retrieved evidence.

**Core user outcome**
Given a factual legal query or uploaded legal document, NyayaVarta should identify relevant Indian legal provisions and precedents, explain why they are relevant, surface supporting passages/citations, and state important uncertainties or missing facts.

## 3. Users & Use Cases
| User | Primary need | Example |
|---|---|---|
| Law student | Case research and precedent discovery | Find cases interpreting a provision. |
| Legal researcher | High-recall discovery across courts | Find semantically similar judgments from multiple courts. |
| Lawyer / advocate | Rapid issue spotting | Identify provisions, precedents and arguments for a new matter. |
| Citizen / self-represented | Plain-language legal information | Understand what laws/cases may be relevant. |
| Academic evaluator | Research benchmarking | Compare BM25, dense, hybrid, reranked and graph-enhanced retrieval. |

## 4. Product Scope
### 4.1 In Scope for Final-Year Baseline
* Text, PDF and voice input.
* Indian-language to English normalization for supported languages.
* Supreme Court and High Court judgment corpus plus statutes/Acts.
* Hybrid retrieval: BM25 + dense retrieval + metadata filtering + reranking.
* Legal-structure-aware document segmentation and chunking.
* Legal NER and structured extraction of cases, courts, judges, provisions, dates and legal issues.
* Knowledge graph for citation/follow/distinguish/apply/interprets relationships.
* Evidence-grounded RAG answer generation with source citations.
* Regional-language text and voice output.
* Offline evaluation and benchmark dashboard.

### 4.2 Optional Integrations
* Indian Kanoon API as an external/live retrieval or verification adapter, not the primary corpus.
* BHASHINI API as an external multilingual adapter for PoC/benchmarking.
* Modal as optional GPU burst infrastructure.

## 5. Functional Requirements
* **FR-01**: Accept plain text input in English or supported Indian languages. (P0)
* **FR-02**: Accept PDF uploads containing text or scans. (P0)
* **FR-03**: Accept voice input in supported Indian languages. (P0)
* **FR-04**: Translate/normalize input to English for the core legal pipeline. (P0)
* **FR-05**: Detect legal entities and issues. (P0)
* **FR-06**: Retrieve relevant cases using hybrid search. (P0)
* **FR-07**: Retrieve statutory provisions. (P0)
* **FR-08**: Rerank a reduced candidate set. (P0)
* **FR-09**: Maintain legal precedent/citation relationships. (P1)
* **FR-10**: Generate citation-grounded explanation. (P0)
* **FR-11**: Generate multilingual text output. (P0)
* **FR-12**: Generate voice output for supported languages. (P1)
* **FR-13**: Display uncertainty and limitations. (P0)
* **FR-14**: Provide document/source traceability. (P0)

## 6. User Experience & Output Contract
The output should prioritize evidence and reasoning structure rather than a single verdict-like sentence.
```text
NYAYAVARTA RESPONSE
Issue identified
Relevant legal provisions
Relevant judgments (ranked)
Why each judgment is relevant
Court reasoning / key passages
Arguments on each side (where available)
Important missing facts / caveats
Sources and citations
Research-use disclaimer
```
The product must not silently invent sections, case names, paragraph references, quotes or outcomes. When evidence is insufficient, it should say so.

## 7. Data & Source Strategy
The product uses a source hierarchy rather than treating every dataset as equally authoritative.
* **AWS Supreme Court**: Primary Supreme Court corpus (Yes for SC V1)
* **AWS High Courts**: Primary HC corpus (Yes for selected HC V1)
* **Kaggle SC dataset**: Rapid bootstrap / cross-check
* **HF Indian Court Decisions**: Scale-up / comparison / backfill
* **KanoonGPT Indian Case Laws**: Cross-check / backfill / research
* **Indian statutes/Acts**: Statutory grounding (Yes)

## 8. Non-Functional Requirements
* **Retrieval latency**: Target p95 <= 3 seconds for local hybrid retrieval on V1-scale corpus.
* **End-to-end response**: Target 10–25 seconds depending on local LLM/voice path.
* **Scalability**: V1 50K–100K judgments; V2 500K–1M.
* **Availability**: Local demo should run offline after models/corpus/indexes are installed.
* **Explainability**: Every substantive legal claim should map to one or more source passages.
* **Cost**: No mandatory paid API in the baseline build.

## 9. Safety, Legal & Trust Requirements
* The product is a legal research assistant, not an attorney and not a definitive legal-advice system.
* Avoid outcome-probability or “winner” language in the default UX.
* Surface jurisdiction, court, decision date and source provenance.
* Do not fabricate quotations or citations. Quote only retrieved source text.

## 10. Success Metrics
* **Recall@10 for relevant cases**: >= 0.80 on benchmark set
* **Citation accuracy**: >= 95% of cited sources exist and support the claim
* **Unsupported-claim rate**: <= 5% on benchmark set
* **CPU retrieval p95**: <= 3 s for V1 target hardware

## 11. MVP and Release Plan
* **V0 — Data**: SC corpus + statutes + schema + dedup
* **V1 — Search**: BM25 + dense retrieval + reranker
* **V1.1 — Reasoning**: RAG + citations + legal structure
* **V1.2 — Graph**: Neo4j legal relationship layer
* **V1.3 — Multilingual**: Indic ASR/MT/TTS
* **V2 — Scale**: Selected High Courts + 500K–1M corpus

## 12. Out of Scope / Future Work
* Fully autonomous legal representation or filing of court documents.
* Guaranteed judgment/outcome prediction for individual cases.
* Training a foundation LLM from scratch.
* Real-time indexing of all new judgments without source/licensing review.
* Commercial production guarantees or paid-user SLAs.

## 13. Acceptance Criteria
* A user can submit text, PDF or voice and receive a normalized English query.
* The system can retrieve and rank Indian legal sources from the local corpus.
* A generated response contains relevant provisions, cases, reasoning summary and citations when evidence exists.
* The system demonstrates lower retrieval latency than a full-corpus brute-force baseline.
* A multilingual text + voice round trip works for at least three Indian languages in the academic demo.
* The interface clearly displays the legal-research disclaimer and source provenance.
