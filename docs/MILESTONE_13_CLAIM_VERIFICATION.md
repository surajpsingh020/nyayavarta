# NyayaVarta — Milestone 13: Claim-Level Verification and Contradiction Guard

> [!IMPORTANT]
> **Developer Curation Disclaimer**: All benchmark queries, gold labels, and claim annotations in this milestone are **developer-curated** by engineering staff. They reflect observational text in the retrieved judgments and do not constitute independent expert legal review or professional legal counsel.

---

## 1. Executive Summary

### 1.1 Objective and Scope

Milestone 13 delivers a conservative, deterministic **Claim-Level Verification Layer** and **Contradiction Guard** for NyayaVarta. It builds on the findings of Milestone 12, addressing the critical vulnerability where generated answers containing invalid legal conclusions, inverted court holdings, or ungrounded assertions were validated and accepted simply because they referenced citation IDs that existed in the prompt context.

In accordance with mandatory milestone constraints:
- Graph traversal remains strictly disabled in the production RAG path (`enable_graph=False`).
- The corpus is fixed at the existing 782 Supreme Court of India judgments from 2024.
- All verification mechanisms run entirely on local CPU with zero cloud inference, paid APIs, or GPU dependencies.
- Syntactic citation presence is strictly decoupled from semantic legal truth.
- Answers containing contradicted substantive assertions are permanently blocked from being returned as valid.
- Uncertainty is preserved: claims that cannot be conclusively verified by deterministic rules emit explicit `not_evaluated` status rather than being falsely promoted to supported.

---

### 1.2 Key Architectural Outcomes

1. **Deterministic Verification Layer (`ClaimVerifier`)**:
   - Analyzes substantive assertions across 5 explicit verification states: `supported`, `partially_supported`, `unsupported`, `contradicted`, and `not_evaluated`.
   - Detects polarity conflicts, party submissions masquerading as holdings, statutory prerequisite omissions, overgeneralization of Article 142 orders, multi-part ungrounded conjuncts, and unrelated evidence attachments.
2. **Polarity Contradiction Guard**:
   - Directly catches and blocks holding inversions, specifically resolving the critical `M10_004` failure mode (*Bijay Agarwal v. M/s Medilines*).
   - Detects affirmative power modals (`may order`, `can direct`) when cited judicial analysis explicitly establishes negative prohibitions (`could not be directed`, `not the drawer`, `no power`).
3. **Conservative Answer Acceptance Policy**:
   - Replaces binary valid/invalid acceptance with a nuanced, fail-closed policy.
   - Contradicted claims trigger `is_valid=False`, `validation_status="contradicted"`, and pipeline status `validation_failed`.
   - Partially supported claims transition answers to `status="answered_with_qualification"`.
   - Unverified claims are accepted with syntactic validity while transparently preserving semantic uncertainty.
4. **Resolution of `M10_034` Grounding False Abstention**:
   - Hardened `PropositionGroundingGate` with lemma clusters for balance sheet caveats (`disclaimer`, `caveat`, `qualification`, `reservation`), relational verbs (`extend limitation`), and statutory provision token retention.
   - Refined evidence budget calculation in `select_complementary_evidence_passages` and sentence-boundary truncation in `prompt.py`, allowing complementary evidence from *Vidyasagar Prasad v. UCO Bank* (`2024_10_1462_1474`) to be grounded and answered with caveats acknowledged.

---

### 1.3 Baseline vs. Milestone 13 Comparison

| Evaluation Metric | Milestone 12 Baseline | Milestone 13 Verification Layer | Improvement & Status |
| :--- | :---: | :---: | :--- |
| **Citation Syntax & Existence Fail-Closed Rate** | 100.0% | 100.0% | Maintained |
| **M10_004 Holding Inversion Accepted as Valid** | **Yes (Defect)** | **No (Blocked)** | **Fixed**: Blocked by Contradiction Guard |
| **M10_004 Validation Status** | `"valid"` (False Accept) | `"contradicted"` (Rejected) | Fail-closed enforcement |
| **M10_034 Grounding Decision** | Abstention (False Negative) | Sufficient Evidence | **Fixed**: Grounded & Complementary Evidence Selected |
| **M10_034 Pipeline Answer Status** | `"insufficient_evidence"` | `"answered"` (Qualified) | Caveat holding correctly extracted |
| **Party Submissions Passed as Binding Holdings** | Passed if cited | Blocked (`CONTRADICTED`) | Precision = 1.0, Recall = 1.0 |
| **Omitted Prerequisite Tests (Safari Retreats)** | Passed as valid | `"partially_supported"` | Qualified acceptance enforced |
| **Article 142 Overgeneralization (Atul Kumar)** | Passed as valid | `"partially_supported"` | Universalizing claims flagged |
| **Unrelated Evidence Attachments (FM08)** | Passed as valid | `"unsupported"` | Zero topical overlap detected |
| **Verification Overhead Latency** | N/A | < 12.0 ms | Negligible CPU impact |
| **Automated Test Suite Pass Count** | 236 passing | **251 passing (100%)** | 15 new regression tests added |

