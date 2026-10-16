# Final Review Pack Audit and Discrepancy Report

**Milestone**: Final Audit, Safety Verification, and College Demo Readiness  
**Date**: October 16, 2026  
**Auditor**: Automated Verification & Codebase Integrity Engine  
**Release Gate Status**: **HOLD (PENDING EXTERNAL LEGAL REVIEW)**  

---

## 1. Executive Summary

As part of the final evaluation and college demonstration readiness audit of NyayaVarta, a comprehensive data-integrity and provenance audit was conducted on the Milestone 25 Blinded Review Pack (`evaluation/rag/milestone25_reviewer_template.jsonl`) and its associated frozen mapping (`evaluation/rag/milestone25_frozen_mapping.json`).

The purpose of this audit is to guarantee that the evaluation benchmark presented for independent legal review is doctrinally sound, traceable to official Supreme Court judgment records, and free from silent metadata corruption.

### Key Audit Metrics
- **Total Cases Audited**: 30 cases across 9 legal categories.
- **Official Judgments Verified in Corpus**: 30 / 30 (100% of referenced document files exist in `data/processed/aws_sc/`).
- **Verbatim Corpus Excerpts**: 19 / 30 cases (15 exact character-slice matches, 4 normalized whitespace-adjusted matches).
- **Synthetic Adversarial Test Passages**: 11 / 30 cases (deliberately crafted in Milestone 16 to evaluate verifier behavior on rejected party submissions, inverted constitutional holdings, and quoted precedents).
- **Critical Metadata Discrepancies Identified**: 2 / 30 cases (`M25_REV_017` and `M25_REV_018`).
- **Integrity Policy Enforced**: Historical Milestone 25 files are preserved unchanged to protect SHA-256 evaluation hashes. Corrected and provenance-annotated versions are published as `milestone25_reviewer_template_v2.jsonl` and `milestone25_frozen_mapping_v2.json`.

---

## 2. In-Depth Root Cause Analysis of Discrepant Cases

### 2.1 Case M25_REV_017: SC/ST Act Bail vs. CPC Section 100

- **Case ID**: `M25_REV_017` (Original Blind Case ID: `M20_BLIND_017`)
- **Official Judgment**: *Shajan Skaria v. The State of Kerala and Anr.* (`2024_8_1086_1145`)
- **Legal Proposition**: *"Anticipatory bail can be granted in offences under the SC/ST Act without examining whether a prima facie case is made out."*
- **Source Passage**: *"Held: No – s.18 does not impose an absolute bar on the power of the courts to examine whether a prima facie case attracting the provisions of the 1989 Act is made out or not – The bar created by ss.18 and 18-A(i) shall not apply, if the complaint does not make out a prima facie case for application of the provisions..."* (Exact character slice `[928:1228]`).
- **M17/M20/M25 Historical Inconsistency**:
  - `statutory_and_doctrinal_context`: *"Code of Civil Procedure, 1908 (CPC): Section 100 jurisdiction of High Court in second appeals, strictly confined to substantial questions of law."*
  - `curated_sub_category`: `statutory_exception_cpc_section100`
  - `doctrinal_rationale`: *"Code of Civil Procedure, 1908 (CPC): Section 100 jurisdiction of High Court in second appeals..."*
- **Root Cause**:
  During the construction of `milestone20_blinded_review_pack.py` and `milestone25_reviewer_template.jsonl`, candidate cases from `milestone17_unseen_claims.jsonl` were indexed into categorized buckets. The script selected the legal proposition and passage for the *Shajan Skaria* judgment under category `statutory_exceptions_and_conditions`, but erroneously mapped the sub-category key and doctrinal rationale of the adjacent case (`cpc_section100`).
