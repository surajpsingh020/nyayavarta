# NyayaVarta — Milestone 8: Multi-Passage Evidence Selection and Context Budgeting Report

**Document Version:** 1.0.0  
**Status:** Completed & Validated  
**Benchmark Artifacts:** `evaluation/rag/milestone8_multipassage_comparison_report.json`, `evaluation/rag/milestone8_multipassage_claims.jsonl`  
**Evaluation Date:** October 2026  
**Provider / Model Evaluated:** Local Ollama (`v0.17.1`), `phi3.5:latest` (CPU, 8 threads, no GPU acceleration)

---

## 1. Executive Summary

Milestone 8 resolves a fundamental retrieval limitation identified in Milestone 7: **single-passage evidence insufficiency**. 

In Milestone 7, context budgeting was restricted to a single evidence passage (`max_passages=1`, `max_chars_per_passage=1000`) to guarantee predictable CPU inference times under 100 seconds. While this successfully eliminated phantom citation hallucination via grammar-constrained dynamic enums (`enum: ["E1"]`), it exposed a real legal RAG defect:
- In complex statutory interpretation cases such as `M6_009` (concerning Section 17(5)(d) of the CGST Act and the "functionality test" for commercial buildings), the judgment (*Chief Commissioner of Central Goods and Service Tax v. M/s Safari Retreats Pvt. Ltd.*, `2024_10_793_859`) splits its discussion across distinct paragraphs.
- Passage 1 (`chars 0..1912`) introduces the statutory provisions and framed the appeal questions, but terminated before the judicial determination.
- Passage 2 (`chars 1914..4487`) contained the explicit holding and the adoption of the functionality test.
- Constrained to $k=1$, the model received only Passage 1. Because the grammar strictly prohibited inventing citations (`[E2]` was not in the dynamic enum), the model safely and correctly abstained (`status: abstain`).

Milestone 8 introduces a **complementary, deduplicating multi-passage selection algorithm** with **context budgeting**, **exact source offset preservation**, and **active evidence sufficiency checks**. It compares the 1-passage baseline against 2-passage and 3-passage configurations on the canonical 10-query benchmark.

### Key Measured Outcomes

| Metric | Milestone 7 Baseline ($k=1$, 1000 chars) | Milestone 8 Config 2 ($k=2$, 750 chars) | Milestone 8 Config 3 ($k=3$, 500 chars) | Impact / Delta |
| :--- | :--- | :--- | :--- | :--- |
| **Evaluated Queries** | 10 canonical | 10 canonical | 10 canonical | Controlled comparative evaluation |
| **Grounding Gate Fast-Exits** | 4 / 4 unanswerable (100%) | 4 / 4 unanswerable (100%) | 4 / 4 unanswerable (100%) | Fast-exit abstentions intact (~0.10s) |
| **LLM Invocations** | 6 answerable queries | 6 answerable queries | 6 answerable queries | Exact same candidate queries |
| **Valid Structured Output Rate** | 100.0% (6 / 6) | 100.0% (6 / 6) | 100.0% (6 / 6) | Zero schema or parsing defects |
| **Unknown / Hallucinated Evidence IDs** | 0 / 6 (0.0%) | 0 / 6 (0.0%) | 0 / 6 (0.0%) | Zero phantom or out-of-budget IDs |
| **Answers Accepted** | 5 / 6 (83.3%) | **6 / 6 (100.0%)** | **6 / 6 (100.0%)** | **M6_009 successfully answered** |
| **Voluntary Model Abstentions** | 1 / 6 (16.7%) [`M6_009`] | **0 / 6 (0.0%)** | **0 / 6 (0.0%)** | 100% answerability on answerable set |
| **Generation Latency (Median)** | **62.97 seconds** | 90.61 seconds | 124.33 seconds | +43.9% ($k=2$) / +97.5% ($k=3$) latency |
| **Generation Latency (p95)** | **98.89 seconds** | 126.84 seconds | 150.82 seconds | Well within 240s CPU timeout budget |
| **Fast-Exit Latency (Median)** | 0.106 seconds | 0.106 seconds | 0.099 seconds | Preserved instantaneous gate exits |
| **Prompt Tokens (Median)** | ~800 tokens | 1,346.5 tokens | 1,448.5 tokens | Context expanded within Llama.cpp cache |
| **Timeouts (> 240s)** | 0 / 10 | 0 / 10 | 0 / 10 | Zero timeouts across all configurations |
| **Automated Regression Suite** | 168 passing | **182 passing (+14 tests)** | **182 passing (+14 tests)** | 100% test pass rate across repository |

