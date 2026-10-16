# Legal Citation and Entity Extraction Design (Milestone 4A)

This document specifies the technical design, patterns, normalization rules, and architectural constraints for NyayaVarta's CPU-first legal citation and entity extraction pipeline.

---

## 1. Architectural Principles & Scope

The citation and entity extraction subsystem serves as the deterministic bridge between raw judgment text and structured legal knowledge graphs (Milestone 4B). In accordance with NyayaVarta's core constraints:

1. **CPU-Only & Zero Commercial Dependencies:** Runs purely using deterministic regular expression automata, rule-based tokenizers, and in-memory hash indexes.
2. **Conservative Entity Resolution:** Mentions are mapped to existing corpus documents only when supported by unambiguous identifiers (neutral citations, exact volume/page, or high-confidence title similarity). Historical precedents (e.g. 1950–2023) are explicitly tagged as `unresolved` rather than fabricated or hallucinated into false matches.
3. **No Inference of Binding Precedent:** A textual citation mention is an observational reference; the extraction system does not assert that a citation creates binding precedent or that an extracted statute governs the case.
4. **Source Provenance & Immutability:** Raw corpus files under `data/processed/aws_sc/` remain untouched. Extraction outputs are written as versioned JSONL datasets under `data/processed/extraction/v1/`.

```
                    ┌───────────────────────────┐
                    │ Raw Full Text of Judgment │
                    └─────────────┬─────────────┘
                                  │
          ┌───────────────────────┴───────────────────────┐
          ▼                                               ▼
┌────────────────────────────┐              ┌───────────────────────────┐
│     CitationExtractor      │              │     StatuteExtractor      │
│  - Neutral Citations (INSC)│              │  - Acts / Statutes        │
│  - Reporter Citations      │              │  - Sections / Subsections │
│    (SCC, SCC OnLine, SCR)  │              │  - Articles (Constitution)│
│  - AIR Citations           │              │  - Procedural Orders/Rules│
│  - Case Names (X v. Y)     │              │  - Constitutional Sched.  │
│  - Unanchored Mentions     │              └─────────────┬─────────────┘
└─────────────┬──────────────┘                            │
              │                                           ▼
              ▼                             ┌───────────────────────────┐
┌────────────────────────────┐              │ statutory_references.jsonl│
│       EntityResolver       │              └───────────────────────────┘
│  - Neutral Citation Index  │
│  - Title Overlap Matching  │
│  - Pre-2024 Historical Flg │
│  - Resolution States:      │
│    * resolved              │
│    * ambiguous             │
│    * unresolved            │
└─────────────┬──────────────┘
              │
      ┌───────┴───────┐
      ▼               ▼
┌─────────────┐ ┌─────────────────────────┐
│case_cites   │ │resolved_entities.jsonl  │
│.jsonl       │ └─────────────────────────┘
└─────────────┘
```

---

## 2. Citation Patterns & Regular Expression Specifications

### 2.1 Formal Law Reporters

| Reporter | Canonical Form | Regex Pattern | Example in Text | Normalized Form |
|---|---|---|---|---|
| **Neutral (INSC)** | `YYYY INSC N` | `\b(?P<year>(?:19\|20)\d{2})\s*INSC\s*(?P<num>\d+)\b` | `2024 INSC 735` | `2024INSC735` |
| **Supreme Court Reports (SCR)** | `[YYYY] Vol SCR Page` | `\[?(?P<year>(?:19\|20)\d{2})\]?\s*(?:\((?P<part>\d+)\)\s*)?(?P<vol>\d+)?\s*S\.?C\.?R\.?\s*(?P<page>\d+)\b` | `[2024] 10 S.C.R. 108` | `[2024] 10 SCR 108` |
| **Supreme Court Cases (SCC)** | `(YYYY) Vol SCC Page` | `(?:\((?P<year>\d{4})\)\|\[(?P<year_sq>\d{4})\]\|(?P<year_plain>\d{4}))\s+(?:(?P<vol>\d+)\s+)?SCC(?:\s*\((?P<subpart>Cri\|L&S\|Civ)\))?\s+(?P<page>\d+)\b` | `(2019) 14 SCC 81` | `(2019) 14 SCC 81` |
| **SCC OnLine** | `YYYY SCC OnLine SC N` | `\b(?P<year>\d{4})\s+SCC\s+OnLine\s+(?P<court>[A-Za-z]+)\s+(?P<num>\d+)\b` | `2024 SCC OnLine SC 1796`| `2024 SCC OnLine SC 1796` |
| **All India Reporter (AIR)** | `AIR YYYY SC Page` | `\bAIR\s+(?P<year>\d{4})\s+(?P<court>SC\|Supreme\s+Court)\s+(?:\(Supp\)\s+)?(?P<page>\d+)\b` | `AIR 1978 SC 597` | `AIR 1978 SC 597` |