- **V2 Remediation**:
  In `milestone25_reviewer_template_v2.jsonl` and `milestone25_frozen_mapping_v2.json`, the metadata is restored to:
  - **Statutory Context**: *Scheduled Castes and the Scheduled Tribes (Prevention of Atrocities) Act, 1989: Section 18 and 18-A bar on anticipatory bail (Section 438 CrPC), and the constitutional exception permitting pre-arrest bail where the complaint fails to disclose a prima facie offence.*
  - **Sub-Category**: `statutory_exception_scst_act_bail`
  - **Doctrinal Rationale**: *SC/ST Act Section 18/18-A does not impose an absolute bar on pre-arrest bail if the complaint does not disclose a prima facie offence under the Act.*

---

### 2.2 Case M25_REV_018: Consumer Medical Negligence vs. Arbitration Limitation

- **Case ID**: `M25_REV_018` (Original Blind Case ID: `M20_BLIND_018`)
- **Official Judgment**: *Najrul Seikh v. Dr. Sumit Banerjee & Anr.* (`2024_2_1065_1071`)
- **Legal Proposition**: *"A consumer forum must decide medical negligence cases based on the report of the Medical Council."*
- **Source Passage**: *"Held: While the report of the Medical Council can be relevant for determining deficiency of service before a consumer forum, it cannot be determinative, especially when it contradicts the evidentiary findings made by a consumer forum..."* (Exact character slice `[941:1241]`).
- **M17/M20/M25 Historical Inconsistency**:
  - `statutory_and_doctrinal_context`: *"Arbitration and Conciliation Act, 1996: Section 34(3) proviso establishing a strict 30-day outer limit for condonation of delay, excluding Section 5 Limitation Act."*
  - `curated_sub_category`: `statutory_condition_arbitration_limitation`
  - `doctrinal_rationale`: *"Arbitration and Conciliation Act, 1996: Section 34(3) proviso establishing a strict 30-day outer limit..."*
- **Root Cause**:
  Identical index alignment defect in `create_milestone20_blinded_review_pack.py`. The proposition and passage regarding medical council reports under consumer protection law were coupled with the statutory rationale intended for Section 34(3) arbitration limitation challenges.
- **V2 Remediation**:
  In `milestone25_reviewer_template_v2.jsonl` and `milestone25_frozen_mapping_v2.json`, the metadata is restored to:
  - **Statutory Context**: *Consumer Protection Act, 2019 / 1986: Adjudication of deficiency of service in medical negligence claims, and the evidentiary status of Medical Council / expert opinions (relevant evidence, but non-binding and non-conclusive).*
  - **Sub-Category**: `statutory_condition_consumer_medical_negligence`
  - **Doctrinal Rationale**: *Consumer Protection Act: While a Medical Council report is relevant evidence before a Consumer Commission, it cannot be treated as conclusive or determinative over evidentiary findings.*

---

## 3. Analysis of Corpus Provenance (Verbatim vs. Synthetic)

The audit revealed that 11 of the 30 cases utilize synthetic adversarial passages. It is critical to distinguish between data corruption and intentional adversarial benchmark design:

1. **Verbatim Excerpts (19 Cases)**:
   - Sourced directly from 2024 Supreme Court judgments in `data/processed/aws_sc/`.
   - 15 cases match the exact character offset boundaries `[start_char:end_char]`.
   - 4 cases (`M25_REV_008`, `M25_REV_012`, `M25_REV_013`, `M25_REV_016`) match verbatim text in the judgment, but character offsets varied by minor whitespace normalization during OCR extraction. In V2, exact character offsets have been calibrated.

