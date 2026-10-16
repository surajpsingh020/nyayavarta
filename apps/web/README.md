# NyayaVarta Web Frontend (Phase 2A)

A lightweight, responsive, and accessible legal-research interface for the **NyayaVarta (न्यायवार्ता)** Supreme Court reasoning engine. Built with **React 18**, **TypeScript**, and **Vite**.

---

## 1. Features & Architecture

- **Legal Research Text Query Interface**: Dedicated query input with accessible keyboard shortcuts (`Ctrl` + `Enter`), inference provider selector (`mock`, `mock_partial`, `ollama`), and parameter controls (`top_k`, `max_passages`, structured output, compression).
- **Audit Demonstration Presets**: One-click execution of the 4 canonical evaluation queries:
  1. *Supported Rule*: Tej Prakash Pathak recruitment rules holding (`verified_supported`).
  2. *Missing Proviso*: SARFAESI Rule 9(4) balance deposit extension without borrower consent (`qualified_answer`).
  3. *Statutory Prohibition*: Section 3(j) Patents Act seed patentability contradiction (`insufficient_evidence` / `rejected_answer`).
  4. *Out of Corpus*: Admiralty limitation period (`insufficient_evidence`).
- **Safe Answer Presentation**: Prominent rendering of verification badges, fail-closed suppression of contradicted assertions, and highlighted clickable citation markers (`[E1]`).
- **Grounding & Evidence Panel**: Collapsible cards displaying all retrieved Supreme Court passages with document IDs, reporter citations, structural labels (`operative_holding`, `facts`, `submission`), and exact character spans `[start_char:end_char]`.
- **Claim-by-Claim Verification Audit**: Expandable audit table displaying sentence-level entailment statuses, detection methods, and specific audit rationales.
- **Fail-Closed Resilience**: Explicit handling of gateway timeouts (HTTP 504), local LLM unavailability (HTTP 503), client validation errors (HTTP 400), and backend disconnection.

---

## 2. Safe Answer Presentation Contract (Milestone 14)

The frontend is strictly bound by the NyayaVarta Legal Verification Contract. It **must never** represent unverified, contradicted, or speculative assertions as legally validated truth.

When displaying responses from `/v1/rag/query`, the UI client inspects `RAGResult.verification_badge` and `RAGResult.citation_validation`:

| `verification_badge` | UI Status Badge | Visual Treatment | Presentation Rule |
| :--- | :--- | :--- | :--- |
| `verified_supported` | **Verified Legal Authority** | Green badge / Verified icon | All claims directly supported by verified judicial authority. Display full answer and clickable citation offsets. |
| `qualified_answer` | **Qualified Answer** | Amber badge / Caution icon | One or more claims are partially supported or subject to unstated statutory qualifications. Display caveats and unresolved nuances prominently. |
| `unverified_answer` | **Unverified Legal Entailment** | Gray / Neutral badge | Syntactic citation references exist, but semantic legal entailment could not be established by deterministic rules. **MUST NOT** be labelled 'verified'. |
| `rejected_answer` | **Answer Rejected** | Red banner / Warning icon | Contains contradicted claims or completely unsupported assertions. The generated text is suppressed or hidden behind an explicit danger modal. |
| `insufficient_evidence` | **Insufficient Evidence in Corpus** | Blue / Info banner | The grounding gate or retriever determined that available judgments do not establish the requested legal proposition. Clean abstention. |
| `system_error` | **Infrastructure Unavailable** | Red alert banner | Local LLM timeout (HTTP 504) or provider unavailability (HTTP 503). Clearly distinct from a legal abstention. |

### Presentation Invariants

1. **Decoupled Citations**: The presence of valid bracket notation (e.g. `[E1]`) or matching passage IDs does *not* imply factual or legal accuracy. Syntactic validity and semantic support are presented distinctly.
2. **Never Elevate `NOT_EVALUATED`**: When claim verification status is `not_evaluated`, the UI displays neutral caution text. Silent conversion of `not_evaluated` into "verified" is strictly prohibited.
3. **Fail-Closed Contradiction Suppressions**: When `verification_badge == "rejected_answer"`, the system prevents users from inadvertently relying on inverted or contradicted holdings.

---

## 3. Getting Started

### Prerequisites
- Node.js >= 18 (Tested on Node.js v22.15.0)
- npm >= 9 (Tested on npm 11.2.0)
- NyayaVarta FastAPI backend running on `http://127.0.0.1:8000`

### Installation
```bash
# From the repository root
cd apps/web

# Install all dependencies
npm install
```

### Configuration
The backend API endpoint is configurable via environment variables:

| Variable | Default Value | Description |
|:---|:---|:---|
| `VITE_API_BASE_URL` | `""` (proxied to `http://127.0.0.1:8000`) | Base URL of the NyayaVarta FastAPI backend |

For custom remote backend endpoints, create an `.env` or `.env.local` file in `apps/web/`:
```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

### Running Development Server
```bash
# Start Vite development server with proxy on port 5173
npm run dev
```
Open `http://localhost:5173` in your browser.

### Running Test Suite
```bash
# Execute Vitest component, contract, and error-handling tests
npm test
```

### Production Build
```bash
# Typecheck with TypeScript and bundle production assets to dist/
npm run build

# Preview production build locally
npm run preview
```