### 2.2 Case Name Patterns (Party v. Party)
- **Regex:** `\b(?P<party1>[A-Z][A-Za-z0-9\.\,\'\s\(\)\@\-\&]{2,60}?)\s+(?P<v>v\.|vs\.?|versus)\s+(?P<party2>[A-Z][A-Za-z0-9\.\,\'\s\(\)\@\-\&]{2,60}?)`
- **Filtering Guardrails:** Disallows single letters, numeric strings, and procedural statutory keywords (e.g., `Section`, `Order`, `Rule`, `Sub-section`, `Clause`).
- **Alias Normalization:** Strips alias markers (e.g., `@ VIJAY KR. SHARMA`).

### 2.3 Unanchored Case References
- **Pattern:** `(?:in the case of|as held in|decision in|judgment in|view taken in|ratio in)\s+(?P<case_name>[A-Z][A-Za-z0-9\.\,\'\s\(\)\@\-]{3,60}?)`
- **Confidence Rating:** Assigned `low` confidence to prevent over-weighting in downstream graph assembly.

### 2.4 Treatment / Observational Signal Detection
Detects immediate lexical signals indicating how a cited judgment was treated:
- Signals: `followed`, `referred to`, `relied upon`, `distinguished`, `held inapplicable`, `overruled`, `approved`, `cited`.

---

## 3. Statutory Reference Patterns

### 3.1 Acts & Statutes
- **Formal Acts with Year:** `[A-Z][A-Za-z\s\(\)\'\-]{2,50}?(?:Act|Code|Rules|Regulations|Order),\s*(?:18|19|20)\d{2}`  
  *Example:* `Indian Penal Code, 1860`, `Limitation Act, 1963`.
- **Preposition Stripping:** Strips leading grammatical noise (e.g., `Under the Indian Penal Code` $\to$ `Indian Penal Code`).
- **Canonical Acronym Resolution:**
  - `IPC` $\to$ `Indian Penal Code, 1860`
  - `CrPC` $\to$ `Code of Criminal Procedure, 1973`
  - `CPC` $\to$ `Code of Civil Procedure, 1908`
  - `PMLA` $\to$ `Prevention of Money Laundering Act, 2002`
  - `IBC` $\to$ `Insolvency and Bankruptcy Code, 2016`
  - `NI Act` $\to$ `Negotiable Instruments Act, 1881`
  - `POCSO` $\to$ `Protection of Children from Sexual Offences Act, 2012`
  - `SARFAESI` $\to$ `Securitisation and Reconstruction of Financial Assets and Enforcement of Security Interest Act, 2002`

### 3.2 Sections, Subsections & Articles
- **Sections:** `(?:Sections?|Sec\.|s\.|u/ss?\.?|under Section)\s+\d+[A-Za-z]*(?:\([0-9a-zA-Z]+\))*(?:/\d+)*`  
  Captures compound sections (`Section 302/34`, `Section 45(1)(ii)`), multiple provisions (`Sections 302 and 120-B`), and shorthand (`u/s 438`).
- **Articles of the Constitution:** `(?:Article|Articles|Art\.)\s+\d+[A-Za-z]*(?:\([0-9a-zA-Z]+\))*`  
  *Example:* `Article 21`, `Article 142`, `Articles 14, 15 and 21`.