2. **Synthetic Adversarial Passages (11 Cases)**:
   - Originating in Milestone 16, these passages evaluate whether the verification engine can distinguish:
     - **Inverted Holdings**: e.g., `M25_REV_014` (*Kesavananda Bharati* basic structure inversion) and `M25_REV_015` (Patents Act Section 3(j) biological process patentability).
     - **Party Submissions vs. Court Holdings**: e.g., `M25_REV_019`, `M25_REV_020`, `M25_REV_021` where counsel's rejected arguments are synthetically framed to test if the model misidentifies submissions as law.
     - **Quoted Precedents vs. Operative Ratios**: e.g., `M25_REV_022`, `M25_REV_023`, `M25_REV_024` where historical landmark cases (*Lalita Kumari*, *D.K. Basu*, *Maneka Gandhi*) are cited in passing.
     - **Ambiguous Statutory Overlaps**: e.g., `M25_REV_028`, `M25_REV_029`, `M25_REV_030`.
   - In all 11 synthetic cases, the document ID references a genuine Supreme Court case, but the passage was synthetically constructed for test purposes.
   - **V2 Action**: In `milestone25_reviewer_template_v2.jsonl`, a new explicit field `"passage_provenance": "synthetic_adversarial_passage"` prevents human reviewers from assuming these passages are verbatim headnotes.

---

## 4. Comprehensive Audit Table (All 30 Cases)

| Case ID | Official Doc ID | Curated Category | Passage In Corpus | Offset Accuracy | Status | Audit Notes |
|:---|:---|:---|:---:|:---:|:---:|:---|
| `M25_REV_001` | `2024_12_28_67` | supported | Yes | Exact | PASS | Tej Prakash Pathak (Recruitment rules) |
| `M25_REV_002` | `2024_10_493_638` | supported | Yes | Exact | PASS | P. Mohanraj (IBC Section 14 moratorium) |
| `M25_REV_003` | `2024_10_393_410` | supported | Yes | Exact | PASS | Satender Kumar Antil (Bail guidelines) |
| `M25_REV_004` | `2024_11_713_721` | supported | Yes | Exact | PASS | Asian Resurfacing (Stay vacation overturned) |
| `M25_REV_005` | `2024_10_1371_1380` | partially_supported | Yes | Exact | PASS | SARFAESI Rule 9(4) balance deposit |
| `M25_REV_006` | `2024_10_45_53` | partially_supported | Yes | Exact | PASS | DV Act Section 25(2) modification |
| `M25_REV_007` | `2024_7_62_68` | partially_supported | Yes | Exact | PASS | PC Act Section 19 prior sanction |
| `M25_REV_008` | `2024_10_1359_1370` | partially_supported | Yes | Approximate | PASS | NCLT power to reject resolution plan (Offset calibrated) |
| `M25_REV_009` | `2024_3_36_45` | unsupported_with_valid_citation | Yes | Exact | PASS | Valid murder case citation paired with maritime claim |
| `M25_REV_010` | `2024_10_1359_1370` | unsupported_with_valid_citation | Yes | Exact | PASS | IBC resolution citation paired with copyright claim |
| `M25_REV_011` | `2024_11_713_721` | unsupported_with_valid_citation | Yes | Exact | PASS | Asian Resurfacing citation paired with rent control claim |
| `M25_REV_012` | `2024_12_28_67` | contradicted | Yes | Approximate | PASS | Direct negation of Tej Prakash rule (Offset calibrated) |
| `M25_REV_013` | `2024_12_1581_1617` | contradicted | Yes | Approximate | PASS | Arbitral award modification negation (Offset calibrated) |
| `M25_REV_014` | `2024_10_493_638` | contradicted | No | Synthetic | SYNTHETIC | Basic structure doctrine inversion test |
| `M25_REV_015` | `2024_10_154_314` | contradicted | No | Synthetic | SYNTHETIC | Patents Act Section 3(j) seed patentability inversion |
| `M25_REV_016` | `2024_10_393_410` | statutory_exceptions_and_conditions | Yes | Approximate | PASS | Section 436A CrPC mandatory bail (Offset calibrated) |
| `M25_REV_017` | `2024_8_1086_1145` | statutory_exceptions_and_conditions | Yes | Exact | FLAGGED | **SC/ST Act bail mislabeled as CPC Section 100** |
| `M25_REV_018` | `2024_2_1065_1071` | statutory_exceptions_and_conditions | Yes | Exact | FLAGGED | **Medical negligence mislabeled as Arbitration delay** |
| `M25_REV_019` | `2024_12_1581_1617` | party_submissions_vs_holdings | No | Synthetic | SYNTHETIC | Counsel submission on award modification |
| `M25_REV_020` | `2024_10_1448_1461` | party_submissions_vs_holdings | No | Synthetic | SYNTHETIC | Submission on premature remission immunity |
| `M25_REV_021` | `2024_10_1371_1380` | party_submissions_vs_holdings | No | Synthetic | SYNTHETIC | Submission on automatic forfeiture without notice |
| `M25_REV_022` | `2024_10_108_125` | quoted_precedents | No | Synthetic | SYNTHETIC | *Lalita Kumari* FIR registration precedent |
| `M25_REV_023` | `2024_10_493_638` | quoted_precedents | No | Synthetic | SYNTHETIC | *D.K. Basu* arrest guidelines precedent |
| `M25_REV_024` | `2024_10_393_410` | quoted_precedents | No | Synthetic | SYNTHETIC | *Maneka Gandhi* Article 21 due process precedent |
| `M25_REV_025` | `2024_10_393_410` | overgeneralized_holdings | Yes | Exact | PASS | Overgeneralized rule on economic offence bail |
| `M25_REV_026` | `2024_10_493_638` | overgeneralized_holdings | Yes | Exact | PASS | Overgeneralized corporate veil lifting |
| `M25_REV_027` | `2024_12_28_67` | overgeneralized_holdings | Yes | Exact | PASS | Overgeneralized public employment interview discretion |
| `M25_REV_028` | `2024_10_150_153` | ambiguous_claims | No | Synthetic | SYNTHETIC | Medical admission deadline waiver ambiguity |
| `M25_REV_029` | `2024_10_793_859` | ambiguous_claims | No | Synthetic | SYNTHETIC | Mall building plant CGST input tax credit |
| `M25_REV_030` | `2024_12_1581_1617` | ambiguous_claims | No | Synthetic | SYNTHETIC | Consumer forum vs arbitration concurrent remedies |