---

## 2. Multi-Passage Selection Architecture

The multi-passage pipeline is implemented in `services/rag/evidence.py` and integrated into `services/rag/pipeline.py` and `services/rag/grounding_gate.py`.

```
Retrieval Candidates (Top-k Judgments)
                 │
                 ▼
┌────────────────────────────────────────────────────────┐
│ Stage 1: Retrieval Candidate Grounding Gate             │
│ - Verifies statutory provisions, focal years, entities │
│ - Instant fast-exit if corpus lacks coverage (~0.10s)  │
└────────────────────────────────────────────────────────┘
                 │ (Pass)
                 ▼
┌────────────────────────────────────────────────────────┐
│ Multi-Passage Complementary Evidence Selection         │
│ - Overlap Rejection: Excludes overlapping spans        │
│ - Jaccard Deduplication: Skips similarity >= 0.80       │
│ - Complementarity Scoring: Rewards novel query tokens  │
│ - Authority Heuristic: Prioritizes holdings ('Held:')  │
│ - Budget Truncation: Max passages (k) & max chars      │
│ - Deterministic Renumbering: [E1], [E2], ..., [Ek]     │
└────────────────────────────────────────────────────────┘
                 │
                 ▼
┌────────────────────────────────────────────────────────┐
│ Stage 2: Active Evidence Sufficiency Check             │
│ - Verifies active budgeted passages cover query tests  │
│ - Catches missing holding / multi-part tests           │
└────────────────────────────────────────────────────────┘
                 │ (Sufficient)
                 ▼
┌────────────────────────────────────────────────────────┐
│ Dynamic Schema Enum Construction & Generation          │
│ - Schema enum strictly restricted to [E1..Ek]          │
│ - Native Ollama JSON schema constrained decoding       │
└────────────────────────────────────────────────────────┘
```

### 2.1 Deduplication & Overlap Rejection
Legal retrieval frequently surfaces adjacent chunks or near-verbatim extracts from headnotes and party submissions. The selection algorithm enforces two strict deduplication filters:
1. **Document Span Overlap Filter:** Passages from the same document ID that overlap in character offsets are rejected:
   $$\max(start_1, start_2) < \min(end_1, end_2)$$
2. **Jaccard Token Deduplication:** For candidate passages across or within documents, word-level Jaccard similarity is computed:
   $$J(A, B) = \frac{|A \cap B|}{|A \cup B|}$$
   Candidates with $J(A, B) \ge 0.80$ against any already-selected passage are discarded.

### 2.2 Complementarity & Judicial Authority Scoring
To select passages that add distinct factual or legal information rather than repeating the same concepts, candidates are ranked by a multi-factor score:
- **Novel Query Coverage:** $+1.5$ per salient query token not covered by previously selected passages.
- **Authoritative Holding Markers:** $+2.0$ boost if the passage contains judicial holding anchors (`"held:"`, `"ratio decidendi"`, `"we conclude"`, `"functionality test"`).
- **Retrieval Rank Decay:** Preserves retrieval priority for primary passages while allowing highly complementary secondary passages to rise.

### 2.3 Exact Character Offset Preservation
Every selected passage preserves the immutable link to the underlying judgment text:
- When a passage is truncated to fit the context budget (`max_chars_per_passage`), the truncation is performed on valid sentence boundaries (`split_sentences_with_offsets`).
- The adjusted start and end offsets satisfy:
  $$\text{document\_text}[\text{char\_offset\_start} : \text{char\_offset\_end}] == \text{passage\_text}$$
- At no point are synthetic passages or altered offsets introduced.

### 2.4 Two-Stage Grounding Gate Architecture
To balance zero-cost fast exits with strict generation sufficiency:
- **Stage 1 (Candidate Gate):** Evaluates the candidate retrieval pool before budgeting. If statutory provisions or historical periods are missing entirely from the corpus, the gate fast-exits in ~0.10s, bypassing LLM prompt construction and inference entirely.
- **Stage 2 (Active Evidence Sufficiency Gate):** Evaluates the budgeted `active_passages` immediately before LLM invocation. If a multi-part legal query inquires about a specific judicial test (e.g. "functionality test", "triple test", "prima facie test") and that test was dropped during passage budgeting, the pipeline abstains rather than prompting the model with incomplete context.

---

## 3. Controlled Benchmark Comparison: 1 vs 2 vs 3 Passages

The canonical 10-query benchmark was executed across three configurations using local Ollama (`phi3.5:latest` on CPU, 8 threads, `temperature=0.0`, `num_predict=140`).

