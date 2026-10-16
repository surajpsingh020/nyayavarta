# NyayaVarta Web Frontend

This directory contains the Next.js frontend skeleton and UI presentation specifications for the NyayaVarta Legal AI platform.

## Safe Answer Presentation Contract (Milestone 14)

The frontend is strictly bound by the NyayaVarta Legal Verification Contract. It **must never** represent unverified, contradicted, or speculative assertions as legally validated truth.

When displaying responses from `/v1/rag/query`, the UI client must inspect `RAGResult.verification_badge` and `RAGResult.citation_validation`:

| `verification_badge` | UI Status Badge | Visual Treatment | Presentation Rule |
| :--- | :--- | :--- | :--- |
| `verified_supported` | **Verified Legal Authority** | Green badge / Verified icon | All claims directly supported by verified judicial authority. Display full answer and clickable citation offsets. |
| `qualified_answer` | **Qualified Answer** | Amber badge / Caution icon | One or more claims are partially supported or subject to unstated statutory qualifications. Display caveats and unresolved nuances prominently. |
| `unverified_answer` | **Unverified Legal Entailment** | Gray / Neutral badge | Syntactic citation references exist, but semantic legal entailment could not be established by deterministic rules. **MUST NOT** be labelled 'verified'. |
| `rejected_answer` | **Answer Rejected** | Red banner / Warning icon | Contains contradicted claims or completely unsupported assertions. The generated text is suppressed or hidden behind an explicit danger modal. |
| `insufficient_evidence` | **Insufficient Evidence in Corpus** | Blue / Info banner | The grounding gate or retriever determined that available judgments do not establish the requested legal proposition. Clean abstention. |
| `system_error` | **Infrastructure Unavailable** | Red alert banner | Local LLM timeout (HTTP 504) or provider unavailability (HTTP 503). Clearly distinct from a legal abstention. |

### Presentation Invariants

1. **Decoupled Citations**: The presence of valid bracket notation (e.g. `[E1]`) or matching passage IDs does *not* imply factual or legal accuracy. Syntactic validity and semantic support must be presented distinctly.
2. **Never Elevate `NOT_EVALUATED`**: When claim verification status is `not_evaluated`, the UI must display neutral caution text. Silent conversion of `not_evaluated` into "verified" is strictly prohibited.
3. **Fail-Closed Contradiction Suppressions**: When `verification_badge == "rejected_answer"`, the system prevents users from inadvertently relying on inverted or contradicted holdings (e.g. holding inversions or misattributed counsel submissions).
