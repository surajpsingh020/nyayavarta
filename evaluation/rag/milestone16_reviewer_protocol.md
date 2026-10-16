# NyayaVarta Milestone 16 — Independent Legal Reviewer Protocol

## 1. Overview and Objective

This protocol governs the external, blinded legal verification of RAG-generated propositions against Supreme Court of India judgments (2024 SCR corpus).

The objective is to establish an objective standard for determining whether generated legal claims are legally and factually substantiated by their cited evidence passages, in full context of the source judgment.

---

## 2. Reviewer Independence and Blinding Guarantees

To ensure objective evaluation:
1. **No System Information**: The reviewer pack (`milestone16_reviewer_pack.jsonl`) contains no system predictions, model names, internal scores, or pipeline metadata.
2. **Context Window**: Each item provides:
   - `cited_passage`: The exact passage cited by the RAG system as evidence.
   - `preceding_context`: Surrounding text immediately preceding the cited passage in the official judgment.
   - `succeeding_context`: Surrounding text immediately following the cited passage.
   - Official judgment metadata (Case title, SCR citation, judgment date, source document ID, chunk index).
3. **No Prior Labels**: The reviewer pack provides `reviewer_label: null` and `reviewer_rationale: null`. Reviewers evaluate claims independently based solely on the source text and legal principles.

---

## 3. Legal Claim Verification Taxonomy

Every claim must be classified into exactly one of five standardized categories:

### A. `supported`
* **Definition**: The legal proposition asserted in the claim is fully and strictly substantiated by the cited passage in context.
* **Requirements**:
  - The holding, rule, or principle stated in the claim matches the court's actual determination.
  - All essential legal conditions, statutory qualifications, and prerequisites mentioned in the passage are honored.
  - The claim does not broaden a narrow fact-specific holding into an unrestricted general doctrine.
* **Example (from *Perumal Raja v. State*, [2024] 1 SCR 12) :**
  - *Claim*: "Under Section 27 of the Evidence Act, the disclosure statement of an accused is admissible only to the extent that it distinctly relates to the fact thereby discovered."
  - *Status*: `SUPPORTED` if the cited passage articulates this exact statutory limitation and ratio.

---

### B. `partially_supported`
* **Definition**: The claim captures some genuine aspects of the text, but omits a critical legal qualification, condition precedent, statutory exception, or procedural threshold, OR overgeneralizes a narrow ruling.
* **Requirements**:
  - The claim is not outright false or fabricated, but is misleading or incomplete without the missing qualification.
  - Omission of statutory caveats (e.g., "subject to Section 45 PMLA twin conditions", "only when fraud is pleaded with specificity", "unless waived by express writing").
* **Example (from *Gurwinder Singh v. State of Punjab*, [2024] 2 SCR 274) :**
  - *Claim*: "Bail may be granted under UAPA if the trial is unduly delayed."
  - *Context*: The Supreme Court held that mere delay does not automatically override Section 43D(5) UAPA unless constitutional rights under Article 21 are gravely violated as per *K.A. Najeeb*.
  - *Status*: `PARTIALLY_SUPPORTED` (omits the statutory threshold of Section 43D(5) and the required high threshold of constitutional deprivation).

---

### C. `unsupported`
* **Definition**: The cited passage does not substantiate the specific legal proposition asserted, even if the general subject matter or parties are related.
* **Requirements**:
  - The passage is silent on the key assertion of the claim.
  - The claim mentions rules or facts not found in or implied by the cited text.
  - Tangential relevance: The text mentions arbitration, but does not state the rule on arbitrator appointment asserted in the claim.
* **Example:**
  - *Claim*: "A cheque bounce complaint under Section 138 NI Act must be filed within 15 days of notice receipt."
  - *Cited Passage*: A discussion regarding the presumption of debt under Section 139 NI Act without any mention of the limitation period under Section 142.
  - *Status*: `UNSUPPORTED`.

---

### D. `contradicted`
* **Definition**: The cited passage or the context directly refutes, inverts, or negates the asserted claim.
* **Requirements**:
  - Inversion of holding: Asserting that the court allowed the appeal when it dismissed it, or held the appellant exempt when it held them liable.
  - Attributing rejected submissions: Asserting an argument made by the losing party or dissenting opinion as the binding ratio of the bench.
  - Inverting statutory interpretation: Claiming a provision is mandatory when the court held it directory, or vice versa.
