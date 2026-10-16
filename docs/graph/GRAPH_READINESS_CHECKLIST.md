# Graph-Readiness Checklist (Milestone 4A.1 Gate)

**Date:** 2026-10-12  
**Milestone:** 4A.1 (Validation and Graph-Readiness Gate)  
**Target Milestone:** 4B (Graph Model & In-Memory / Neo4j Graph Foundation)  
**Status:** Audit Complete  

---

## 1. Readiness Assessment Matrix

| Area | Readiness Criterion | Verification Method | Status | Notes & Evidence |
| :--- | :--- | :--- | :---: | :--- |
| **1. Schema & Data Invariants** | Zero JSON parsing or schema format errors | Script `validate_extraction_jsonl.py` on all 175,784 records | **PASS** | 0 schema errors across all 3 JSONL files. |
| | Foreign Key Integrity: All resolved targets exist in corpus | Cross-checked 8,844 target doc IDs against 782 corpus files | **PASS** | 100% valid. 0 orphan target IDs. |
| | Ambiguous candidate valid keys | Cross-checked 472 candidate sets against corpus files | **PASS** | 100% valid. All candidate IDs exist. |
| | Status Invariant Enforced | Audited `resolved`, `ambiguous`, `unresolved` constraints | **PASS** | Zero invariant violations across corpus. |
| | Pipeline Output Determinism | Double-run SHA256 comparison on sample documents | **PASS** | 100% identical byte-for-byte SHA256 checksums. |
| **2. Citation Extraction** | Precision $\ge 90.0\%$ | Measured against 116 gold benchmark mentions | **PASS** | 92.92% precision across all citation types. |
| | Recall $\ge 85.0\%$ | Measured against 116 gold benchmark mentions | **PASS** | 90.52% recall across all citation types. |
| | Span Overlap Controlled | Overlapping span detection across 54,750 records | **CAUTION** | 2,318 overlapping span pairs found (neutral vs title). Fixed header prefix stripping. |
| | Deduplication Integrity | Exact duplicate check on `(doc, raw, span)` | **PASS** | Exactly 1 duplicate found in baseline; span deduplication added in `extract_all()`. |
| **3. Entity Resolution Quality** | Non-fabrication guarantee | Verified unresolved mentions have null target ID | **PASS** | 45,434 unresolved mentions (82.98%) strictly set `target_doc_id = null`. |
| | Target Document ID Accuracy $\ge 90\%$ | Strict ID matching against corrected gold sample | **PASS** | **94.74%** on all predicted resolved; **100.0%** when status correct. |
| | Cross-Era Collision Prevention | Tested temporal/title collisions | **RESTRICTION** | Title-only matching linked 2020 *Davinder Singh* to 2024 judgment. Needs year corroboration. |
| | Reporter Coverage Limitation | Audited SCR, SCC, AIR resolution paths | **RESTRICTION** | SCR citations (`[2024] X SCR Y`) cannot resolve because resolver lacks SCR volume-page index. |
| **4. Statutory Reference Modeling** | Bare Section Ambiguity Handling | Audited 5 bare sections (e.g. "Section 5", "Section 14") | **PASS** | 100% recall with `governing_statute = null`. No fabricated act links. |
| | Provision Extraction Accuracy | Evaluated on 55 gold statutory references | **PASS** | Precision: 98.00%, Recall: 89.09%, F1: 0.9333. |
| | Legal Disclaimers & Epistemology | Verified legal status warnings | **PASS** | Mentions modeled as textual references, not legal binding ratio. |
| **5. Graph Topology & Edge Viability** | Self-Citation Edge Loop Prevention | Flagged 8,184 self-citations out of 8,844 resolved | **RESTRICTION** | **92.54% of resolved citations are self-citations**. Must NOT become `CITES` graph edges. |
| | Cross-Document Graph Density | Counted cross-document links between 2024 judgments | **RESTRICTION** | Only 660 true cross-document links exist in the 782-doc 2024 corpus. |
| | Historical Dangling Node Strategy | Handled 45,434 unresolved historical citations | **RESTRICTION** | Must model historical precedents as stub nodes or exclude from path traversals. |

---

## 2. Final Recommendation

### Recommendation: **READY WITH DOCUMENTED RESTRICTIONS**

The extraction and resolution pipeline is mathematically deterministic, enforces 100% schema and foreign-key integrity, and demonstrates high empirical accuracy (92.9% citation precision, 98.0% statute precision, 94.7% target ID precision).

However, **direct, unrestricted conversion of extracted records into a Knowledge Graph will introduce severe graph modeling artifacts** (self-loops, disconnected historical dead-ends, and unanchored statutory edges). Therefore, Milestone 4B implementation MUST operate under the six documented architectural restrictions below.