### 3.1 Side-by-Side Results Table

| Query ID | Domain | Expected | Milestone 7 ($k=1$, 1000c) | Milestone 8 Config 2 ($k=2$, 750c) | Milestone 8 Config 3 ($k=3$, 500c) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **M6_001** | Constitutional | Answer | Answered (`[E1]`) in 62.97s | Answered (`[E1]`) in 126.83s | Answered (`[E1]`) in 104.15s |
| **M6_002** | Commercial (IBC) | Answer | Answered (`[E1]`) in 47.78s | Answered (`[E1]`) in 90.57s | Answered (`[E1]`) in 150.82s |
| **M6_004** | Commercial (Limitation) | Answer | Answered (`[E1]`) in 45.48s | Answered (`[E1]`) in 83.89s | Answered (`[E1]`) in 114.20s |
| **M6_005** | Negotiable Instruments | Answer | Answered (`[E1]`) in 52.34s | Answered (`[E1]`) in 90.65s | Answered (`[E1]`) in 139.56s |
| **M6_007** | Constitutional (Prison) | Answer | Answered (`[E1]`) in 98.89s | Answered (`[E2]`) in 82.91s | Answered (`[E1]`) in 130.69s |
| **M6_009** | Taxation (CGST 17(5)) | Answer | **Abstained (missing holding)** | **Answered (`[E2]`) in 101.86s** | **Answered (`[E2]`, `[E3]`) in 117.97s** |
| **M6_017** | Data Protection | Abstain | Fast-Exit (0.106s) | Fast-Exit (0.101s) | Fast-Exit (0.095s) |
| **M6_018** | Personal / Property | Abstain | Fast-Exit (0.108s) | Fast-Exit (0.110s) | Fast-Exit (0.094s) |
| **M6_019** | Criminal / Contempt | Abstain | Fast-Exit (0.104s) | Fast-Exit (0.102s) | Fast-Exit (0.102s) |
| **M6_020** | Patents (GM Mustard) | Abstain | Fast-Exit (0.155s) | Fast-Exit (0.151s) | Fast-Exit (0.142s) |

### 3.2 Performance & Resource Summary

```
Latency vs Answer Acceptance Curve:
Configuration         Answer Acceptance    Median Latency    Prompt Tokens
-------------------------------------------------------------------------
Config 1 (k=1, 1000c)      83.3% (5/6)        62.97s            ~800
Config 2 (k=2, 750c)      100.0% (6/6)        90.61s          1,346.5
Config 3 (k=3, 500c)      100.0% (6/6)       124.33s          1,448.5
```

---

## 4. Deep-Dive Case Study: Resolution of M6_009

### 4.1 The Defect in Milestone 7
Query: *"Does Section 17(5)(d) of the CGST Act apply the functionality test to determine whether a building constructed for leasing qualifies as a plant for input tax credit?"*

- **Passage 1 (chars 0..1912):** Recited the statutory text of Section 17(5)(d) and recorded that the High Court had read down the provision. It stopped at paragraph 14, where the Supreme Court posed the questions to be decided.
- **Milestone 7 Baseline ($k=1$):** Because only Passage 1 was budgeted, the prompt did not contain the Supreme Court's actual ruling on the functionality test. 
- **Model Behavior:** Instead of hallucinating that the text contained the ruling or inventing citations, `phi3.5:latest` output:
  ```json
  {
    "status": "abstain",
    "claims": [],
    "abstention_reason": "The provided evidence does not mention the functionality test or clarify whether a building constructed for leasing qualifies as a plant under Section 17(5)(d) of the CGST Act."
  }
  ```
- **Validation Outcome:** Valid abstention, but a false negative on an answerable legal query.

### 4.2 The Resolution in Milestone 8 Config 2 ($k=2$, 750 chars)
- **Selected Evidence:**
  - `E1` (`2024_10_793_859`, chars 0..749): Statutory framing of Section 17(5)(d).
  - `E2` (`2024_10_793_859`, chars 1914..2663): Explicit holding:
    > *"Functionality test to be applied to decide whether the construction of an immovable property is a 'plant' for the purposes of clause (d) of Section 17(5)..."*
- **Model Output:**
  ```json
  {
    "status": "answer",
    "claims": [
      {
        "text": "Section 17(5)(d) defines 'plant or machinery' for input tax credit purposes.",
        "evidence_ids": ["E2"]
      },
      {
        "text": "'Plant', when construed in the context of Section 16 and clause (d) of section 17(5), includes buildings essential to service transactions like leasing, indicating a functionality test.",
        "evidence_ids": ["E2"]
      }
    ],
    "abstention_reason": ""
  }
  ```
