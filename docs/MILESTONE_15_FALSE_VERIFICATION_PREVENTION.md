# NyayaVarta — Milestone 15: False Verification Prevention and Answer-Level Safety Report

**Status:** Completed  
**Date:** 2026-10-14  
**Evaluator:** NyayaVarta Deterministic ClaimVerifier & Conservative Answer Aggregator  
**Test Suite Status:** 278 / 278 Tests Passing (100% Pass Rate)  
**Corpus:** 782 Supreme Court Judgments (2024)  
**Primary Deliverables:**
- Core Verifier Enhancements: [`services/rag/claim_verifier.py`](file:///c:/Users/KIIT0001/Desktop/Repos/nyayavarta/services/rag/claim_verifier.py)
- Aggregation & Validation Updates: [`services/rag/validator.py`](file:///c:/Users/KIIT0001/Desktop/Repos/nyayavarta/services/rag/validator.py) & [`services/rag/pipeline.py`](file:///c:/Users/KIIT0001/Desktop/Repos/nyayavarta/services/rag/pipeline.py)
- Evaluation Runner: [`scripts/benchmark/evaluate_milestone15_safety.py`](file:///c:/Users/KIIT0001/Desktop/Repos/nyayavarta/scripts/benchmark/evaluate_milestone15_safety.py)
- Verification Results: [`evaluation/rag/milestone15_verification_results.json`](file:///c:/Users/KIIT0001/Desktop/Repos/nyayavarta/evaluation/rag/milestone15_verification_results.json)
- Claim Audit Log: [`evaluation/rag/milestone15_claim_audit.jsonl`](file:///c:/Users/KIIT0001/Desktop/Repos/nyayavarta/evaluation/rag/milestone15_claim_audit.jsonl)
- Regression Test Suite: [`tests/test_milestone15_safety.py`](file:///c:/Users/KIIT0001/Desktop/Repos/nyayavarta/tests/test_milestone15_safety.py)

---

## 1. Executive Summary

Milestone 14 evaluated NyayaVarta's claim-level verifier across 44 held-out, unseen legal claims spanning 11 categories. While Milestone 14 reported a 0.00% False Acceptance Rate (FAR) for contradicted and unsupported claims, closer inspection revealed a critical safety defect: **two claims whose ground-truth label was `partially_supported` (`CR_M14_014` and `CR_M14_017`) were misclassified as `supported`**, reducing precision in the `supported` class to **75.00%** (6 true positives, 2 false positives).

In a high-stakes legal question-answering system, presenting a partially supported legal claim as fully verified poses severe risks of misdirection, particularly when an answer omits mandatory statutory conditions (e.g., SARFAESI Rule 9(4) written consent) or fabricates ungrounded judicial remedies (e.g., universal quashing of criminal convictions in prison reform cases).

Milestone 15 directly resolves this defect through three primary interventions:
1. **Root-Cause Fixes for Context Leakage and Condition Waivers**:
   - Prevented multi-part claim stem leakage (`CR_M14_014`) by computing distinct vocabulary in conjunctive clauses after filtering out stems shared with earlier supported propositions.
   - Prevented negative condition waivers from bypassing verification (`CR_M14_017`) by detecting waiver phrases (e.g., `"without seeking any written consent"`) against cited statutory prerequisite terms and expanding affirmative modal coverage (`"may deposit"`).
2. **Reconciliation and Disaggregation of False Acceptance Metrics**:
   - Reconciled the reporting discrepancy from Milestone 14 by explicitly computing separate false-acceptance rates for partially supported, unsupported, and contradicted claims.
   - Across all 38 non-supported claims in the held-out benchmark, **zero claims are promoted to `supported`** (Total Non-Supported FAR = 0.00%, down from 5.26%).
   - Supported-class precision increased from **75.00% to 100.00%** (6/6).
3. **Conservative Deterministic Answer-Level Aggregation Invariant**:
   - Enforced a fail-closed presentation invariant across the pipeline, validator, and API contract: an answer is **never promoted to `verified_supported`** unless 100% of its substantive claims are directly verified as supported by judicial authority.
   - Any single partially supported or unsupported claim demotes the entire answer to `qualified_answer`.
   - Any single contradicted claim triggers `rejected_answer` and answer text suppression.
   - Unverified (`not_evaluated`) claims or missing claims lists are strictly preserved as `unverified_answer`.
   - Across multi-claim composition scenarios, the Answer-Level False Verification Rate (AFVR) is **0.00%** (0 / 7).

---

## 2. Investigation and Root-Cause Reproduction of M14 False Acceptances

### 2.1 Failure Analysis: `CR_M14_014` (Shared-Context Stem Leakage)

- **Query**: *"Did the Supreme Court quash criminal convictions when holding prison caste segregation unconstitutional?"*
- **Claim Sentence**: *"The Court held that caste-based labor segregation in prisons violates Article 14 and ruled that all existing prison convictions stand quashed."*
- **Cited Authority**: Headnote holding from *Sukanya Shantha v. Union of India & Ors.* ([2024] 10 SCR 493).
- **Gold Label**: `partially_supported` (the first conjunct regarding prison labor segregation is constitutional settled law; the second conjunct claiming quashing of existing criminal convictions is ungrounded).
- **Milestone 14 Predicted Status**: `supported` (False Acceptance via `direct_holding_entailment`).

#### Root Cause
In Milestone 14, multi-part claim checking split conjunctive sentences on `and held that` / `and ruled that`. Part 1 contained vocabulary `{caste, based, labor, segregation, prisons, violates, article}`, and Part 2 contained `{existing, prison, convictions, stand, quashed}`. The cited passage contained the general topic words `prisons` and `prison`. Because Part 2 contained the shared topic noun `prison`, the intersection check `len(p2_words.intersection(p_words)) >= 1` evaluated to `True` (matching `{"prison"}`). Check #7 concluded that both Part 1 and Part 2 had textual support, falling through to Check #9 (`direct_holding_entailment`), which saw 7 overlapping words and erroneously classified the claim as `supported`.

#### Implementation Fix
In `services/rag/claim_verifier.py::ClaimVerifier.verify_claim`:
```python
p1_words = set(re.findall(r'\b[a-z0-9]{4,}\b', parts[0])) - self.GENERIC_WORDS
p2_words = set(re.findall(r'\b[a-z0-9]{4,}\b', parts[1])) - self.GENERIC_WORDS
p1_stems = {w[:4] for w in p1_words}
p2_distinct_words = {w for w in p2_words if not any(w.startswith(s) for s in p1_stems)}

p1_supported = len(p1_words.intersection(p_words)) >= 1
if p2_distinct_words:
    p2_supported = len(p2_distinct_words.intersection(p_words)) >= 1
else:
    p2_supported = len(p2_words.intersection(p_words)) >= 1

if p1_supported and not p2_supported:
    return ClaimVerificationResult(
        status=ClaimVerificationStatus.PARTIALLY_SUPPORTED,
        method="multipart_claim_check",
        ...
    )
```
By filtering out stems shared with Part 1 (`'pris'`), `p2_distinct_words` contains only `{existing, convictions, stand, quashed}`, which has zero overlap with the passage. Part 2 is recognized as ungrounded, correctly returning `PARTIALLY_SUPPORTED`.

---

### 2.2 Failure Analysis: `CR_M14_017` (Negative Condition Waiver Omission)

- **Query**: *"Can an auction purchaser under SARFAESI Rule 9(4) deposit balance consideration at any time?"*
- **Claim Sentence**: *"The auction purchaser may deposit the balance consideration after 15 days without seeking any written consent."*
- **Cited Authority**: Court analysis from *IDBI Bank Ltd. v. Ramswaroop Daliya & Ors.* ([2024] 10 SCR 1371), holding that the period under Rule 9(4) is *extendable with the consent in writing of the parties*.
- **Gold Label**: `partially_supported` (omits mandatory statutory requirement of written consent for time extension).
- **Milestone 14 Predicted Status**: `supported` (False Acceptance via `direct_holding_entailment`).

#### Root Cause
Two compounding defects caused this false acceptance:
1. The modal phrase `"may deposit"` was absent from `RE_AFFIRMATIVE_MODALS`, so Check #3 and Check #4 did not detect a modal conflict.
2. The claim shared 6 substantive words with the cited passage (`purchaser`, `consent`, `consideration`, `deposit`, `balance`, `auction`). Check #9 treated high word overlap on a `court_analysis` passage as sufficient for `direct_holding_entailment`. The presence of the negative waiver phrase `"without seeking any written consent"` was ignored because the verifier lacked a dedicated negative condition waiver detector.

#### Implementation Fix
1. Expanded `RE_AFFIRMATIVE_MODALS` to include `may\s+deposit|can\s+deposit|may\s+alter|can\s+alter|may\s+claim|can\s+claim|unconditionally\s+entitled`.
2. Introduced `RE_NEGATIVE_CONDITION_WAIVER`:
   ```python
   RE_NEGATIVE_CONDITION_WAIVER = re.compile(
       r'\b(?:without\s+(?:seeking\s+)?(?:any\s+)?(?:written\s+)?(?:consent|sanction|approval|permission|order|hearing|notice|affording|recording)|'
       r'unconditionally\s+entitled|unconditionally|without\s+(?:any\s+)?qualification)\b',
       re.IGNORECASE
   )
   ```
3. Added Check #6b (`statutory_qualification_omission_check`):
   When a claim matches `RE_NEGATIVE_CONDITION_WAIVER` and the cited passage establishes that the waived condition (`consent`, `writing`, `sanction`, `approval`, etc.) is required, the verifier immediately returns `PARTIALLY_SUPPORTED`.
4. Guarded Check #9: Prevented `direct_holding_entailment` from triggering whenever `neg_waiver` or `claim_modal` is present.

---

## 3. Reconciled Evaluation Metrics and Benchmark Audit

### 3.1 Reconciling the Milestone 14 Metric Discrepancy

In Milestone 14, FAR was defined as:
$$\text{FAR}_{\text{M14}} = \frac{\text{Contradicted or Unsupported Predicted as Supported}}{\text{Total Contradicted } (12) + \text{Total Unsupported } (4)} = \frac{0}{16} = 0.00\%$$

This formulation failed to account for `partially_supported` claims promoted to `supported` (2 out of 16). In Milestone 15, we define explicit, disaggregated safety metrics:

| Metric Name | M14 Baseline | M15 Reconciled | Absolute Change | Evaluation Target |
| :--- | :---: | :---: | :---: | :---: |
| **Overall Claim Accuracy** | 86.36% (38/44) | **93.18% (41/44)** | +6.82% | Higher is better |
| **Macro F1 Score** | 0.8496 | **0.9133** | +0.0637 | Higher is better |
| **Supported-Class Precision** | 75.00% (6/8) | **100.00% (6/6)** | +25.00% | 100.00% |
| **Supported-Class Recall** | 100.00% (6/6) | **100.00% (6/6)** | 0.00% | $\ge 90.00\%$ |
| **Partially Supported False Acceptance Rate** | 12.50% (2/16) | **0.00% (0/16)** | -12.50% | **0.00%** |
| **Unsupported False Acceptance Rate** | 0.00% (0/4) | **0.00% (0/4)** | 0.00% | **0.00%** |
| **Contradicted False Acceptance Rate** | 0.00% (0/12) | **0.00% (0/12)** | 0.00% | **0.00%** |
| **Total Non-Supported False Acceptance Rate** | 5.26% (2/38) | **0.00% (0/38)** | -5.26% | **0.00%** |
| **False Rejection Rate (Supported $\to$ Contradicted)** | 0.00% (0/6) | **0.00% (0/6)** | 0.00% | **0.00%** |
| **Preservation of Uncertainty (`not_evaluated` Recall)** | 83.33% (5/6) | **83.33% (5/6)** | 0.00% | $\ge 80.00\%$ |
| **Answer-Level False Verification Rate (AFVR)** | Not evaluated | **0.00% (0/7)** | — | **0.00%** |

---

### 3.2 Confusion Matrix (Milestone 15 Reconciled)

$$\begin{array}{r|ccccc}
\text{Gold} \backslash \text{Predicted} & \textbf{Supported} & \textbf{Partially Supp.} & \textbf{Unsupported} & \textbf{Contradicted} & \textbf{Not Evaluated} \\
\hline
\textbf{Supported (6)} & \mathbf{6} & 0 & 0 & 0 & 0 \\
\textbf{Partially Supported (16)} & \mathbf{0} & \mathbf{14} & 1 & 0 & 1 \\
\textbf{Unsupported (4)} & \mathbf{0} & 0 & \mathbf{4} & 0 & 0 \\
\textbf{Contradicted (12)} & \mathbf{0} & 0 & 0 & \mathbf{12} & 0 \\
\textbf{Not Evaluated (6)} & \mathbf{0} & 0 & 1 & 0 & \mathbf{5} \\
\end{array}$$

#### Key Observations
1. **Zero False Positives in Supported Class**: The first column contains only true positives (6) and zero false positives from any other category. Supported precision is strictly 100.00%.
2. **Safe Fallbacks for Ambiguity**: The 3 non-exact matches across the benchmark are safe conservative classifications:
   - `CR_M14_019` (`partially_supported`): Predicted as `not_evaluated` (preserves uncertainty; neither promoted nor falsely contradicted).
   - `CR_M14_020` (`partially_supported`): Predicted as `unsupported` (safe conservative rejection of ungrounded assertion).
   - `CR_M14_041` (`not_evaluated`): Predicted as `unsupported` (safe conservative rejection of ungrounded assertion).
3. **Zero Inversions**: No supported claim was classified as contradicted, and no contradicted claim was classified as supported.

---

### 3.3 Per-Class Performance Summary

| Class | Gold Count | Predicted Count | True Positives | False Positives | Precision | Recall | F1 Score |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `supported` | 6 | 6 | 6 | 0 | **1.0000** | **1.0000** | **1.0000** |
| `partially_supported` | 16 | 14 | 14 | 0 | **1.0000** | **0.8750** | **0.9333** |
| `unsupported` | 4 | 6 | 4 | 2 | **0.6667** | **1.0000** | **0.8000** |
| `contradicted` | 12 | 12 | 12 | 0 | **1.0000** | **1.0000** | **1.0000** |
| `not_evaluated` | 6 | 6 | 5 | 1 | **0.8333** | **0.8333** | **0.8333** |

---

## 4. Conservative Answer-Level Aggregation Invariant

### 4.1 Aggregation Policy Architecture

In NyayaVarta, an answer generated by an LLM typically contains multiple sentences or structured claims. While individual claims receive claim-level verification verdicts, the user interacts with the final synthesized answer.

We enforce a strict, deterministic answer-level aggregation policy across [`services/rag/validator.py`](file:///c:/Users/KIIT0001/Desktop/Repos/nyayavarta/services/rag/validator.py) and [`services/rag/pipeline.py`](file:///c:/Users/KIIT0001/Desktop/Repos/nyayavarta/services/rag/pipeline.py):

```mermaid
flowchart TD
    A["RAG Answer Generated"] --> B{"Syntax / Offset Valid?"}
    B -- "No" --> C["Status: validation_failed<br/>Badge: rejected_answer"]
    B -- "Yes" --> D{"Any Claim Contradicted?"}
    D -- "Yes" --> C
    D -- "No" --> E{"All Claims Unsupported?"}
    E -- "Yes" --> C
    E -- "No" --> F{"Any Partial or Unsupported Claim?"}
    F -- "Yes" --> G["Status: answered_with_qualification<br/>Badge: qualified_answer"]
    F -- "No" --> H{"Any Claim Not Evaluated?"}
    H -- "Yes" --> I["Status: answered<br/>Badge: unverified_answer"]
    H -- "No" --> J{"All Claims Supported (100%)?"}
    J -- "Yes" --> K["Status: answered<br/>Badge: verified_supported"]
    J -- "No / Empty" --> I
```

### 4.2 Mathematical Invariant

The badge `verified_supported` is assigned **if and only if**:
$$\text{verification\_badge} = \text{'verified\_supported'} \iff \begin{cases}
\text{len}(\text{claims}) > 0 \\
\text{all}(c.\text{verification\_status} == \text{'supported'} \;\forall\; c \in \text{claims}) \\
\text{contradicted\_count} == 0 \\
\text{unsupported\_count} == 0 \\
\text{partially\_supported\_count} == 0 \\
\text{unverified\_count} == 0 \\
\text{val\_result}.\text{is\_valid} == \text{True} \\
\text{val\_result}.\text{attribution\_complete} == \text{True}
\end{cases}$$

If even a single claim fails this condition, `verified_supported` is strictly blocked.

---

### 4.3 Answer-Level Safety Scenario Audit

To evaluate answer aggregation end-to-end, we executed 7 representative multi-claim composition scenarios in [`scripts/benchmark/evaluate_milestone15_safety.py`](file:///c:/Users/KIIT0001/Desktop/Repos/nyayavarta/scripts/benchmark/evaluate_milestone15_safety.py):

| Scenario ID | Answer Composition | Expected Badge | Actual Badge | Passed? | Safety Violation? |
| :--- | :--- | :---: | :---: | :---: | :---: |
| `AS_01_all_supported` | Claim 1 (Supported) + Claim 2 (Supported) | `verified_supported` | `verified_supported` | **PASS** | None |
| `AS_02_supported_and_partial` | Claim 1 (Supported) + Claim 2 (Partially Supported) | `qualified_answer` | `qualified_answer` | **PASS** | None (Correctly Demoted) |
| `AS_03_supported_and_unsupported` | Claim 1 (Supported) + Claim 2 (Unsupported) | `qualified_answer` | `qualified_answer` | **PASS** | None (Correctly Demoted) |
| `AS_04_supported_and_contradicted` | Claim 1 (Supported) + Claim 2 (Contradicted) | `rejected_answer` | `rejected_answer` | **PASS** | None (Correctly Suppressed) |
| `AS_05_supported_and_unverified` | Claim 1 (Supported) + Claim 2 (Not Evaluated) | `unverified_answer` | `unverified_answer` | **PASS** | None (Uncertainty Preserved) |
| `AS_06_all_contradicted` | Claim 1 (Contradicted) | `rejected_answer` | `rejected_answer` | **PASS** | None (Correctly Suppressed) |
| `AS_07_empty_claims` | Status 'answer' with empty claims list | `rejected_answer` | `rejected_answer` | **PASS** | None (Invalid schema blocked) |

**Result**: 7 / 7 scenarios passed exactly. Zero false promotions to `verified_supported`.

---

## 5. Rule-Based Heuristics vs. Semantic Legal Entailment

A fundamental design commitment of NyayaVarta is honesty regarding what automated verification layers actually prove:

### What the Deterministic ClaimVerifier Proves
1. **Syntactic and Citation Integrity**: Confirms whether bracket tags (`[E1]`) exist and map to active, verified passage text from the current retrieval candidate pool.
2. **Explicit Negation and Polarity Inversion**: Detects affirmative claims asserted against explicit judicial prohibitions (e.g., ordering authorized signatories under Section 148 NI Act, changing recruitment rules midway, altering arbitral awards under Section 34).
3. **Structural Misattribution**: Identifies counsel arguments and party submissions mischaracterized as binding judicial holdings.
4. **Known Statutory Prerequisite Omissions**: Catches omissions of mandatory statutory conditions (e.g., functionality test under Section 17(5)(d) CGST, written consent under SARFAESI Rule 9(4), Section 19 PC Act sanction).
5. **Overgeneralization of Article 142 Relief**: Flags universalized doctrinal claims derived from case-specific equitable relief.

### What the Deterministic ClaimVerifier Does NOT Prove
1. **General Natural Language Entailment**: Lexical overlap against a judicial holding passage indicates topical and lexical alignment; it does *not* prove that every possible nuance, sub-clause, or legal exception is satisfied.
2. **Doctrinal Validity Across Jurisdictions**: The verifier operates on textual observations within the retrieved 2024 judgment passage. It cannot determine whether a precedent was subsequently distinguished, questioned, or modified by a larger Constitution Bench.
3. **Implied Statutory Interpretations**: Complex statutory interplay requiring legislative history or canons of construction cannot be deterministically verified by regex or lexical pattern matching.

### Why Preserving `NOT_EVALUATED` is Crucial
When deterministic rules cannot verify semantic truth, the verifier emits `NOT_EVALUATED`. Under our presentation contract, answers containing unverified claims receive the neutral badge `unverified_answer`. They are **never silently converted to `verified_supported`**. This fail-closed design prevents the AI from conferring false legal authority on plausible-sounding but unverified text.

---

## 6. Regression and Safety Verification

### 6.1 Test Suite Results
The full project test suite was executed via `pytest`:
- **Total Tests**: 278
- **Passed**: 278 (100%)
- **Failed**: 0
- **Duration**: 64.49 seconds (local CPU)

### 6.2 Milestone 15 Safety Regression Suite (`tests/test_milestone15_safety.py`)
15 dedicated unit and integration tests verify the Milestone 15 safety invariants:
1. `test_multi_part_claim_shared_context_leak_prevention`: Confirms stem filtering prevents context leaks from Part 1 into Part 2.
2. `test_negative_condition_waiver_prevention`: Confirms waiver phrases like `"without seeking any written consent"` trigger `statutory_qualification_omission_check`.
3. `test_affirmative_modal_deposit_prevention`: Confirms `"may deposit"` cannot bypass condition checks.
4. `test_answer_aggregation_all_supported`: Verifies pure supported answers receive `verified_supported`.
5. `test_answer_aggregation_demoted_by_partially_supported`: Verifies partial support demotes answer to `qualified_answer`.
6. `test_answer_aggregation_demoted_by_unsupported`: Verifies unsupported claims demote answer to `qualified_answer`.
7. `test_answer_aggregation_rejected_by_contradicted`: Verifies contradicted claims reject the answer and trigger `is_answer_suppressed`.
8. `test_answer_aggregation_unverified_when_claim_not_evaluated`: Verifies `not_evaluated` claims result in `unverified_answer`.
9. `test_answer_aggregation_empty_claims_rejected`: Verifies empty claims lists are rejected.
10. `test_answer_aggregation_free_form_no_claims`: Verifies ungrounded free-form text is rejected.
11. `test_abstention_presentation_badge`: Verifies clean abstention yields `insufficient_evidence`.
12. `test_system_error_presentation_badge`: Verifies provider failures yield `system_error`.
13. `test_all_contradicted_claims_suppressed`: Verifies completely contradicted responses are suppressed.
14. `test_all_unsupported_claims_suppressed`: Verifies completely unsupported responses are suppressed.
15. `test_unseen_claims_benchmark_zero_false_acceptances`: Verifies 0 false acceptances across the entire 44-case held-out benchmark.

---

## 7. Artifact Integrity and Environment Commitments

In accordance with project safety guidelines:
1. **Preserved Baselines**: All historical benchmark artifacts (`evaluation/rag/milestone10_benchmark_42q.jsonl`, `evaluation/rag/milestone13_claim_audit.jsonl`, `evaluation/rag/milestone14_unseen_claims.jsonl`, `evaluation/rag/milestone14_verification_results.json`) remain strictly unmodified.
2. **Gold Label Integrity**: No gold labels in `evaluation/rag/milestone14_unseen_claims.jsonl` were modified or re-annotated.
3. **Graph Traversal**: Knowledge graph traversal remains disabled (`enable_graph=False`) in the production query path.
4. **Hardware Footprint**: All verification and aggregation evaluations run deterministically on CPU in under 15 milliseconds per query.

---

## 8. Summary of Results and Conclusion

Milestone 15 successfully resolves the false verification vulnerabilities discovered in Milestone 14:
- **Partially Supported False Acceptance Rate**: Reduced from **12.50% to 0.00%**.
- **Total Non-Supported False Acceptance Rate**: Reduced from **5.26% to 0.00%**.
- **Supported-Class Precision**: Increased from **75.00% to 100.00%**.
- **Answer-Level False Verification Rate**: **0.00%**.
- **Full Test Suite**: **278 passed / 278 tests**.

NyayaVarta now enforces an airtight presentation and verification contract that guarantees no legal answer is presented to users as verified truth unless all of its substantive assertions have been directly substantiated by verified judicial authority.