* **Example (from *Bijay Agarwal v. M/s Medilines*, [2024] 5 SCR 785) :**
  - *Claim*: "The High Court was justified in setting aside the arbitral award because patent illegality was demonstrated."
  - *Holding/Passage*: The Supreme Court held that the High Court exceeded its Section 34 jurisdiction and that patent illegality was *not* made out, restoring the award.
  - *Status*: `CONTRADICTED`.

---

### E. `not_evaluated`
* **Definition**: The claim cannot be responsibly evaluated due to corrupted text, unreadable transcript, missing statutory context, or unintelligible drafting.
* **Requirements**:
  - Used sparingly when context is ambiguous or truncated in a manner that prevents fair legal assessment.

---

## 4. Key Legal Distinctions for Reviewers

Reviewers should apply the following legal tests:

1. **Party Submissions vs. Judicial Holding**:
   - Judgments frequently summarize the arguments of appellant and respondent counsel (e.g., "Mr. Senior Counsel contends that...").
   - A claim presenting an advocate's submission as the court's holding is `CONTRADICTED` if rejected, or `UNSUPPORTED` if not adopted.
2. **Quoted Precedent vs. Current Case Holding**:
   - The court often cites older precedents (e.g., *Maneka Gandhi*, *Kesavananda Bharati*).
   - If the claim asserts "In [Current 2024 Case], the Supreme Court held X", ensure the court actually applied or affirmed X, rather than distinguishing or departing from it.
3. **Statutory Provisos and Exceptions**:
   - If an assertion states an absolute rule (e.g., "An unstamped arbitration agreement is always void and cannot be acted upon"), but the 7-judge bench (*In Re Interplay*, [2024] 1 SCR 1) held that non-stamping is a curable defect that does not void the clause at referral stage, an absolute claim is `CONTRADICTED` or `PARTIALLY_SUPPORTED` depending on formulation.
4. **Discretionary / Article 142 Orders vs. Substantive Law**:
   - Orders passed under Article 142 to do "complete justice" between the parties cannot be generalized as standard statutory procedure without noting their exceptional nature.

---

## 5. Reviewer File Submission Format

Reviewers should record their evaluations in `evaluation/rag/milestone16_reviewer_template.jsonl`.
Each line must be a valid JSON object matching this schema:

```json
{
  "case_id": "M16_REV_001",
  "reviewer_label": "supported",
  "reviewer_rationale": "The cited passage in paragraph 14 explicitly lays down the twin requirements under Section 45 PMLA and confirms they apply to anticipatory bail.",
  "confidence": "high",
  "qualifications_identified": [],
  "reviewer_id": "REV_LEGAL_01"
}
```

### Valid Values:
- `reviewer_label`: `"supported"` | `"partially_supported"` | `"unsupported"` | `"contradicted"` | `"not_evaluated"` (lowercase).
- `confidence`: `"high"` | `"medium"` | `"low"`.
- `qualifications_identified`: Array of strings detailing any omitted legal conditions (required if `partially_supported`).
- `reviewer_rationale`: Brief explanation grounded in the text (mandatory).

---

## 6. Automated Validation and Rejection Criteria

When submitted to `scripts/benchmark/evaluate_milestone16_review.py`, entries are rejected if:
- `case_id` does not match an entry in the reviewer pack.
- `reviewer_label` is missing or not one of the 5 allowed enums.
- `reviewer_rationale` is empty or shorter than 10 characters.
- Duplicate evaluations for the same `case_id` from the same `reviewer_id` are detected.

---

## 7. Metrics Computed from Review

The evaluation runner calculates:
1. **Confusion Matrix**: System Predicted vs Reviewer Gold (5x5).
2. **False Acceptance Rates (FAR)**:
   - Contradiction FAR: % of `contradicted` claims predicted as `supported`.
   - Unsupported FAR: % of `unsupported` claims predicted as `supported`.
   - Partial FAR: % of `partially_supported` claims predicted as `supported`.
   - Overall Non-Supported FAR (must be 0.00% for strict safety).
3. **Class Precision, Recall, and F1**:
   - Specifically `supported` precision (must be 100% to guarantee safe answers).
4. **Answer-Level Promotion Safety**:
   - Verification that any answer containing non-supported claims is never awarded `verified_supported`.
5. **Multi-Reviewer Agreement**:
   - Cohen's Kappa / Fleiss' Kappa when multiple reviewer files are supplied.
