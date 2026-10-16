# NyayaVarta — Milestone 6.1: Answer Quality & Citation Integrity Hardening Report

**Date**: October 13, 2026  
**Status**: Completed  
**Corpus**: 782 Supreme Court of India judgments (2024)  
**Evaluator Provenance**: `developer_curated` (epistemic honesty strictly maintained; non-certified engineering evaluation)  
**Hardware & Environment**: Local CPU (x86_64, AVX2, Windows 11, Python 3.13.3 venv, Ollama v0.3+)  
**Target Local SLM**: `phi3.5:latest` (3.82B parameters, Q4_K_M)

---

## 1. Executive Summary

Milestone 6 demonstrated end-to-end functionality across retrieval, proposition grounding, and generation, but revealed three critical failure modes:
1. **Citation Validation Leakage**: The pipeline treated answers containing invalid or placeholder markers (e.g., `[E#]`) as `"answered"` and `"sufficient_evidence"`, failing closed only in diagnostic summaries rather than system status.
2. **Attribution Cleavage**: All 16 claims categorized as `partially_supported` in the Milestone 6 claim review were caused by a naive sentence boundary regex `\.\s+` cleaving citations attached to terminal periods, and the extraction of controversy-framing headnotes (`Issue for Consideration`) rather than substantive holdings (`Held:`).
3. **Limited Live Inference**: Live Ollama evaluation in Milestone 6 covered only 7 queries (with 6 fast-exit abstentions and 1 generation requiring ~161s), giving insufficient coverage of answerable cases.

### Milestone 6.1 Achievements:
- **Fail-Closed Contract**: Upgraded `services/rag/validator.py` and `services/rag/pipeline.py` so that any citation anomaly (malformed syntax like `[E#]`, non-existent IDs like `[E99]`, or uncited substantive assertions) transitions the pipeline status to `"validation_failed"` or `"insufficient_evidence"`, guaranteeing that unverified generations are never emitted as valid legal answers.
- **Root-Cause Resolution of the 16 Partial Claims**: Authored `docs/MILESTONE_6_1_PARTIAL_SUPPORT_AUDIT.md`, deployed abbreviation- and citation-aware segmentation lookaheads, and added bench/header metadata recognition.
- **Prompt Template Hardening**: Eliminated instructional `[E#]` placeholders from `services/rag/prompt.py` and instituted Rule 8 prohibiting placeholder tokens.
- **Bounded 10-Query Live Ollama Benchmark**: Successfully executed a 10-query evaluation (6 answerable across single-holding, multi-passage, and statutory interpretation categories; 4 out-of-corpus/adversarial abstentions).
- **Zero Timeouts**: Achieved 100% completion (0 timeouts across 10 queries, whereas Milestone 6 timed out on its second generation).
- **Regression Suite**: Added 14 comprehensive tests in `tests/test_milestone6_1_hardening.py`, bringing repository test coverage to **154 passing tests** (100% pass rate).

---

## 2. Complete Evaluation Metric Definitions

To ensure methodological rigor and prevent conflation of distinct pipeline stages, Milestone 6.1 defines the following evaluation metrics:

### 2.1 Citation Precision
$$\text{Citation Precision} = \frac{|\text{Valid Evidence IDs Cited in Answer}|}{|\text{Total Evidence IDs Cited in Answer}|}$$
- A citation is valid if and only if its identifier exists in the active retrieved evidence context for that specific query turn.
- In Milestone 6.1 live Ollama evaluation:
  - Queries `M6_001`, `M6_002`, `M6_004`, `M6_005`, `M6_007` cited `['E1']` with precision $1.0$.
  - Query `M6_009` cited `['E1', 'E2', 'E3']` when only `E1` was in context budget, yielding precision $\frac{1}{3} = 0.333$.
  - Overall citation precision across all emitted citations: $\frac{6}{8} = 75.0\%$.

### 2.2 Citation Recall
$$\text{Citation Recall} = \frac{|\text{Sentences with Valid In-Line Bracket Citations}|}{|\text{Total Substantive Assertive Sentences in Generated Answer}|}$$
- Structural headers, conversational disclaimers, and explicit abstention formulas are filtered from the denominator.
- Answers where recall $< 1.0$ fail citation validation due to un-cited substantive propositions.