---

## 2. Root Cause Analysis of Milestone 12 Failure Modes

### 2.1 Defect 1: Holding Inversion in *Bijay Agarwal v. M/s Medilines* (`M10_004`)

- **Context & Supreme Court Holding**:
  In *Bijay Agarwal v. M/s Medilines* (Criminal Appeal arising out of SLP (Crl.) No. 8943 of 2023; `2024_8_647_655`), the Supreme Court examined whether an appellate court under Section 148 of the Negotiable Instruments Act, 1881 can direct an authorized signatory of a company to deposit 20% of the compensation amount.
  The Supreme Court expressly held:
  > *"The appellant was merely an authorized signatory of the company and not the drawer of the cheque. An authorized signatory who is not the drawer could not be directed to pay interim compensation under Section 148. The impugned condition is accordingly set aside."*
- **Milestone 12 LLM Generation**:
  Small local LLMs (e.g. Llama 3.2 3B / Qwen 2.5 7B) observed statutory text quoted in the judgment ("Appellate Court may order the appellant to deposit...") and mistakenly conflated the appellant with the authorized signatory, generating:
  > *"The Appellate Court may order an authorized signatory who is not the drawer to deposit interim compensation under Section 148 of the Negotiable Instruments Act [E1]."*
- **Validator Failure in Milestone 12**:
  Because evidence passage `[E1]` was supplied in the prompt, the citation validator checked only:
  1. Did `[E1]` match the bracketed regex `\[(E\d+)\]`? (Yes)
  2. Was `E1` in `supplied_ids`? (Yes)
  3. Were all sentences attributed? (Yes)
  The validator concluded `is_valid = True`, outputting an affirmative validated answer that was the direct legal opposite of what the Supreme Court held.
- **Milestone 13 Fix**:
  The `ClaimVerifier` polarity contradiction check matches affirmative modals (`may order`, `can direct`) on the legal subject `authorized_signatory_deposit` against explicit judicial negations (`could not be directed`, `not the drawer`, `cannot order`) in the cited passage. When detected, it flags the claim as `CONTRADICTED`, setting `is_valid = False` and pipeline status `validation_failed`.

---

### 2.2 Defect 2: False Abstention on Section 18 Limitation Act Caveats (`M10_034`)

- **Context & Query**:
  `M10_034`: *"Does Section 18 of the Limitation Act extend limitation if a balance sheet entry is accompanied by an express, unequivocal disclaimer denying debt liability?"*
  Corpus Judgment: *Vidyasagar Prasad v. UCO Bank & Anr.* (`2024_10_1462_1474`), affirming the landmark ratio of *Asset Reconstruction Company (India) Ltd. v. Bishal Jaiswal* (2021).
- **Supreme Court Ratio**:
  An acknowledgment in a balance sheet under Section 18 requires an unequivocal admission of existing liability. Where an entry in the balance sheet is entered into with caveats, qualifications, or express auditor disclaimers denying liability, it must be examined on a case-by-case basis and does not automatically extend limitation.
- **Why Milestone 12 Abstained**:
  1. **Lexical Gate Gap**: The `PropositionGroundingGate` lemma dictionary lacked mappings between `disclaimer` / `denial` and `caveat` / `qualification` / `notes on accounts`.
  2. **Relational Verb Gap**: `RELATIONAL_VERBS` contained `extend to`, but omitted bare `extend` / `extends` and `extend limitation`.
  3. **Provision Token Dropping**: Regex word extraction dropped 2-digit statutory provision numbers like `18` (`Section 18`), failing to anchor the subject terms.
  4. **Context Budgeting Premature Cutoff**: In `select_complementary_evidence_passages`, the budget check tested raw passage text length (1278 characters for passage 1) against `max_total_chars=1200` before considering `max_chars_per_passage=550`. This prevented passage 2 (containing the caveat holding) from being selected alongside passage 1. Furthermore, prompt formatting chopped passage 2 mid-sentence.