---

## 3. Mandatory Restrictions for Milestone 4B Graph Implementation

### Restriction 1: Self-Citation Edge Exclusion (Zero Self-Loops)
- **Problem:** 8,184 out of 8,844 resolved citations (92.54%) are self-citations where a judgment mentions its own neutral citation, SCR volume, or case title in the header.
- **Rule:** Milestone 4B graph loader **MUST NOT** create directed `(:Judgment)-[:CITES]->(:Judgment)` edges where `source_doc_id == target_doc_id`.
- **Implementation:** Self-citations must be loaded as node properties on the Judgment node (e.g., `j.neutral_citation`, `j.scr_citation`), never as citation edges.

### Restriction 2: Dangling Historical Precedents Handling
- **Problem:** 45,434 citations (82.98%) cite pre-2024 decisions (1950–2023) outside the 2024 AWS corpus.
- **Rule:** The Knowledge Graph must distinguish internal closed-corpus edges from external historical references.
- **Implementation:** External citations must either:
  1. Be represented as lightweight external stub nodes: `(:Judgment)-[:CITES_HISTORICAL {reporter: "SCC", year: 1980}]->(:ExternalPrecedent {citation: "(1980) 1 SCC 81"})`, OR
  2. Be stored as string list properties on the Judgment node during initial prototype loading.
  Under no circumstances may unresolved citations be forced into 2024 target IDs.

### Restriction 3: Corroboration Guardrail for Title-Based Graph Edges
- **Problem:** Title-only keyword matching can create false cross-era links when a judgment refers to an earlier stage of a case (e.g., *State of Punjab v. Davinder Singh (2020) 8 SCC 1* matching the 2024 Constitution Bench judgment).
- **Rule:** A high-confidence `CITES` edge in Neo4j may only be formed if:
  1. Matched via exact Neutral Citation (`YYYY INSC N`), OR
  2. Matched via Title Overlap $\ge 0.85$ **AND** corroborated by year $\ge 2024$.
  Title-only matches lacking year corroboration must be flagged with `edge_confidence = "provisional"` or downgraded to `MENTIONS_NAME`.

### Restriction 4: Ambiguous Statutory Provision Edge Guardrail
- **Problem:** Judgments frequently cite bare sections (e.g., "Section 302", "Section 14", "Section 5") without attaching the governing Act in the same phrase.
- **Rule:** The graph loader **MUST NOT** create direct `(:Judgment)-[:INVOKES]->(:Act)` edges for sections where `governing_statute = null`.
- **Implementation:** Bare sections must be stored as `(:Judgment)-[:REFERENCES_SECTION {section_number: "5", governing_act: "UNSPECIFIED"}]->(:Section)` or disambiguated only when an explicit Act occurs in the immediate preceding paragraph.

### Restriction 5: Observational Epistemology for Statutory Graph Edges
- **Problem:** Mentioning an Act or Section in a judgment does not mean that provision governed the disposition or remains good law.
- **Rule:** Edges linking Judgments to Statutes must be named `[:MENTIONS_STATUTE]` or `[:CITES_SECTION]`.
- **Prohibited Edge Types:** Do not create edges named `[:GOVERNED_BY]`, `[:APPLIES_RATIO]`, or `[:VALID_LAW]` based purely on regex text extraction.

### Restriction 6: SCR Volume/Page Lookup Table Requirement
- **Problem:** SCR formal citations (`[2024] 10 S.C.R. 108`) represent 15.0% of all corpus citations (8,225 records) but currently fall through to `unresolved` because document IDs are based on pagination (`2024_10_108_125`) while the resolver only indexed `citation: "2024INSC735"`.
- **Requirement:** Before building cross-judgment citation edges based on SCR reporters, Milestone 4B must construct an SCR index mapping `(year, volume, start_page) -> document_id`.

---

## 4. Sign-Off Summary

| Role | Status | Sign-off Date |
| :--- | :---: | :---: |
| **Benchmark Provenance Auditor** | Verified & Disclosed | 2026-10-12 |
| **Entity Resolution Gate** | Passed (94.7% target accuracy) | 2026-10-12 |
| **JSONL Integrity Scanner** | Passed (100% foreign key validity, 0 broken invariants) | 2026-10-12 |
| **Statute Extractor Auditor** | Passed (98.0% precision, 89.1% recall) | 2026-10-12 |
| **Graph-Readiness Recommendation** | **READY WITH DOCUMENTED RESTRICTIONS** | 2026-10-12 |