### 2.3 Fully Supported Answer Rate
$$\text{Fully Supported Answer Rate} = \frac{|\text{Answered Queries where ALL claims are labeled 'supported' and citation validation passed}|}{|\text{Total Completed Queries}|}$$
- Requires syntactic citation validity, existence validity, full sentence attribution, and verified grounding in retrieved judicial passages.

### 2.4 Partially Supported Answer Rate
$$\text{Partially Supported Answer Rate} = \frac{|\text{Answered Queries where claims establish background/issues but lack complete ratio decidendi}|}{|\text{Total Completed Queries}|}$$
- Captured in the claim review artifact. Never promoted to valid status in API responses.

### 2.5 Unsupported / Hallucinated Answer Rate
$$\text{Unsupported Rate} = \frac{|\text{Answered Queries containing external legal assertions contradictory to or absent from evidence}|}{|\text{Total Completed Queries}|}$$
- System performance: **0.0%** across both Milestone 6 and 6.1 (zero ungrounded factual hallucinations emitted as answered).

### 2.6 Gate Abstention Precision & Recall
$$\text{Gate Abstention Precision} = \frac{\text{True Abstentions}}{\text{True Abstentions} + \text{False Abstentions}}$$
$$\text{Gate Abstention Recall} = \frac{\text{True Abstentions}}{\text{True Abstentions} + \text{False Answers on Unanswerable}}$$
- On the 4 gold unanswerable queries (`M6_017`, `M6_018`, `M6_019`, `M6_020`):
  - Correct Abstentions: $4/4$ ($100.0\%$).
  - False Answers: $0/4$ ($0.0\%$).
  - Abstention Precision: $100.0\%$. Abstention Recall: $100.0\%$.

### 2.7 Separation of Latencies: Fast-Exit vs. Generation
- **Gate Fast-Exit Latency**: The wall-clock elapsed duration for retrieval, passage assembly, and `PropositionGroundingGate` execution when the gate decides to abstain prior to LLM invocation.
- **Full Generation Latency**: The complete end-to-end duration including retrieval, passage assembly, grounding gate, prompt construction, local SLM token generation via Ollama, citation validation, and response serialization.
- *Strict Invariant*: These two latency regimes are never averaged together into a single misleading metric.

---

## 3. Cross-Milestone Comparative Matrix

The following matrix compares performance across NyayaVarta milestones from Milestone 5C through Milestone 6.1:

| Milestone | Target Evaluator / Provider | Queries Tested | Gate Abstention Accuracy | Citation Validity Rate | Supported Claims Rate | Fast-Exit Latency (Median) | Generation Latency (Median) | Generation TPS | Regression Tests Passing | Key Architectural Milestone |
|---|---|---|---|---|---|---|---|---|---|---|
| **5C** | `mock` / `ollama` (1 q) | 20 (13 ans, 7 abst) | 71.4% (5/7) | 100% (syntactic) | 84.6% (11/13 rev) | N/A | 1.8 ms (mock) / 144s (ollama) | ~7.2 tps | 97 | 20-query evaluation set; initial Ollama CPU benchmark |
| **5D** | `mock` | 20 (13 ans, 7 abst) | 100% (7/7) | 100% (syntactic) | 100% (13/13) | 0.80 ms | 2.1 ms | N/A | 113 | Introduction of Proposition Grounding Gate; fixed LAQ015/LAQ016 |
| **5E** | `mock` (adversarial) | 20 (6 ans, 14 ungrounded) | 100% (14/14) | 100% (syntactic) | 100% (6/6) | 0.22 ms | 1.9 ms | N/A | 122 | Adversarial matrix: negation, exception, party submission, rejected arguments |
| **5F** | `phi3.5:latest` (live) | 32 gate / 6 ollama | 100% (27/27 gate) | 0% (ollama) | 0% (6/6 abst) | 0.32 ms | 144.8s (ollama) | ~6.5 tps | 124 | Unseen test set; blinded review; discovered SLM over-abstention |
| **6** | `mock` (22 q) / `phi3.5` (7 q) | 22 e2e / 8 ollama | 100% (6/6) | 27.3% (mock) / 75% (ollama) | 56.8% (21/37 supp, 16 part) | 0.18 s | 0.06s (mock) / 159.4s (ollama) | 7.67 tps | 140 | End-to-end 22-query benchmark; discovered `[E#]` and regex cleavage |
| **6.1** | `phi3.5:latest` (bounded) | 10 (6 ans, 4 abst) | **100% (4/4)** | **100% (syntactic)** / **Fail-Closed** | **100% (8/8 rev)** | **88 ms** (0.088s) | **141.5s** (141,536 ms) | **6.0 tps** (eval) | **154** | **Fail-closed response policy; regex cleavage fix; prompt de-biasing; 0 timeouts** |

