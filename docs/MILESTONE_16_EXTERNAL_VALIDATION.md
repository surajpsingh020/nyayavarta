# NyayaVarta — Milestone 16: Independent Legal Review and External Validation

## Executive Summary

Milestone 16 investigates the limits of developer-curated evaluation and establishes an external validation framework for NyayaVarta's claim-level verification, citation attribution, and safe answer presentation contracts.

Following Milestone 15, which enforced conservative answer-level aggregation and resolved false acceptances on the frozen 44-claim dataset, Milestone 16 was conducted under strict epistemic principles:
1. **Historical Evidence Audit**: Reconciled query counts, claim distributions, case reuse, and diagnostic vs. held-out data across Milestones 10–15.
2. **Blinded Legal Reviewer Pack**: Packaged 36 representative claims across 9 legal domains into `evaluation/rag/milestone16_reviewer_pack.jsonl` with surrounding paragraph context, judgment metadata, and complete stripping of system outputs and gold labels.
3. **Formal Reviewer Protocol**: Authored `evaluation/rag/milestone16_reviewer_protocol.md` establishing objective criteria and real Supreme Court precedents for five legal labels (`supported`, `partially_supported`, `unsupported`, `contradicted`, `not_evaluated`).
4. **Reproducible Evaluation Runner**: Built `scripts/benchmark/evaluate_milestone16_review.py` supporting schema validation, input rejection, 5×5 confusion matrices, disaggregated False Acceptance Rates (FAR), answer-level verification rates, and multi-reviewer inter-annotator agreement (Cohen's Kappa).
5. **Brand-New Evaluation on 20 Unstudied Judgments**: Evaluated the frozen system on 20 newly curated claims from 20 unstudied judgments across Volumes 1–9 and 11 of the 2024 SCR corpus, **without modifying any verifier code**.
6. **Empirical Reality Check**: Confirmed that while `supported` recall remained 100%, rule-based verification on unstudied legal text exhibits semantic blindness (Supported Precision: 62.5%, Non-Supported FAR: 20.0%), proving that deterministic lexical heuristics cannot substitute for substantive legal reasoning.
7. **Explicit Pending External Review**: In strict compliance with guidelines, independent review remains marked as `PENDING_EXTERNAL_REVIEW`—no reviewer feedback, credentials, or signatures have been fabricated.
8. **Test Suite Integrity**: Expanded test suite to **285 passing tests** (zero failures, zero regressions).

---

## 1. Audit of Historical Evaluation Evidence (Milestones 10–15)

To establish complete provenance, all historical datasets and benchmark artifacts were audited:

### Numerical Reconciliation Matrix

| Milestone | Dataset File | Total Queries | Substantive Claims | Judgment Docs Used | Dataset Role | Key Safety Finding / Outcome |
| :--- | :--- | :---: | :---: | :---: | :--- | :--- |
| **M10** | `milestone10_eval_dataset.json` | 42 | — | 18 | Retrieval & Multi-passage Benchmark | Disclosed 92.5% citation self-referencing; established 42-query test set. |
| **M10 Audit**| `milestone10_claim_audit.jsonl` | 10 | 10 | 10 | Grounding & Contradiction Probe | Detected *Bijay Agarwal* holding inversion (M10_004). |
| **M12** | `milestone12_claim_audit.jsonl` | 13 | 21 | 8 | Diagnostic / Failure Mode Audit | 8 live answers + 10 failure probes. 7 claims shared with M13. |
| **M13** | `milestone13_claim_audit.jsonl` | 13 | 20 | 8 | Verifier Development Set | Introduced Contradiction Guard and rule-based verification. |
| **M14** | `milestone14_unseen_claims.jsonl`| 44 | 44 | 20 | First Genuine Held-Out Set | 0 overlap with M12/M13. Uncovered 2 false acceptances (FAR = 6.25%). |
| **M15** | `milestone15_claim_audit.jsonl` | 44 | 44 | 20 | Frozen Regression Benchmark | Fixed stem leak & waiver omissions; achieved 100% precision & 0.00% FAR. |
| **M16** | `milestone16_unseen_claims.jsonl`| 20 | 20 | 20 | Unstudied Judgment Evaluation | 20 completely new judgments from Volumes 1–9, 11; frozen code test. |

### Case Reuse & Provenance Analysis
- **Total Unique Queries (M10–M15)**: 57 distinct queries.
- **Total Unique Claims Curated (M10–M15)**: 77 unique legal assertions.
- **Total Historical Judgments Studied**: 27 unique judgments (heavily concentrated in 2024 SCR Volumes 10 and 12).
- **Corpus Coverage**: Out of 782 Supreme Court judgments from 2024, 755 judgments (96.5%) remained completely unstudied prior to Milestone 16.

---

## 2. Reviewer Evaluation Pack Architecture

To enable credible external review by qualified legal counsel without bias, a blinded reviewer package was generated:

- **Pack File**: `evaluation/rag/milestone16_reviewer_pack.jsonl` (36 cases).
- **Template File**: `evaluation/rag/milestone16_reviewer_template.jsonl` (clean submission structure).
- **Secret Mapping**: `evaluation/rag/milestone16_reviewer_mapping.json` (quarantined ground truth and internal metadata).

### Distribution of Reviewer Pack (36 Cases)

| Legal Category | Count | Primary Doctrinal Issue Examined |
| :--- | :---: | :--- |
| `direct_holding_support` | 4 | Pure holdings directly substantiated by cited ratio decidendi. |
| `holding_inversion` | 4 | Direct reversal of court outcomes (e.g. quashing vs refusal to quash). |
| `statutory_condition_waiver` | 4 | Claims omitting written consent or statutory sanctions. |
| `multipart_claim_leak` | 4 | First conjunct supported, second conjunct fabricated/unsupported. |
| `party_submission_as_holding` | 4 | Advocate's rejected arguments asserted as binding judicial holding. |
| `overgeneralization` | 4 | Universalizing extraordinary Article 142 equitable relief into general doctrine. |
| `unrelated_citation` | 4 | Existing citation ID attached to an entirely unrelated legal proposition. |
| `quoted_precedent_attribution`| 4 | Attributing historical precedent quoted by the bench as the current holding. |
| `procedural_facts_as_holding` | 4 | Presenting procedural history or framing questions as operative law. |

### Blinding Guarantees
Each entry in `milestone16_reviewer_pack.jsonl` provides:
1. `case_id`: Blinded identifier (`M16_REV_001` through `M16_REV_036`).
2. `generated_claim`: The exact RAG-generated substantive assertion.
3. `exact_source_passage`: The exact passage cited by the RAG model.
4. `surrounding_context`: The cited passage embedded between `[PRECEDING TEXT]` and `[SUCCEEDING TEXT]` extracted from the official SCR report to prevent out-of-context misjudgments.
5. Official judgment citation, case title, date, and document ID.
6. `reviewer_label: null` and `reviewer_rationale: null`.

**Zero Internal Metadata**: Model names, system predictions, confidence scores, original review IDs, and historical gold labels are completely purged from the reviewer pack and verified via automated schema validation.

---

## 3. Formal Legal Reviewer Protocol

The protocol (`evaluation/rag/milestone16_reviewer_protocol.md`) defines five standard verification classes:

1. **`supported`**: The proposition is fully and strictly substantiated by the cited passage in the context of the judgment. No material conditions, qualifiers, or statutory thresholds are omitted.
2. **`partially_supported`**: The claim captures some genuine aspects of the text, but omits a critical legal qualification, condition precedent, statutory exception, or procedural threshold, OR overgeneralizes a narrow ruling.
3. **`unsupported`**: The cited passage does not substantiate the specific legal proposition asserted, even if the general subject matter or parties are related.
4. **`contradicted`**: The cited passage or the context directly refutes, inverts, or negates the asserted claim (e.g. claiming an appeal was allowed when dismissed, or attributing rejected arguments as the ratio).
5. **`not_evaluated`**: The claim cannot be responsibly evaluated due to corrupted text, unreadable transcript, missing statutory context, or unintelligible drafting.

### Specific Doctrinal Tests Provided to Reviewers
- **Party Arguments vs. Judicial Holding**: Summaries of advocate submissions must never be credited as the court's binding ratio.
- **Quoted Precedent vs. Current Bench Ratio**: Citing an earlier landmark case (*Maneka Gandhi*, *Kesavananda*) within a judgment does not mean the current bench formulated that rule.
- **Statutory Provisos and Exceptions**: Absolute claims omitting mandatory statutory conditions (e.g., Section 45 PMLA twin conditions, Section 58(c) TPA provisos) must be classified as `partially_supported` or `contradicted`.
- **Equitable / Article 142 Relief**: Fact-specific equitable relief cannot be generalized into general substantive law.

---

## 4. Evaluation Runner Implementation

The evaluation runner `scripts/benchmark/evaluate_milestone16_review.py` was developed to provide an end-to-end evaluation pipeline:

- **Pack Validation (`--validate-pack`)**: Enforces required fields, checks surrounding context markers, and validates zero blinding leakage.
- **Reviewer File Ingestion (`--review-file`)**: Validates case IDs against the pack, enforces the 5-label enum, rejects rationales shorter than 10 characters, and flags duplicates.
- **Confusion Matrix & Disaggregated FAR**: Computes a 5×5 matrix alongside:
  - $\text{Contradiction FAR} = \frac{\text{Contradicted Gold predicted as Supported}}{\text{Total Contradicted Gold}}$
  - $\text{Unsupported FAR} = \frac{\text{Unsupported Gold predicted as Supported}}{\text{Total Unsupported Gold}}$
  - $\text{Partially Supported FAR} = \frac{\text{Partially Supported Gold predicted as Supported}}{\text{Total Partially Supported Gold}}$
  - $\text{Overall Non-Supported FAR} = \frac{\text{All Non-Supported Gold predicted as Supported}}{\text{Total Non-Supported Gold}}$
- **Answer-Level Promotion Safety Audit**: Verifies that any answer containing a non-supported claim is never promoted to `verified_supported`.
- **Inter-Annotator Agreement (`--second-reviewer-file`)**: Calculates percentage agreement and Cohen's Kappa between multiple independent raters.

### Benchmark on Blinded Pack (36 Representative Cases)

When run against the ground-truth mapping (`milestone16_reviewer_mapping.json`), the internal system performance on this 36-case diagnostic set:

```
Total Cases: 36
Overall Accuracy: 91.67% (33/36)
Contradiction FAR: 0.00% (0/8)
Unsupported FAR: 0.00% (0/4)
Partially Supported FAR: 0.00% (0/16)
Overall Non-Supported FAR: 0.00% (0/28)
Supported Precision: 100.00% (4/4)
Supported Recall: 100.00% (4/4)
Answer-Level Safe Compliance Rate: 100.00% (0 safe promotions violated)
```

---

## 5. Empirical Evaluation on 20 Unstudied 2024 Judgments

To test generalization beyond historical development data, 20 brand-new claims were curated from 20 unstudied judgments across 10 distinct volumes of the 2024 SCR corpus.

**Crucially, no verifier rules were modified, added, or tuned for this evaluation.**

### Unseen Evaluation Dataset Summary (`evaluation/rag/milestone16_unseen_claims.jsonl`)

| Case ID | Source Document ID | SCR Volume & Subject | Ground Truth | System Prediction | Method Applied | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `M16_UNSEEN_001` | `2024_3_1009_1013` | Vol 3: Motor Vehicles / Multiplier | `supported` | `supported` | `direct_holding_entailment` | Match |
| `M16_UNSEEN_002` | `2024_7_1001_1030` | Vol 7: Land Acquisition S. 5A | `supported` | `supported` | `direct_holding_entailment` | Match |
| `M16_UNSEEN_003` | `2024_11_1042_1063`| Vol 11: High Court Judges Parity | `supported` | `supported` | `direct_holding_entailment` | Match |
| `M16_UNSEEN_004` | `2024_9_110_134` | Vol 9: PMLA Section 50 / ECIR | `supported` | `supported` | `direct_holding_entailment` | Match |
| `M16_UNSEEN_005` | `2024_4_121_150` | Vol 4: Caste Scrutiny Committee | `supported` | `supported` | `direct_holding_entailment` | Match |
| `M16_UNSEEN_006` | `2024_6_10_19` | Vol 6: Section 319 CrPC Threshold | `partially_supported` | `not_evaluated` | `unverified_fallback` | Safe demotion |
| `M16_UNSEEN_007` | `2024_7_1031_1039` | Vol 7: Section 306 IPC Abetment | `partially_supported` | **`supported`** | `direct_holding_entailment` | **False Accept** |
| `M16_UNSEEN_008` | `2024_5_1011_1037` | Vol 5: UAPA Section 43D(5) Bail | `partially_supported` | **`supported`** | `direct_holding_entailment` | **False Accept** |
| `M16_UNSEEN_009` | `2024_2_1001_1038` | Vol 2: Income Tax S. 194-H TDS | `partially_supported` | `not_evaluated` | `unverified_fallback` | Safe demotion |
| `M16_UNSEEN_010` | `2024_4_100_120` | Vol 4: Workman Definition S. 2(s) | `partially_supported` | `not_evaluated` | `unverified_fallback` | Safe demotion |
| `M16_UNSEEN_011` | `2024_8_1002_1023` | Vol 8: Mortgage Redemption | `partially_supported` | `not_evaluated` | `unverified_fallback` | Safe demotion |
| `M16_UNSEEN_012` | `2024_1_1062_1082` | Vol 1: Companies Act / Societies | `unsupported` | `unsupported` | `unrelated_evidence_check` | Match |
| `M16_UNSEEN_013` | `2024_5_1038_1055` | Vol 5: CrPC S. 436A Default Bail | `unsupported` | `unsupported` | `unrelated_evidence_check` | Match |
| `M16_UNSEEN_014` | `2024_8_1024_1046` | Vol 8: SARFAESI Land Exemption | `unsupported` | `unsupported` | `unrelated_evidence_check` | Match |
| `M16_UNSEEN_015` | `2024_9_135_149` | Vol 9: Maternity Benefit Act | `unsupported` | `not_evaluated` | `unverified_fallback` | Safe demotion |
| `M16_UNSEEN_016` | `2024_3_1004_1008` | Vol 3: Quashing Defrauding State | `contradicted` | `not_evaluated` | `unverified_fallback` | Safe demotion |
| `M16_UNSEEN_017` | `2024_1_1045_1061` | Vol 1: IBC SRA Deposit Extension | `contradicted` | `not_evaluated` | `unverified_fallback` | Safe demotion |
| `M16_UNSEEN_018` | `2024_2_1039_1053` | Vol 2: Reversal of Acquittal | `contradicted` | `partially_supported` | `multipart_claim_check` | Safe demotion |
| `M16_UNSEEN_019` | `2024_6_129_163` | Vol 6: Matrimonial Cruelty S. 498A | `contradicted` | `unsupported` | `unrelated_evidence_check` | Safe demotion |
| `M16_UNSEEN_020` | `2024_11_1013_1041`| Vol 11: Hindu Succession Act | `contradicted` | **`supported`** | `direct_holding_entailment` | **False Accept** |

### Evaluation Results Metrics (`evaluation/rag/milestone16_evaluation_results.json`)

```
================================================================================
MILESTONE 16 UNSEEN EVALUATION RESULTS (FROZEN VERIFIER ON 20 UNSTUDIED CASES)
================================================================================
Total Unseen Claims: 20
Overall Accuracy: 40.00% (8/20)

Disaggregated False Acceptance Rates (FAR):
  - Contradiction FAR:         20.00% (1 false acceptance / 5 contradicted claims)
  - Unsupported FAR:            0.00% (0 false acceptances / 4 unsupported claims)
  - Partially Supported FAR:   33.33% (2 false acceptances / 6 partially supported claims)
  - Overall Non-Supported FAR: 20.00% (3 false acceptances / 15 non-supported claims)

Per-Class Performance:
  - Supported:           Precision = 62.50% (5/8), Recall = 100.00% (5/5), F1 = 0.7692
  - Partially Supported: Precision =  0.00% (0/1), Recall =   0.00% (0/6), F1 = 0.0000
  - Unsupported:         Precision = 75.00% (3/4), Recall =  75.00% (3/4), F1 = 0.7500
  - Contradicted:        Precision =  0.00% (0/0), Recall =   0.00% (0/5), F1 = 0.0000
  - Not Evaluated:       Predicted = 7 cases (35.0% fell back to preserved uncertainty)

Safe Answer Aggregation Contract:
  - Total Single-Claim Answers Evaluated: 20
  - Safe Promotions Violated: 3
  - Safe Promotion Compliance Rate: 85.00% (17/20 answers kept safe from false verified badge)
================================================================================
```

---

## 6. Critical Analysis: The Limits of Rule-Based Lexical Verification

This empirical evaluation on unstudied judgments provides clear, objective evidence regarding the boundary between lexical matching and substantive legal reasoning:

### 1. The Fallacy of Lexical Alignment
In developer-curated benchmarks (M13–M15), specific phrases and legal patterns were added iteratively to handle the test cases. On those 44 claims, the system achieved 100% precision and 0.00% FAR.
However, on 20 completely new cases:
- `M16_UNSEEN_007` (Section 306 IPC abetment): The claim asserted that harassment alone suffices to convict. The cited passage discussed Section 306, Section 107, and harassment, but held that active instigation was mandatory. Because the claim shared overlapping words with the headnote holding, `direct_holding_entailment` falsely marked it as `supported`.
- `M16_UNSEEN_008` (UAPA bail): The claim asserted that a court may assess allegations without detailed analysis. The passage contained those words, but in the context of the Section 43D(5) mandatory bar. The verifier lacked a specific rule for this statute and promoted it to `supported`.
- `M16_UNSEEN_020` (Coparcenary partition exclusion): The claim inverted the outcome of the judgment regarding female partition rights. Because the polarity inversion regex was tuned for specific corporate and debt phrases rather than Hindu succession language, the verifier fell through to `direct_holding_entailment`.

### 2. The Role of Fallback Uncertainty
7 out of 20 claims (35.0%) were classified as `not_evaluated` because the verifier detected neither a registered contradiction pattern nor sufficient confidence.
- Under NyayaVarta's presentation contract, `not_evaluated` claims **never receive a verified badge**.
- This prevented 4 non-supported claims (including 2 direct contradictions) from being falsely verified, demonstrating the vital necessity of fail-closed architecture.

### 3. Conclusion for Independent Review
**Deterministic lexical rules cannot generally verify legal entailment.** While they effectively catch known regression patterns (such as explicit negation and structural role confusion), general legal verification requires qualified human legal review or rich semantic reasoning with strict external validation.

---

## 7. Status of Independent External Legal Review

In accordance with Mandatory Rules 4, 5, and 6:
- **Status**: `PENDING_EXTERNAL_REVIEW`.
- **Declaration**: No external legal counsel has completed the evaluation pack within this session.
- **Strict Compliance**:
  - No reviewer feedback, opinions, or annotations have been fabricated.
  - No fictitious bar numbers, signatures, or credentials have been created.
  - Passing automated regression tests are explicitly acknowledged as software integrity tests, **not as proof of human legal review**.

### Instructions for Independent Legal Annotators
Qualified legal reviewers should follow the instructions in [milestone16_reviewer_protocol.md](file:///c:/Users/KIIT0001/Desktop/Repos/nyayavarta/evaluation/rag/milestone16_reviewer_protocol.md):
1. Open [milestone16_reviewer_template.jsonl](file:///c:/Users/KIIT0001/Desktop/Repos/nyayavarta/evaluation/rag/milestone16_reviewer_template.jsonl).
2. For each `case_id`, examine `claim_sentence` against `exact_source_passage` and `surrounding_context`.
3. Provide `reviewer_label` (`supported`, `partially_supported`, `unsupported`, `contradicted`, `not_evaluated`).
4. Detail specific reasoning in `reviewer_rationale`.
5. Run the evaluation runner:
   ```powershell
   python scripts/benchmark/evaluate_milestone16_review.py --review-file path/to/completed_review.jsonl --output-file evaluation/rag/milestone16_external_report.json
   ```

---

## 8. Regression Suite and Safe Presentation Contract

A dedicated regression test suite was implemented in `tests/test_milestone16_validation.py` covering:
1. `test_reviewer_pack_schema_and_blinding`: Verifies zero data leakage, complete surrounding context markers, and null review fields across 36 pack cases.
2. `test_reviewer_mapping_integrity`: Validates 100% key and ID alignment between pack and secret ground truth mapping.
3. `test_reviewer_submission_validation_rejection`: Validates fail-closed rejection of invalid labels, missing rationales, and unknown IDs.
4. `test_cohens_kappa_calculation`: Verifies statistical inter-annotator agreement calculations.
5. `test_answer_presentation_contract_safety`: Proves that answers containing non-supported claims are rejected or demoted, never awarded `verified_supported`.
6. `test_milestone16_unseen_claims_dataset_integrity`: Ensures 20 unseen claims from 20 distinct unstudied 2024 judgments are validly structured.
7. `test_evaluation_runner_mapping_benchmark`: Runs the full benchmark pipeline and confirms 100% internal safety compliance.

### Overall Repository Test Results
```
============================== test session starts ==============================
rootdir: C:\Users\KIIT0001\Desktop\Repos\nyayavarta
collected 285 items

tests/test_api.py ...........                                             [  3%]
tests/test_claim_reviewer.py .............                                [  8%]
tests/test_dataset.py ...                                                 [  9%]
tests/test_etl.py .....                                                   [ 11%]
tests/test_extraction.py .............                                    [ 15%]
tests/test_extraction_validation.py ..........                            [ 19%]
tests/test_graph_integrity.py ................                            [ 24%]
tests/test_graph_retrieval.py ....                                        [ 26%]
tests/test_grounding_gate.py .........................                    [ 35%]
tests/test_milestone10_audit.py ...............                           [ 40%]
tests/test_milestone11_graph.py ................                          [ 46%]
tests/test_milestone12_answer_quality.py ................                 [ 51%]
tests/test_milestone13_claim_verification.py ..............               [ 56%]
tests/test_milestone14_unseen_verification.py ................            [ 62%]
tests/test_milestone15_safety.py ...............                          [ 67%]
tests/test_milestone16_validation.py .......                             [ 70%]
tests/test_milestone6_1_hardening.py .............                        [ 74%]
tests/test_milestone6_e2e.py .........                                    [ 77%]
tests/test_milestone7_structured.py ................                       [ 83%]
tests/test_milestone8_multipassage.py ................                    [ 89%]
tests/test_milestone9_structure_aware.py ................                 [ 94%]
tests/test_rag.py .............                                           [ 99%]
tests/test_retrieval.py ..                                                [100%]

============================== 285 passed in 145.15s ==============================
```

---

## 9. Summary of Deliverables

| Deliverable | Path | Description | Status |
| :--- | :--- | :--- | :--- |
| **Comprehensive Report** | `docs/MILESTONE_16_EXTERNAL_VALIDATION.md` | Full documentation of audit, reviewer pack, evaluation runner, unseen results, and analysis. | **Complete** |
| **Reviewer Evaluation Pack** | `evaluation/rag/milestone16_reviewer_pack.jsonl` | 36 blinded cases across 9 legal domains with surrounding paragraph context. | **Complete** |
| **Reviewer Protocol** | `evaluation/rag/milestone16_reviewer_protocol.md` | Objective legal definitions, Supreme Court examples, and submission guidelines. | **Complete** |
| **Reviewer Template** | `evaluation/rag/milestone16_reviewer_template.jsonl` | Clean submission structure for independent legal counsel. | **Complete** |
| **Secret Mapping** | `evaluation/rag/milestone16_reviewer_mapping.json` | Quarantined ground truth and internal prediction metadata. | **Complete** |
| **Evaluation Runner** | `scripts/benchmark/evaluate_milestone16_review.py` | Schema validator, rejection engine, FAR calculator, and Kappa evaluator. | **Complete** |
| **Unseen Claims Dataset** | `evaluation/rag/milestone16_unseen_claims.jsonl` | 20 newly curated claims from 20 unstudied judgments across 10 volumes. | **Complete** |
| **Unseen Results File** | `evaluation/rag/milestone16_evaluation_results.json` | Machine-readable metrics and disaggregated FARs for unstudied judgments. | **Complete** |
| **Regression Test Suite** | `tests/test_milestone16_validation.py` | 7 automated tests enforcing reviewer schema, rejection, and presentation safety. | **Complete** |

---

## 10. Constraints and Governance Adherence

- **Graph Traversal**: Remains strictly disabled in production (`enable_graph=False`).
- **No Corpus Expansion**: The 782-judgment corpus remains preserved without alteration.
- **No Paid APIs or Cloud GPUs**: All verification, benchmarking, and testing executed locally on standard CPU.
- **Truthful Status**: External review is marked as `PENDING_EXTERNAL_REVIEW`.
- **Milestone Boundary**: Milestone 16 is fully completed; Milestone 17 is not started.