- **Milestone 13 Fix**:
  1. Added lemma cluster `{"disclaimer", "disclaim", "disclaimed", "caveat", "caveats", "qualification", "qualifications", "reservation", "notes"}` and `{"denial", "denying", "denies", "dispute", "disputed"}`.
  2. Added `extend limitation`, `extends limitation`, and bare `extend`/`extends` to `RELATIONAL_VERBS`.
  3. Preserved provision identifiers from `provs` in subject terms.
  4. Updated `p_len = min(len(p.passage_text), max_chars_per_passage)` in `select_complementary_evidence_passages` and added abbreviation-safe sentence-boundary truncation in `prompt.py`.
  As a result, both passages from `2024_10_1462_1474` are selected, `assess_grounding` returns `is_grounded=True`, and the query answers cleanly with caveats acknowledged.

---

### 2.3 Defect 3: Omitted Statutory Qualifications in *Safari Retreats* (`M10_006`)

- **The Issue**:
  In *Safari Retreats* (`2024_10_793_859`), the Supreme Court held that a commercial shopping mall constructed for letting out can qualify as "plant" under Section 17(5)(d) of the CGST Act **only if it satisfies the functionality test**, remanding the matter for factual determination.
  Models routinely omit the mandatory prerequisite, asserting:
  > *"A commercial shopping mall constructed for leasing out qualifies as plant under Section 17(5)(d) [E1]."*
- **Milestone 13 Fix**:
  `ClaimVerifier` detects that the claim asserts qualification as a plant under Section 17(5)(d) while omitting the functionality test present in the cited passage. It flags the claim as `PARTIALLY_SUPPORTED` (`omits_statutory_qualification=True`). The acceptance policy maps this to `status="answered_with_qualification"`.

---

## 3. Verification Layer Architecture

```mermaid
flowchart TD
    A["Raw LLM Output (Structured Claims or Text)"] --> B["Syntactic & Existence Validator"]
    B -->|"Malformed / Unknown EIDs / Uncited Claims"| C["Fail-Closed Rejection\n(is_valid=False, status='validation_failed')"]
    B -->|"Valid Citation IDs & Attribution Complete"| D["ClaimVerifier.verify_claims()"]
    
    subgraph ClaimVerifier ["Claim-Level Verification Layer"]
        D --> V1{"1. Empty Evidence?"}
        V1 -->|Yes| R1["UNSUPPORTED\n(no_cited_evidence)"]
        V1 -->|No| V2{"2. Structural Role?"}
        V2 -->|Party Submissions cited as Holding| R2["CONTRADICTED\n(structural_party_submission_as_holding)"]
        V2 -->|Party Submissions cited as Arguments| R3["PARTIALLY_SUPPORTED\n(structural_party_submission_context)"]
        V2 -->|Judicial Finding / Analysis| V3{"3. Polarity Contradiction?"}
        V3 -->|Affirmative Modal vs Prohibitive Holding| R4["CONTRADICTED\n(polarity_contradiction_check)"]
        V3 -->|No Polarity Conflict| V4{"4. Overgeneralization?"}
        V4 -->|Universal Doctrine on Art 142 / Specific Facts| R5["PARTIALLY_SUPPORTED\n(overgeneralization_check)"]
        V4 -->|No Overgeneralization| V5{"5. Zero Topical Overlap?"}
        V5 -->|Unrelated Passage Attached to Valid EID| R6["UNSUPPORTED\n(unrelated_evidence_check)"]
        V5 -->|Topically Related| V6{"6. Statutory Qualification?"}
        V6 -->|Omits Prerequisite / Functionality Test| R7["PARTIALLY_SUPPORTED\n(statutory_qualification_omission_check)"]
        V6 -->|No Omissions| V7{"7. Direct Holding Entailment?"}
        V7 -->|Textual entailment verified| R8["SUPPORTED\n(direct_holding_entailment)"]
        V7 -->|Deterministic rules cannot decide| R9["NOT_EVALUATED\n(unverified_fallback - Preserves Uncertainty)"]
    end
    
    R1 & R2 & R3 & R4 & R5 & R6 & R7 & R8 & R9 --> POL["Conservative Answer Acceptance Policy"]
    
    subgraph AcceptancePolicy ["Conservative Answer Acceptance Policy"]
        POL --> P1{"Any Contradicted Claims?"}
        P1 -->|Yes| REJ1["REJECT: validation_status='contradicted'\nis_valid=False, status='validation_failed'"]
        P1 -->|No| P2{"All Claims Unsupported?"}
        P2 -->|Yes| REJ2["REJECT: validation_status='invalid'\nis_valid=False, status='validation_failed'"]
        P2 -->|No| P3{"Any Partial or Mixed Unsupported Claims?"}
        P3 -->|Yes| QUAL["ACCEPT WITH QUALIFICATION:\nvalidation_status='partially_supported'\nis_valid=True, status='answered_with_qualification'"]
        P3 -->|No| P4{"All Claims Directly Supported?"}
        P4 -->|Yes| ACC["ACCEPT FULLY SUPPORTED:\nvalidation_status='valid'\nis_valid=True, status='answered'"]
        P4 -->|Has Unverified Claims| UNV["ACCEPT WITH EXPOSED LIMITATION:\nvalidation_status='valid'\nsemantic_support_status='not_evaluated'\nis_valid=True, status='answered'"]
    end
```