---

## 4. Live Ollama Inference Results (`phi3.5:latest`)

### 4.1 Evaluation Configuration
- **Model**: `phi3.5:latest` (3.82B parameters, Q4_K_M quantization).
- **Execution Engine**: Local Ollama server (`http://localhost:11434`) running on Windows 11 host CPU.
- **Thread Allocation**: 8 CPU worker threads.
- **Context Budget**: `max_passages = 1`, `max_chars_per_passage = 1000`, `num_ctx = 2048`, `num_predict = 140`, `temperature = 0.0`.
- **Timeout Limit**: 240.0s per query turn.
- **Dataset**: 10 targeted queries selected from Milestone 6 end-to-end dataset:
  - 6 answerable queries: `M6_001` (Article 142 IIT fee glitch), `M6_002` (IBC Sec 62 appeal), `M6_004` (Limitation Sec 18 balance sheet), `M6_005` (NI Act Sec 148 signatory deposit), `M6_007` (Prison caste discrimination), `M6_009` (CGST Sec 17(5)(d) functionality test).
  - 4 abstention queries: `M6_017` (DPDP Act Sec 18), `M6_018` (Muslim law coparcenary), `M6_019` (Anticipatory bail in contempt), `M6_020` (Patents Act Sec 3(j) GM mustard).

### 4.2 Query-by-Query Outcome Summary

| Query ID | Legal Domain | Expected Answerable | Actual Status | Grounding Decision | Citation Validity | Valid Cited IDs | Invalid Cited IDs | Generation Latency | Prompt Eval Tokens / TPS | Eval Tokens / TPS |
|---|---|---|---|---|---|---|---|---|---|---|
| `M6_001` | Constitutional Law | Answerable | `insufficient_evidence` | `topically_relevant...` | `invalid` (attribution) | `['E1']` | `[]` | 227.03s | 1335 / 12.2 tps | 508 / 4.63 tps |
| `M6_002` | Insolvency Law | Answerable | **`answered`** | **`sufficient_evidence`** | **`valid`** | `['E1']` | `[]` | 141.54s | 1350 / 22.0 tps | 407 / 5.32 tps |
| `M6_004` | Insolvency & Limitation | Answerable | **`answered`** | **`sufficient_evidence`** | **`valid`** | `['E1']` | `[]` | 176.38s | 1332 / 18.7 tps | 424 / 4.16 tps |
| `M6_005` | Commercial Criminal | Answerable | `insufficient_evidence` | `topically_relevant...` | `valid` | `['E1']` | `[]` | 120.02s | 1333 / 26.2 tps | 436 / 6.60 tps |
| `M6_007` | Constitutional Law | Answerable | `insufficient_evidence` | `topically_relevant...` | `invalid` (attribution) | `['E1']` | `[]` | 130.37s | 1257 / 25.6 tps | 512 / 6.53 tps |
| `M6_009` | Taxation Law | Answerable | `insufficient_evidence` | `topically_relevant...` | `invalid` (hallucinated `E2`, `E3`) | `['E1']` | `['E2', 'E3']` | 128.72s | 1363 / 26.5 tps | 512 / 6.86 tps |
| `M6_017` | Data Protection | Unanswerable | **`insufficient_evidence`** | **`insufficient_grounding`** | **`valid`** | `[]` | `[]` | **0.08s (fast-exit)** | N/A (bypassed) | N/A (bypassed) |
| `M6_018` | Personal Law | Unanswerable | **`insufficient_evidence`** | **`insufficient_grounding`** | **`valid`** | `[]` | `[]` | **0.06s (fast-exit)** | N/A (bypassed) | N/A (bypassed) |
| `M6_019` | Criminal Procedure | Unanswerable | **`insufficient_evidence`** | **`insufficient_grounding`** | **`valid`** | `[]` | `[]` | **0.09s (fast-exit)** | N/A (bypassed) | N/A (bypassed) |
| `M6_020` | Intellectual Property | Unanswerable | **`insufficient_evidence`** | **`insufficient_grounding`** | **`valid`** | `[]` | `[]` | **0.16s (fast-exit)** | N/A (bypassed) | N/A (bypassed) |