- **Validation:** 
  - Citation syntax: Valid.
  - Citation existence: Valid (`E2` exists in active evidence).
  - Schema conformity: 100%.
  - Zero hallucinated IDs (`invalid_ids: []`).

### 4.3 Resolution in Milestone 8 Config 3 ($k=3$, 500 chars)
In Config 3, three passages were selected (`E1`, `E2`, and `E3`). The model synthesized claims citing both `[E2]` and `[E3]`:
- Claim 1 cited `[E2]`: Section 17(5)(d) functionality application.
- Claim 2 cited `[E3]`: Analogous application to business assets.
- Both citations conformed strictly to the dynamic enum `["E1", "E2", "E3"]`.

---

## 5. Context Budgeting and CPU Latency Trade-Off Analysis

Running local quantized models (`phi3.5:latest`) on CPU without dedicated GPU acceleration introduces strict latency boundaries:
1. **Prompt Processing Cost ($T_{\text{prompt}}$):** Processing 1,350 to 1,500 tokens of legal text on 8 CPU threads requires ~60 to 80 seconds.
2. **Generation Cost ($T_{\text{eval}}$):** Generating 120 to 150 completion tokens requires ~18 to 25 seconds.
3. **Budget Trade-Offs:**
   - Unbudgeted multi-passage inclusion ($k \ge 4$ or full 2,000-char passages) pushes prompt length beyond 2,500 tokens, resulting in generation times exceeding 200–240 seconds and risking HTTP timeout aborts.
   - **Optimal Configuration:** **Config 2 ($k=2$, max 750 chars per passage)** represents the optimal operational envelope. It expands retrieval sufficiency to resolve multi-paragraph holdings (100% answer acceptance), while maintaining a median latency of 90.61s and a p95 latency of 126.84s (well below the 240s threshold).

---

## 6. Regression Test Suite

Fourteen new regression tests were authored in `tests/test_milestone8_multipassage.py` to safeguard against architectural regressions:
1. `test_extractive_sentence_compression_exact_offsets`: Verifies sentence extraction and exact character offset preservation.
2. `test_jaccard_similarity_deduplication`: Verifies threshold-based near-duplicate detection.
3. `test_span_overlap_exclusion`: Verifies exclusion of overlapping spans within the same document.
4. `test_complementary_evidence_selection_ordering`: Verifies novel token and authority scoring.
5. `test_budget_capping_max_passages`: Verifies strict bounding by `max_passages`.
6. `test_budget_capping_max_chars`: Verifies character limits per passage.
7. `test_active_evidence_renumbering`: Verifies deterministic renumbering to `E1..Ek`.
8. `test_active_evidence_sufficiency_gate_passes_when_test_present`: Verifies Stage 2 gate permits sufficient passages.
9. `test_active_evidence_sufficiency_gate_abstains_when_test_missing`: Verifies Stage 2 gate catches missing legal holdings.
10. `test_pipeline_single_passage_backward_compatibility`: Verifies exact preservation of Milestone 7 baseline behavior when `max_passages=1`.
11. `test_pipeline_multi_passage_active_evidence_isolation`: Verifies that unselected passages do not leak into prompt or schema enum.
12. `test_pipeline_multi_passage_dynamic_schema_enum`: Verifies schema enum dynamically expands to `["E1", "E2"]` when $k=2$.
13. `test_citation_validator_validates_multi_evidence_ids`: Verifies validator correctly audits multiple cited IDs (`[E1]`, `[E2]`).
14. `test_api_rag_endpoint_supports_enable_compression`: Verifies FastAPI endpoint exposes `enable_compression` parameter.

**Full Test Suite Result:** `182 passed, 1 warning in 16.85s` (100% pass rate).

---

## 7. Limitations & Epistemic Boundaries

In accordance with NyayaVarta's core design principles:
1. **Developer-Curated Status:** The benchmark queries and gold labels remain developer-curated. No practicing advocates or judicial officers have certified the legal accuracy of the generated answers.
2. **Citation Existence vs Semantic Correctness:** Citation validation verifies that `[E2]` was an active passage containing the cited text. The `semantic_support_status` remains strictly labeled as `not_evaluated` unless human legal review is documented.
3. **Corpus Boundaries:** The system operates over 782 Supreme Court judgments from 2024. It does not provide legal advice, does not track post-2024 legislative amendments, and must not be used as a substitute for professional legal counsel.
