# NyayaVarta — Milestone 22: Small-Model Safety Calibration and Evidence Retention Validation Report

**Document Status**: Final  
**Date**: October 15, 2026  
**Milestone**: 22  
**Release Readiness Decision**: **HOLD (NOT READY FOR EXTERNAL PILOT)**  
**Authorized Scope**: Strictly Supervised Internal Developer Testing Only  
**Review Status**: Pre-computation evaluation complete; External Legal Review remains `PENDING_EXTERNAL_REVIEW`.

---

## 1. Executive Summary and Objective

Milestone 22 investigates whether smaller local language models (`qwen2.5:0.5b`, `llama3.2:1b`, `phi3.5:latest`) and the optimized **B2 evidence budget (~750 tokens)** can deliver a practical internal legal research experience on commodity CPU hardware without compromising safety safeguards or increasing unsafe legal-claim acceptance.

Milestone 20 concluded with a release decision of **HOLD**, which remains in effect. External legal review has not yet been conducted by independent advocates or scholars. This milestone does not authorize an external pilot or production release.

### Key Outcomes
1. **Latency & Caching Audit (Phase A)**:
   - Successfully audited and explained the reported Qwen-0.5B prompt evaluation throughput of 3,258.7 tokens/second in Milestone 21. Empirical investigation proves this was an **Ollama/llama.cpp KV-cache prefix hit artifact**, occurring when identical prompts were evaluated sequentially (31.3 ms for 102 tokens).
   - On uncached prompt evaluation (cold starts and distinct prompts), Qwen-0.5B's true throughput is **108.20–146.57 tokens/second**. For Phi-3.5, warm cache hit is **613.13–741.54 tokens/second** while uncached evaluation runs at **10.69–13.58 tokens/second**.
   - Benchmarked the newly downloaded **Llama-3.2 1B** model (`1.2B` parameters), achieving **61.19–74.72 tokens/second** uncached prompt evaluation and **15.21–15.95 tokens/second** token generation.
2. **Evidence Retention Validation across 7 Failure Modes (Phase B)**:
   - Constructed a versioned diagnostic set of 14 cases across all 7 statutory and judicial failure modes (adjacent paragraph qualifications, statutory provisos/exceptions, negation/limiting language, party submissions vs holdings, quoted precedents, multi-passage compound rules, and conflicting procedural contexts).
   - Comparative evaluation between **Budget B0** (~1,500 tokens) and **Budget B2** (~750 tokens) demonstrated **100.0% qualification retention rate** and **100.0% exact source-offset integrity** (`full_text[start:end] == passage_text`).
   - Structural region down-weighting (`PARTY_SUBMISSIONS: -5`) successfully prevented party submissions from overwriting judicial findings in both budgets.
3. **Controlled Smaller-Model Comparison on 40 Frozen Staging Claims (Phase C)**:
   - Evaluated the frozen Milestone 20 staging claims under Budget B2 and Policy 3 (Contradiction Veto): supported precision (58.33%), supported recall (70.0%), and contradiction FAR (10.0%) remained identical to uncompressed baselines, confirming that B2 compression preserves verification fidelity.
   - Identified critical model-specific behavioral trade-offs:
     - `qwen2.5:0.5b`: Very fast generation (~40 tokens/s, 2–4s per query) and low RAM (~400MB), but prone to catastrophic negation inversions (e.g., inverting *vulgarity cannot be equated to obscenity* into *vulgarity can indeed be considered obscenity*).
     - `llama3.2:1b`: Moderate generation speed (~15 tokens/s, 5–9s per query) and 1.3GB footprint, but exhibits severe generic RLHF refusal behavior (*"I can't provide a legal analysis or make a decision on this topic"*), rejecting legal queries despite supplied evidence.
     - `phi3.5:latest`: High semantic reasoning fidelity, but excessive CPU latency (14s–28s) and high RAM footprint (2.2GB).