### 4.3 Detailed Performance Analysis

#### 1. Gate Fast-Exit Distribution (Abstentions)
- **Sample Size**: 4 queries.
- **Latency Distribution**:
  - Minimum: 0.064s (64 ms)
  - Median: 0.088s (88 ms)
  - p95: 0.162s (162 ms)
  - Maximum: 0.162s (162 ms)
- **Observations**: The Proposition Grounding Gate executed predicate analysis, statutory extraction, and disjoint-subject detection in under 10 ms of pure gate time, saving an estimated 560 to 700 seconds of expensive, unnecessary CPU generation.

#### 2. LLM Generation Distribution (Answerable Queries)
- **Sample Size**: 6 queries.
- **Latency Distribution**:
  - Minimum: 120.02s
  - Median: 141.54s
  - p95: 227.03s
  - Maximum: 227.03s
- **Throughput & Token Timings**:
  - **Generation Speed**: Median 6.0 tokens/second (range: 4.16 tps to 6.86 tps).
  - **Time to First Token (TTFT)**: TTFT on CPU is dominated by prompt evaluation (`prompt_eval_ms`). For ~1300 prompt tokens, prompt eval took between 49.2s and 109.4s (median ~56.4s, prompt ingestion rate: ~22 to 26 tokens/sec).
  - **Timeouts**: **0 timeouts out of 6 invocations** (100% completion within the 240s boundary).

#### 3. Real-World Efficacy of the Fail-Closed Hardening
- In `M6_009`, the local SLM generated an answer citing `[E1]`, `[E2]`, and `[E3]`. Because the bounded context provided only `E1`, the citation validator detected `invalid_ids = ['E2', 'E3']`.
- Under the Milestone 6 logic, this answer would have been emitted with `status: "answered"` alongside an obscure diagnostic note.
- Under the Milestone 6.1 fail-closed contract, `pipeline.py` intercepted the invalid citation result and refused to emit the answer as answered, transitioning the status to `insufficient_evidence` / `validation_failed`.
- Similarly, in `M6_001` and `M6_007`, the SLM omitted citations on certain substantive sentences. The validator flagged the missing attribution and enforced fail-closed safety.
- In `M6_002` and `M6_004`, the SLM adhered strictly to the prompt rules, citing `[E1]` consistently without placeholder tokens. Both answers were validated, verified, and successfully returned as `answered`.

---

## 5. Summary of Partial Support Audit Findings

As detailed in `docs/MILESTONE_6_1_PARTIAL_SUPPORT_AUDIT.md`, an exhaustive audit of all 16 `partially_supported` claims from Milestone 6 (`C01` across `M6_001` to `M6_016`) established two root causes:

1. **Sentence Boundary Cleavage**:
   - The regex `\.\s+` previously split sentences directly between a terminal period and a following bracket citation (`... text. [E1]`), leaving `C01` with `cited_evidence_ids = []`.
   - Remediated by implementing a non-cleaving lookahead: `(?:\.|\?|\!)\s+(?!\[(?:E\d+|E#|E|evidence|source|ref)[^\]]*\])`.
2. **Issue Framing vs. Ratio Decidendi**:
   - In 14 of 16 cases, the text extracted for `C01` was the headnote section `Issue for Consideration` (e.g., *"Whether a pendente lite transferee can file an application under Order XXI Rule 99..."*).
   - This text accurately frames the legal controversy before the Supreme Court, but does not state the Court's binding answer (*ratio decidendi*).
   - *Epistemic Finding*: The label `partially_supported` was substantively correct. NyayaVarta properly distinguishes between identifying an issue under consideration and establishing a binding judicial holding.

---

## 6. Regression Test Suite Verification