- **Procedural Orders & Rules:** `(?:Order\s+[IVXLCDM0-9]+\s+Rule\s+\d+[A-Za-z]*|Rule\s+\d+[A-Za-z]*(?:\([0-9a-zA-Z]+\))*)`  
  *Example:* `Order XXI Rule 99`, `Rule 9(4)`.
- **Schedules:** `(?:First|Second|...|Tenth|Eleventh|Twelfth)\s+Schedule`  
  *Example:* `Tenth Schedule`.

---

## 4. Conservative Entity Resolution Design

Entity resolution resolves extracted citation mentions against the 782 canonical judgments in `data/processed/aws_sc/`.

### Resolution Hierarchy:
1. **Tier 1: Exact Neutral Citation Matching**
   - Matches mention normalized key (e.g. `2024INSC735`) against the corpus neutral citation hash map.
   - If matched: `resolved` (Confidence: 1.0).
   - If neutral key is not found: `unresolved`.
2. **Tier 2: Historical Reporter Cutoff**
   - For SCC, AIR, and SCR citations where the publication year $< 2024$, the target is mathematically guaranteed not to exist in the 2024 Supreme Court corpus.
   - Categorized as `unresolved` (Match method: `historical_reporter_pre_2024`).
3. **Tier 3: Case Title Token Overlap Matching**
   - Strips legal boilerplate (`versus`, aliases `@`, registry numbers).
   - Extracts distinguishing party keywords.
   - Computes keyword overlap and Jaccard similarity.
   - If single candidate has overlap $\ge 0.80$: `resolved`.
   - If multiple candidates tie within $0.05$ similarity (e.g. multiple related appeals titled `State of M.P. v. ...`): explicitly flagged as `ambiguous` with candidate IDs recorded.
   - If overlap $< 0.80$: `unresolved`.

---

## 5. Storage Schemas (`data/processed/extraction/v1/`)

### 5.1 Case Citations Schema (`case_citations.jsonl`)
```json
{
  "source_doc_id": "string",
  "citation_type": "neutral_insc | scc | scc_online | scr | air | case_title | unanchored_mention",
  "raw_text": "string",
  "normalized_citation": "string",
  "components": {
    "year": "integer (optional)",
    "volume": "integer (optional)",
    "page": "integer (optional)",
    "court": "string (optional)",
    "party1": "string (optional)",
    "party2": "string (optional)"
  },
  "start_char": "integer",
  "end_char": "integer",
  "mention_context": "string",
  "treatment_signal": "string (optional)",
  "extraction_method": "string",
  "confidence": "high | medium | low",
  "version": "1.0.0",
  "provenance": "string"
}
```

### 5.2 Statutory References Schema (`statutory_references.jsonl`)
```json
{
  "source_doc_id": "string",
  "reference_type": "statute_act | statutory_section | constitutional_article | procedural_order_rule | statutory_schedule",
  "raw_text": "string",
  "normalized_reference": "string",
  "components": {
    "act_title": "string (optional)",
    "section_numbers": "string (optional)",
    "articles": "array of strings (optional)",
    "order": "string (optional)",
    "rule": "string (optional)",
    "schedule_name": "string (optional)"
  },
  "start_char": "integer",
  "end_char": "integer",
  "mention_context": "string",
  "extraction_method": "string",
  "confidence": "high | medium",
  "version": "1.0.0",
  "provenance": "string"
}
```

### 5.3 Resolved Entities Schema (`resolved_entities.jsonl`)
```json
{
  "source_doc_id": "string",
  "mention_raw": "string",
  "mention_normalized": "string",
  "resolution_status": "resolved | ambiguous | unresolved",
  "resolved_document_id": "string | null",
  "ambiguous_candidate_ids": "array of strings (optional)",
  "matched_case_title": "string | null",
  "match_method": "string",
  "confidence_score": "float",
  "is_self_citation": "boolean",
  "version": "1.0.0",
  "provenance": "string"
}
```