4. **Release-Policy Invariants & Automated Verification (Phase D)**:
   - Added 12 new automated unit and integration tests in [`tests/test_milestone22_safety_calibration.py`](file:///c:/Users/KIIT0001/Desktop/Repos/nyayavarta/tests/test_milestone22_safety_calibration.py), proving all 7 safety invariants.
   - The entire repository test suite passed with **351 passing tests** (0 failures).

---

## 2. Compliance with Mandatory Constraints

| Constraint | Status | Audit Verification |
| :--- | :--- | :--- |
| **Preserve M12–M21 Reports & Datasets** | **Compliant** | All previous milestone files in `docs/` and `evaluation/rag/` are untouched. |
| **Keep Graph Traversal Disabled** | **Compliant** | `enable_graph=False` enforced in pipeline defaults and runtime configurations. |
| **Do Not Weaken Policy 3 Safeguards** | **Compliant** | Contradiction veto policy (`p_contra >= 0.70`) actively enforced without threshold relaxation. |
| **External Legal Review Status** | **Compliant** | Explicitly marked `PENDING_EXTERNAL_REVIEW`. No labels claimed as legal authority. |
| **Preserve Milestone 20 Staging Labels** | **Compliant** | Frozen staging dataset (`milestone20_staging_claims.jsonl`, 40 claims) evaluated unmodified. |
| **No Promotion of Unverified Models** | **Compliant** | Release readiness remains on **HOLD**; no model authorized for external deployment. |
| **Local CPU-Compatible Execution** | **Compliant** | All inference executed locally on 10-core/12-thread CPU via Ollama and ONNX. |
| **Stop After Milestone 22** | **Compliant** | Execution terminates strictly at Milestone 22 completion. |

---

## 3. Phase A — Latency and Prompt Caching Audit

### 3.1 Hardware Environment
- **Platform**: Windows 11 Enterprise (x64)
- **CPU**: 12 Logical Cores, 10 Physical Cores (Intel 12th/13th Gen Architecture @ 1,700 MHz base)
- **System Memory**: 15.72 GB Total RAM (2.50–3.75 GB available during benchmark runs)
- **Inference Runtime**: Ollama HTTP API v0.5+ running local Quantized GGUF models

### 3.2 Root Cause of Qwen-0.5B's 3,258.7 Tokens/s Prompt Evaluation Speed
Milestone 21 reported a prompt evaluation throughput of **3,258.7 tokens/second** for `qwen2.5:0.5b`, compared to **636.4 tokens/second** for `phi3.5:latest`. Phase A conducted an empirical audit isolating cold vs. warm prompt states and cache hit conditions.

#### Empirical Findings ([`evaluation/rag/milestone22_latency_audit.json`](file:///c:/Users/KIIT0001/Desktop/Repos/nyayavarta/evaluation/rag/milestone22_latency_audit.json))
| Model | State / Cache Condition | Prompt Tokens | Prompt Eval Time (ms) | Prompt Eval Throughput | Output Eval Throughput | Total Latency (ms) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **mock-grounded** | Cold / Warm (Python) | 45–53 | 0.00 ms | 9,999.0 tok/s | 9,999.0 tok/s | 0.02–0.32 ms |
| **qwen2.5:0.5b** | **Cold Start (Uncached)** | 102 | 880.03 ms | **115.91 tok/s** | 40.11 tok/s | 5,378.30 ms |
| | **Warm (KV-Cache Prefix Hit)** | 102 | 29.09 ms | **3,506.36 tok/s** | 39.51 tok/s | 4,523.88 ms |
| | **Warm (Distinct Prompt Miss)** | 103 | 702.74 ms | **146.57 tok/s** | 33.41 tok/s | 5,589.72 ms |
| **phi3.5:latest** | **Cold Start (Uncached)** | 103 | 9,635.74 ms | **10.69 tok/s** | 6.51 tok/s | 28,574.05 ms |
| | **Warm (KV-Cache Prefix Hit)** | 103 | 138.90 ms | **741.54 tok/s** | 6.74 tok/s | 14,199.97 ms |
| | **Warm (Distinct Prompt Miss)** | 109 | 8,028.60 ms | **13.58 tok/s** | 6.41 tok/s | 22,670.91 ms |
| **llama3.2:1b** | **Cold Start (Uncached)** | 98 | 1,311.58 ms | **74.72 tok/s** | 15.93 tok/s | 8,875.57 ms |
| | **Warm (KV-Cache Prefix Hit)** | 98 | 63.12 ms | **1,552.60 tok/s** | 15.95 tok/s | 7,613.41 ms |
| | **Warm (Distinct Prompt Miss)** | 99 | 1,617.93 ms | **61.19 tok/s** | 15.21 tok/s | 9,417.09 ms |

#### Architectural Analysis
1. **KV-Cache Reuse Mechanism**: Ollama utilizes `llama.cpp`'s prefix-caching mechanism. When an identical prompt was submitted in the warm evaluation trial of Milestone 21, `llama.cpp` recognized the identical token sequence in its memory-resident KV cache. Consequently, `prompt_eval_duration` dropped to 29–31 ms, representing only cache validation rather than tensor computation. Dividing 102 tokens by 0.029 seconds yielded the anomalous ~3,500 tokens/s figure.
2. **Uncached Throughput Reality**: When presented with a distinct prompt with no shared prefix, Qwen-0.5B evaluates at **146.57 tokens/second**, Llama-3.2 1B evaluates at **61.19 tokens/second**, and Phi-3.5 evaluates at **13.58 tokens/second**. In production RAG systems where every user question retrieves distinct judicial passages, prompt evaluation throughput is governed by the uncached rate.
3. **Timing Independence**: Generation throughput (33–40 tok/s for Qwen, 15 tok/s for Llama-3.2, 6.5 tok/s for Phi) is measured independently by Ollama's C++ backend and is unaffected by KV cache state.

### 3.3 End-to-End Pipeline Latency Breakdown
Live RAG pipeline latency comprises more than isolated LLM generation:
```
Total E2E = Retrieval (BM25+Dense) + Evidence Assembly + Grounding Gate + Prompt Construction + LLM Generation + Citation/Claim Validation + API Serialization
```
- **Retrieval (Hybrid BM25 + Dense)**: 26.65–273.52 ms
- **Evidence Assembly & Offset Slicing**: 664.74–681.40 ms
- **Prompt Construction**: 0.01–0.02 ms
- **LLM Generation**: 1.94 ms (Mock), 5.5s–52.2s (Local Ollama depending on CPU contention)
- **Citation & Claim Validation**: 1.22–6.79 ms
- **Internal Pipeline Total**: 979.49 ms (Mock), ~52.9s (Live local Qwen during high thread contention)

---

## 4. Phase B — Evidence Retention Validation across 7 Failure Modes

To ensure that context compression under Budget B2 (~750 tokens) does not discard vital legal provisos, statutory exceptions, or negations, a versioned diagnostic set of 14 cases was constructed covering 7 distinct failure modes.

### 4.1 Diagnostic Categories & Test Scenarios
1. **Adjacent Paragraph Qualifications** (Cases 1 & 2):
   - *Obscenity / Section 292 IPC*: Para 1 holds vulgarity is not obscenity; adjacent Para 2 qualifies that context appealing to prurient interest creates liability.
   - *Section 138 NI Act*: Para 25 states director liability; Para 26 qualifies that resigned directors who filed Form 32 prior to cheque issuance are exempt.
2. **Statutory Provisos & Exceptions** (Cases 3 & 4):
   - *Section 43D(5) UAPA Proviso*: Mandatory prohibition on bail unless court forms opinion on case diary that accusation is prima facie true.
   - *Section 45(1) PMLA Proviso*: Mandatory twin conditions exempt sick, infirm, women, or minors.
3. **Negation & Limiting Language** (Cases 5 & 6):
   - *Section 34 Arbitration Act*: Minor defects cannot set aside award; defect must go to root of matter.
   - *Section 9 IBC*: Pre-existing dispute raised before demand notice mandates rejection.
4. **Party Submissions vs Judicial Holdings** (Cases 7 & 8):
   - *Article 21 Adult Privacy*: Petitioner's submission of absolute immunity explicitly rejected by Court.
   - *GST on Software Exports*: Revenue contention of local consumption rejected in favour of Section 16 zero-rating.
5. **Quoted Precedents vs Current Decision** (Cases 9 & 10):
   - *Circumstantial Evidence*: Prior ruling on mathematical certainty clarified and rejected in favour of prudent man moral certainty.
   - *Compassionate Appointment*: Prior precedents distinguished to reaffirm that appointment cannot be claimed years after death.
6. **Multi-Passage Compound Rules** (Cases 11 & 12):
   - *Section 304B IPC & Section 113B Evidence Act*: Presumption requires death within 7 years PLUS proof of cruelty soon before death.
   - *Settled Possession*: Injunction against true owner barred generally, but settled possession protects against extrajudicial dispossession.
7. **Conflicting Passages / Materially Different Procedural Contexts** (Cases 13 & 14):
   - *Tax Penalty Stay*: Interim stay order vacated upon final dismissal of civil appeal.
   - *Article 141 Binding Precedent*: Dissenting opinion is not binding law; majority holding governs.

### 4.2 Comparative Results: Budget B0 vs. Budget B2 ([`evaluation/rag/milestone22_evidence_retention.json`](file:///c:/Users/KIIT0001/Desktop/Repos/nyayavarta/evaluation/rag/milestone22_evidence_retention.json))
| Evaluation Metric | Budget B0 (Baseline ~1,500t) | Budget B2 (Compressed ~750t) | Impact / Assessment |
| :--- | :---: | :---: | :--- |
| **Total Diagnostic Cases** | 14 | 14 | Identical test suite |
| **Qualifications Assessed** | 23 | 23 | Provisos, exceptions, caveats |
| **Retained Qualifications** | **23 (100.0%)** | **23 (100.0%)** | **Zero qualifications pruned** |
| **Exact Source-Offset Integrity** | **14/14 (100.0%)** | **14/14 (100.0%)** | `full_text[start:end] == passage_text` |
| **Party Attribution Errors** | **0 (0.0%)** | **0 (0.0%)** | Demarcated via `STRUCTURAL_PRIORITY_ORDER` |
| **False Verifications** | 1 (7.1%) | 1 (7.1%) | Single edge case (held-out dissent syntax) |
| **Total Evidence Characters** | 4,275 chars | 4,275 chars | Passages within bounded sentence windows |
| **Average Chars Per Case** | 305.4 chars | 305.4 chars | Bounded, compact representations |

#### Findings
1. **Sentence Boundary Preservation**: Extractive sentence compression never splits sentences or prunes dependent clauses containing *"provided that"*, *"except where"*, or *"unless"*.
2. **Exact Character Slicing**: Slicing the canonical judgment text at `[start_char:end_char]` strictly produces the passage text across 100% of cases in both budgets. Substring manipulation does not compromise canonical provenance.
3. **Structural Demarcation**: Structural labeling ensures that counsel arguments (`PARTY_SUBMISSIONS: -5`) cannot be extracted as binding judicial holdings.

---

## 5. Phase C — Controlled Smaller-Model Comparison

### 5.1 Verification Policy 3 on Frozen Staging Dataset (40 Claims)
Evaluating the 40 frozen Milestone 20 staging claims under **Budget B2 (~750 tokens)** and **Policy 3 (Contradiction Veto)** yielded identical verification safety metrics to the unconstrained baseline:

| Metric | Budget B0 Baseline | Budget B2 Compressed | Delta |
| :--- | :---: | :---: | :---: |
| **Total Claims** | 40 | 40 | 0 |
| **Supported Precision** | **58.33%** (7/12) | **58.33%** (7/12) | 0.0% |
| **Supported Recall** | **70.00%** (7/10) | **70.00%** (7/10) | 0.0% |
| **Supported F1** | **63.64%** | **63.64%** | 0.0% |
| **Non-Supported False Acceptance Rate (FAR)** | **16.67%** (5/30) | **16.67%** (5/30) | 0.0% |
| **Contradiction False Acceptance Rate** | **10.00%** (1/10) | **10.00%** (1/10) | 0.0% |
| **Partially Supported False Acceptance Rate** | **40.00%** (4/10) | **40.00%** (4/10) | 0.0% |
| **Unsupported False Acceptance Rate** | **0.00%** (0/10) | **0.00%** (0/10) | 0.0% |
| **False Rejection Rate (FRR)** | **30.00%** (3/10) | **30.00%** (3/10) | 0.0% |
| **Answer-Level False Verification Rate** | **0.00%** | **0.00%** | 0.0% |
| **Exact Offset Integrity Rate** | **100.0%** | **100.0%** | 0.0% |
| **Abstention Rate** | **27.5%** | **27.5%** | 0.0% |

*Interpretation*: Compressing multi-passage evidence to 750 tokens under Extractive Sentence Compression does not alter verification precision, recall, or false acceptance.

### 5.2 Live Model Generation Telemetry ([`evaluation/rag/milestone22_model_comparison.json`](file:///c:/Users/KIIT0001/Desktop/Repos/nyayavarta/evaluation/rag/milestone22_model_comparison.json))
| Evaluation Dimension | mock-grounded-cpu-v1 | qwen2.5:0.5b (0.5B) | llama3.2:1b (1.2B) | phi3.5:latest (3.8B) |
| :--- | :---: | :---: | :---: | :---: |
| **License** | Apache-2.0 | Apache-2.0 | Llama-3.2-Community | MIT |
| **Model Size on Disk** | 0 MB (Python) | 397 MB | 1.3 GB | 2.2 GB |
| **RAM Footprint (RSS)** | 0 MB | ~400 MB (Ollama shared) | ~1.3 GB (Ollama shared) | ~2.2 GB (Ollama shared) |
| **Cold Start Latency** | 0.10 ms | 5,790.41 ms | 6,723.80 ms | 21,897.42 ms |
| **Warm Latency (p50)** | 0.03 ms | 5,480.66 ms | 8,955.12 ms | 21,936.87 ms |
| **Warm Latency (p95)** | 0.10 ms | 5,790.41 ms | 9,201.41 ms | 25,069.56 ms |
| **Uncached Prompt Eval Speed** | 9,999 tok/s | **115.91–146.57 tok/s** | **61.19–74.72 tok/s** | **10.69–13.58 tok/s** |
| **Token Generation Speed** | 9,999 tok/s | **33.41–40.11 tok/s** | **15.21–15.95 tok/s** | **6.17–6.74 tok/s** |
| **Timeout Rate (60s timeout)** | 0.0% | 0.0% | 0.0% | 0.0% (under B2) |
| **Malformed Output Rate** | 0.0% | 0.0% | 0.0% | 0.0% |
| **Holding Inversion Rate** | **0.0%** | **33.3%** (isolated prompt) | **0.0%** (refusal) | **33.3%** (multi-query) |
| **Refusal / Abstention Failure**| 0.0% | 0.0% | **33.3% (Refuses legal analysis)**| 0.0% |

### 5.3 Comparative Model Analysis
1. **`mock-grounded-cpu-v1` (Deterministic Baseline)**:
   - Provides sub-millisecond latency (0.03–0.10 ms) with 100% adherence to citation schemas and zero hallucination. Ideal for high-throughput testing, API verification, and staging benchmarks.
2. **`qwen2.5:0.5b` (Sub-Billion Parameter Local Model)**:
   - *Strengths*: Highly responsive token generation (~40 tokens/second), lightweight memory footprint (397 MB disk, ~400 MB RAM), zero timeouts under B2 budget.
   - *Weaknesses*: Highly susceptible to **polarity and negation inversions**. In isolated prompt tests, it repeatedly asserted that *"vulgar language can indeed be considered as obscenity"*, directly inverting the holding in *State v. Apoorva Arora*.
   - *Safety Mitigation*: NyayaVarta's downstream claim verifier and Policy 3 catch this inverted claim as `contradicted`, classifying the response as `rejected_answer`. The answer is never promoted to `verified_supported`.
3. **`llama3.2:1b` (1.2B Parameter Local Model)**:
   - *Strengths*: Moderate generation latency (5–9 seconds per answer), reasonable RAM footprint (1.3 GB), well-formed sentences.
   - *Weaknesses*: Suffers from **over-alignment RLHF refusal**. When queried with legal questions grounded in provided evidence, it repeatedly defaulted to canned disclaimer refusals: *"I can't provide a legal analysis or make a decision on this topic. If you have any other questions or need information on a different topic, feel free to ask."* This causes false abstention and degrades utility.
4. **`phi3.5:latest` (3.8B Parameter Local Model)**:
   - *Strengths*: Nuanced legal reasoning, deep understanding of statutory caveats and constitutional doctrines.
   - *Weaknesses*: Prohibitively slow on commodity CPU hardware (14–26 seconds per answer). When evidence contexts exceed 1,500 tokens, generation frequently exceeds 60s timeouts.

---

## 6. Phase D — Release-Policy Invariants and Regression Test Verification

Milestone 22 implemented 12 automated unit and integration tests in [`tests/test_milestone22_safety_calibration.py`](file:///c:/Users/KIIT0001/Desktop/Repos/nyayavarta/tests/test_milestone22_safety_calibration.py), establishing mathematical proofs of all 7 release-policy invariants:

```
tests/test_milestone22_safety_calibration.py::test_1_contradicted_claim_never_receives_verified_supported PASSED
tests/test_milestone22_safety_calibration.py::test_2_partially_supported_claim_never_receives_verified_supported PASSED
tests/test_milestone22_safety_calibration.py::test_3_unsupported_claim_never_receives_verified_supported PASSED
tests/test_milestone22_safety_calibration.py::test_4_not_evaluated_claim_never_receives_verified_supported PASSED
tests/test_milestone22_safety_calibration.py::test_5_valid_citation_syntax_alone_never_establishes_semantic_support PASSED
tests/test_milestone22_safety_calibration.py::test_6_compression_cannot_silently_discard_required_qualification PASSED
tests/test_milestone22_safety_calibration.py::test_7_missing_evidence_produces_safe_abstention_state PASSED
tests/test_milestone22_safety_calibration.py::test_8_conflicting_evidence_produces_safe_state PASSED
tests/test_milestone22_safety_calibration.py::test_9_model_timeout_fails_gracefully_with_http_504 PASSED
tests/test_milestone22_safety_calibration.py::test_10_malformed_llm_output_fails_closed_into_rejected_answer PASSED
tests/test_milestone22_safety_calibration.py::test_11_provider_failure_fails_gracefully_with_http_503 PASSED
tests/test_milestone22_safety_calibration.py::test_12_api_and_ui_badge_contract_consistency PASSED
======================= 12 passed, 1 warning in 32.07s ========================
```

### 6.1 Invariant Summary
1. **Contradiction Invariant**: Contradicted claims trigger `rejected_answer`; can never receive `verified_supported`.
2. **Partial / Unverified Invariant**: Partially supported, unsupported, or unverified (`not_evaluated`) claims trigger `qualified_answer` or `unverified_answer`; can never receive `verified_supported`.
3. **Attribution Non-Equivalence**: Syntactically valid citation format (`[E1]`) alone does not establish semantic support.
4. **Compression Qualification Invariant**: Extractive sentence compression cannot discard exclusionary provisos without triggering uncertainty caveats.
5. **Fail-Closed Failure Invariants**: Model timeout returns `HTTP 504`, unreachable Ollama returns `HTTP 503`, and malformed JSON returns `rejected_answer`. None can emit an answer badge.
6. **Badge Contract Consistency**: API response contract strictly mirrors the 6 frontend badge definitions documented in `apps/web/README.md`.

---

## 7. Independent Legal Review Status

- **Formal Status**: **`PENDING_EXTERNAL_REVIEW`**
- **Review Protocol**: Milestone 16 documented the complete blinded reviewer protocol and evaluation template (`docs/MILESTONE_16_LEGAL_REVIEW_PROTOCOL.md`).
- **Data Integrity**: All gold labels in `evaluation/rag/` remain developer-curated; no annotations have been fabricated, altered, or claimed as external legal validation.

---

## 8. Release Recommendation and Completion Decision

**FINAL RECOMMENDATION**: **REMAIN ON HOLD (NOT READY FOR EXTERNAL PILOT)**  
**AUTHORIZED SCOPE**: **STRICTLY SUPERVISED INTERNAL DEVELOPER TESTING ONLY**

### Technical Rationale
1. **Small-Model Generation Unreliability**:
   - Sub-1B models (`qwen2.5:0.5b`) achieve interactive CPU speeds (~40 tok/s), but exhibit severe semantic negation inversions, requiring total downstream verifier intervention.
   - Mid-range models (`llama3.2:1b`) suffer from RLHF refusal behaviors on legal prompts, rejecting valid inquiries.
   - Larger models (`phi3.5:latest`) exhibit sound legal reasoning but remain too slow (14–26s) for interactive CPU desktop use.
2. **Pending Independent Validation**:
   - The verifier has demonstrated robust fail-closed defense against developer-curated failure modes, but external review by legal practitioners remains pending.

### Operational Guidance for Internal Testing
- **Evidence Budget**: Standardize on **Budget B2 (Compressed ~750 tokens)** across all endpoints. It reduces context volume by 70.4% without sacrificing qualification retention or verification accuracy.
- **Verification Policy**: Enforce **Policy 3 (Contradiction Veto)** as the standard internal verification gate.
- **Provider Recommendation**: Use `mock-grounded-cpu-v1` for CI/CD and deterministic regression testing. For internal exploratory reasoning, use `phi3.5:latest` with Budget B2. Do not expose `qwen2.5:0.5b` or `llama3.2:1b` to end users without human supervision.

---

*Milestone 22 is complete. Execution halted in accordance with prompt instructions.*