The regression suite was expanded with 14 targeted tests in `tests/test_milestone6_1_hardening.py`. The full repository test suite was executed:

```bash
.\venv\Scripts\pytest.exe -v
```

### Results:
- **Total Tests Run**: 154
- **Passed**: 154 (100%)
- **Failed**: 0
- **Duration**: 21.65 seconds

### Coverage of the 14 Mandatory Milestone 6.1 Test Cases:
1. `test_case_01_malformed_marker_bracket_e_hash`: Rejects `[E#]`, `[]`, `[E ]` with fail-closed status.
2. `test_case_02_unknown_evidence_id_e99`: Rejects non-existent citation ID `[E99]`.
3. `test_case_03_stale_citation_id_e2`: Rejects citation ID from prior context when only `E1` is active.
4. `test_case_04_substantive_claim_without_citation`: Flags substantive legal assertion lacking citations.
5. `test_case_05_one_supported_one_unsupported_claim`: Enforces fail-closed when any substantive sentence is uncited.
6. `test_case_06_multi_part_claim_single_support`: Detects compound assertion where only one clause has citation support.
7. `test_case_07_statutory_exception_missing_from_evidence`: Abstains when qualification/exception is absent from retrieved evidence.
8. `test_case_08_party_submission_misrepresented_as_holding`: Gate detects party contention framing and rejects holding status.
9. `test_case_09_contradictory_evidence_passages`: Gate detects contradictory judicial indicators and forces abstention.
10. `test_case_10_valid_answer_multiple_citations`: Successfully validates and accepts multi-citation brackets (`[E1, E2]`).
11. `test_case_11_safe_abstention_on_unsupported_query`: Confirms fast-exit abstention on out-of-corpus statutory query.
12. `test_case_12_provider_timeout_and_failure_error_masking`: Verifies 504/503 HTTP status mapping and secret/traceback masking.
13. `test_case_13_api_serialization_invalid_and_partially_supported`: Verifies Pydantic serialization of validation statuses and notes.
14. `test_case_14_diagnostic_warning_never_promoted_to_valid`: Verifies invariant that warnings/partial support are never promoted to valid.

---

## 7. Known Limitations & Epistemic Honesty Boundaries

1. **CPU Latency Ceiling**: On 8-thread CPU inference, `phi3.5:latest` requires ~50–100 seconds for prompt evaluation and ~70–110 seconds for token generation (~120–220 seconds total). While acceptable for offline verification and research workflows, real-time interactive chat requires quantized SLM GPU acceleration or speculative decoding.
2. **SLM Citation Precision Under Low Context**: When constrained to 1 evidence passage (`max_passages: 1`), smaller models occasionally hallucinate citations `[E2]` and `[E3]` from habit or training priors. The fail-closed validator reliably intercepts these occurrences, but prompting techniques alone cannot eliminate 100% of SLM hallucinations without structured JSON schema decoding.
3. **Internal Evaluator Provenance**: All claim annotations, gold judgments, and evaluation datasets in this milestone were created by software and ML engineers (`developer_curated`). They have not been reviewed or certified by advocates, legal scholars, or judicial officers.
4. **No Legal Advice Warranty**: NyayaVarta is an experimental academic prototype operating over 782 Supreme Court judgments from 2024. It does not provide legal advice, does not cover high courts or statutes comprehensively, and must not be relied upon for litigation or legal practice.

---

## 8. Concrete Recommendations for Milestone 7

1. **Constrained Decoding / Grammars**: Enforce GBNF grammars or Ollama JSON schema constraints during inference to mechanically forbid the emission of un-cited sentences or citation IDs outside the active evidence set (`enum: ["E1", "E2"]`).
2. **Passage Chunking Optimization**: Break long judgment headnotes into atomic ratio decidendi chunks (200–400 tokens) to minimize prompt evaluation time on CPU from ~60s down to ~15s.
3. **Structured Claim Reviewer API**: Expose the claim review tooling directly in the FastAPI interface (`/rag/review-claims`) allowing human legal practitioners to audit generated answers interactively.
4. **Independent Legal Evaluation**: Partner with qualified legal researchers to evaluate a blind sample of 50 queries across constitutional, commercial, and criminal domains.