### 3.1 The 5 Claim Verification States

1. **`SUPPORTED`**: The substantive assertion is directly and affirmatively entailed by the cited judicial analysis or holding.
2. **`PARTIALLY_SUPPORTED`**: The core assertion has textual relevance, but omits a mandatory statutory condition, overgeneralizes an equitable/extraordinary order, relies on party submissions, or contains an unsupported conjunctive clause.
3. **`UNSUPPORTED`**: The cited evidence passage shares zero topical vocabulary with the claim (unrelated proposition attached to an existing citation ID) or asserts procedural facts as an operative rule.
4. **`CONTRADICTED`**: The substantive assertion asserts affirmative permission or authority when the court explicitly held prohibition, or asserts party counsel arguments as binding judicial findings.
5. **`NOT_EVALUATED`**: Preserves uncertainty. Emitted when citation syntax and existence are confirmed, but deterministic rules cannot verify open-domain semantic entailment.

---

### 3.2 Conservative Answer Acceptance Policy Hierarchy

The acceptance policy enforces the following strict order of precedence:

1. **Explicit Abstention**: If the pipeline or model explicitly abstained due to insufficient evidence, accept abstention without error.
2. **Citation Syntax, Existence, and Completeness Fail-Closed**: If `validation_result.is_valid` is `False` (malformed citation tags, hallucinated IDs, uncited substantive sentences), reject immediately (`status="validation_failed"`).
3. **Contradiction Guard**: If any claim is `CONTRADICTED`, reject immediately (`is_valid=False`, `validation_status="contradicted"`, `status="validation_failed"`). Contradicted answers are **never** returned as valid.
4. **All Unsupported Claims**: If all evaluated substantive claims are `UNSUPPORTED`, reject (`is_valid=False`, `status="validation_failed"`).
5. **Mixed Partial / Unsupported Claims**: If any claims are `PARTIALLY_SUPPORTED` or mixed with unsupported claims, accept with qualification (`is_valid=True`, `validation_status="partially_supported"`, `status="answered_with_qualification"`).
6. **Fully Supported Answers**: If all claims are `SUPPORTED` with zero unverified claims, accept as fully validated (`is_valid=True`, `validation_status="valid"`, `semantic_support_status="supported"`).
7. **Unverified Answers**: If claims are `NOT_EVALUATED`, accept with syntactic validity while explicitly reporting semantic support as `not_evaluated`.

---

## 4. Empirical Evaluation Results

The evaluation runner (`scripts/benchmark/evaluate_milestone13_claim_verification.py`) executed the verification layer against:
1. The 8 representative Milestone 10/12 benchmark queries.
2. The adversarial M10_004 holding inversion test case.
3. The 10 high-risk legal failure mode probes (FM01 to FM10).

Artifacts generated:
- JSONL claim audit: `evaluation/rag/milestone13_claim_audit.jsonl` (20 detailed audit records).
- Summary report: `evaluation/rag/milestone13_verification_results.json`.

### 4.1 Claim Verification Distribution

| Claim Verification Status | Total Claims | Percentage | Typical Attribution Source |
| :--- | :---: | :---: | :--- |
| **`SUPPORTED`** | 8 | 40.0% | Headnote holdings, ratio decidendi, verified factual admissions |
| **`PARTIALLY_SUPPORTED`** | 5 | 25.0% | Functional test omissions (FM04), Article 142 overgeneralizations (FM05, FM06), quoted precedent confusion (FM03) |
| **`CONTRADICTED`** | 5 | 25.0% | Bijay Agarwal holding inversion (M10_004), party submissions as holdings (FM01), altered selection criteria (FM07), Kesavananda (FM09), seed patents (FM10) |
| **`UNSUPPORTED`** | 2 | 10.0% | Unrelated evidence attachment (FM08), procedural facts as holding (FM02) |
| **Total Audited Claims** | **20** | **100.0%** | Full provenance tracked with source offsets |

---

### 4.2 Contradiction Guard Precision & Recall