---

## 5. Artifact Preservation & Versioning Invariants

To adhere strictly to data integrity constraints:
1. **Zero Historical Mutation**:
   - `evaluation/rag/milestone25_reviewer_template.jsonl` (SHA-256 preserved).
   - `evaluation/rag/milestone25_frozen_mapping.json` (SHA-256 preserved).
   - All historical tests in `tests/test_milestone25_independent_review.py` continue to pass without modification.
2. **Version 2 Deliverables**:
   - `evaluation/rag/milestone25_reviewer_template_v2.jsonl`: Cleaned template with corrected statutory context for `M25_REV_017` and `M25_REV_018`, calibrated offsets for `M25_REV_008`, `012`, `013`, `016`, and explicit `"passage_provenance"` metadata. Blinding is preserved with 0 leaks of gold categories or system predictions.
   - `evaluation/rag/milestone25_frozen_mapping_v2.json`: Cleaned mapping linking each V2 case to corrected subcategories and doctrinal rationales.
   - `evaluation/rag/final_review_pack_audit.json`: Full machine-readable audit manifest containing 30 case audit records.

---

## 6. Review Status and Release Decision

Even with metadata calibration in Version 2, NyayaVarta's formal legal evaluation status remains:

$$\mathbf{Release\ Gate:\ HOLD\ (PENDING\_EXTERNAL\_REVIEW)}$$

- No independent human evaluation has been conducted.
- No legal conclusions or claims of clinical accuracy are made on the basis of developer-curated benchmarks.
- NyayaVarta is technically validated for educational and academic college project demonstration, but is **NOT AUTHORIZED FOR REAL-WORLD LEGAL PRACTICE OR CLIENT ADVICE**.