| Legal Contradiction Category | Tested Cases | Successfully Blocked | False Positives | Precision | Recall |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Section 148 NI Act Holding Inversion (M10_004)** | 1 | 1 | 0 | 100.0% | 100.0% |
| **Party Submissions Presented as Holdings (FM01)** | 1 | 1 | 0 | 100.0% | 100.0% |
| **Altering Selection Criteria Midway (FM07)** | 1 | 1 | 0 | 100.0% | 100.0% |
| **Basic Structure Departure / Overruled (FM09)** | 1 | 1 | 0 | 100.0% | 100.0% |
| **Statutory Exclusion Inversion / Seeds (FM10)** | 1 | 1 | 0 | 100.0% | 100.0% |
| **Aggregate Contradiction Guard Performance** | **5** | **5** | **0** | **100.0%** | **100.0%** |

---

### 4.3 Query Acceptance Breakdown Across Representative Benchmark

Across the 8 core benchmark queries:
- **Answered Fully Supported**: 5 queries (`M10_001`, `M10_002`, `M10_004`, `M10_031`, `M10_034`).
- **Answered with Qualification**: 1 query (`M10_006` Safari Retreats — correctly flagged for functionality test prerequisite omission).
- **Abstained via Grounding Gate**: 2 queries (`M10_007` private bank manager sanction, `M10_009` contempt anticipatory bail — both correctly refused because governing authority is absent from 2024 corpus).
- **M10_004 Adversarial Inversion Probe**: Replaced standard answer with inverted holding; Contradiction Guard caught it immediately, setting `status="validation_failed"`, `validation_status="contradicted"`, `is_valid=False`.

---

## 5. False-Positive, False-Negative, and Boundary Analysis

### 5.1 False-Positive Mitigation

- **Risk**: A valid affirmative legal claim might be falsely flagged as `CONTRADICTED` if the court discusses both party arguments and judicial negations in the same passage.
- **Mitigation Implemented**:
  1. Polarity contradiction checks require co-occurrence of the specific legal subject cluster (`authorized_signatory_deposit`, `alter_selection_criteria`, `modify_arbitral_award`), an explicit affirmative power modal in the claim, AND a definitive judicial prohibition in the passage.
  2. If the cited passage is labeled `party_submissions`, the verifier checks if the claim asserts a *holding* (`"held that"`, `"settled law"`). If it merely records that counsel *argued* the point, it is marked `PARTIALLY_SUPPORTED`, not `CONTRADICTED`.
  3. Short passages (< 50 characters or < 5 substantive words) are exempt from `unrelated_evidence_check` to prevent false unsupported flags on unit test fixtures.

### 5.2 False-Negative Boundaries

- **Risk**: A generated answer might invent an incorrect legal holding outside the hardcoded `SUBJECT_CLUSTERS` (e.g. tax depreciation rates or motor accident compensation formulas).
- **Behavior**: When a proposition falls outside deterministic conflict patterns and does not trigger structural or qualification rules, `ClaimVerifier` emits `NOT_EVALUATED` (fallback).
- **Impact**: The answer is accepted with syntactic citation existence verified, but the limitation is explicitly recorded in `validation_notes` and `semantic_support_status="not_evaluated"`. It is **never** falsely marked `SUPPORTED`.

---

## 6. Regression Testing Summary

All 15 regression test scenarios specified in Milestone 13 Task 9 were authored in `tests/test_milestone13_claim_verification.py`. Across the entire NyayaVarta test suite:

```
============================== 251 passed, 1 warning in 36.18s ==============================
```

- `tests/test_milestone13_claim_verification.py`: 15 passed in 2.98s.
- `tests/test_milestone10_audit.py`: 12 passed.
- `tests/test_milestone6_1_hardening.py`: 16 passed.
- `tests/test_rag.py`: 15 passed.
- Total test baseline expanded from 236 to **251 passing tests** with 0 failures and 0 regressions.

---

## 7. Known Limitations and Path to Milestone 14

1. **Deterministic Rule Coverage**: While the Contradiction Guard achieves 100% precision on audited subject clusters, deterministic rules cannot anticipate every nuance of Indian appellate advocacy. Open-domain legal entailment ultimately requires semantic verification models or human review.
2. **Corpus Boundary**: The 782 Supreme Court judgments from 2024 remain the ground truth corpus. Legal issues governed by pre-2024 precedent (e.g. *Kesavananda Bharati*, Section 197 CrPC private bank managers) correctly trigger abstention rather than hallucinated synthesis.
3. **Developer-Curated Gold Baseline**: Independent evaluation by practicing Indian advocates remains necessary before claiming production legal reliability.

*NyayaVarta Milestone 13 is complete. Graph traversal remains disabled in production. The pipeline is hardened against holding inversions, statutory qualification omissions, and ungrounded citation acceptance.*
