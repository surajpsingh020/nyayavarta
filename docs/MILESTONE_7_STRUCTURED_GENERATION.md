# NyayaVarta — Milestone 7: Structured Output and Citation-Constrained Generation Report

**Document Version:** 1.0.0  
**Status:** Completed & Validated  
**Benchmark Artifacts:** `evaluation/rag/milestone7_structured_comparison_report.json`, `evaluation/rag/milestone7_structured_claims.jsonl`  
**Evaluation Date:** October 2026  
**Provider / Model Evaluated:** Local Ollama (`v0.17.1`), `phi3.5:latest` (CPU, 8 threads)

---

## 1. Executive Summary

Milestone 7 addresses a critical vulnerability observed during free-form RAG generation in Milestone 6.1: **citation attribution cleavage and citation hallucinations**. When language models generate free-form text with unstructured evidence markers (`[E1]`, `[E2]`), two failure modes frequently occur on CPU-constrained local inference:
1. **Trailing Unattributed Assertions:** The model generates introductory or concluding sentences without citation markers, causing fail-closed rejection by the citation validator.
2. **Hallucinated Evidence Markers:** When retrieval provides insufficient evidence or a constrained passage budget ($k=1$), the model fabricates references to non-existent passages (e.g. inventing `[E2]` and `[E3]`).

To eliminate these defects without rewriting the pipeline or compromising fail-closed safeguards, Milestone 7 implements **Schema-Constrained Generation** using Ollama's native JSON Schema engine with dynamically generated enum constraints, paired with dual-layer application-side verification.

### Key Measured Outcomes

| Metric | Milestone 6.1 (Free-Form Baseline) | Milestone 7 (Structured Generation) | Impact / Delta |
| :--- | :--- | :--- | :--- |
| **Evaluated Queries** | 10 canonical | 10 canonical | Identical benchmark set |
| **Grounding Gate Fast-Exits** | 4 / 4 (100%) | 4 / 4 (100%) | Gate fully preserved; median 0.106s |
| **LLM Invocations** | 6 | 6 | Exact same 6 answerable candidates |
| **Valid Structured Output Rate** | N/A (Free-form) | **100.0% (6 / 6)** | Zero malformed JSON or schema rejections |
| **Unknown / Hallucinated Evidence IDs** | 1 / 6 (16.7%) | **0 / 6 (0.0%)** | **100% elimination of phantom IDs** |
| **Valid Answers Accepted** | 2 / 6 (33.3%) | **5 / 6 (83.3%)** | +50% acceptance (eliminated cleavage) |
| **Model Voluntary Abstentions** | 0 / 6 | **1 / 6 (16.7%)** | Model correctly abstained on under-specified query (`M6_009`) |
| **Generation Latency (Median)** | 141.54 seconds | **62.97 seconds** | **2.25x faster generation** |
| **Generation Latency (p95)** | 227.03 seconds | **98.89 seconds** | **2.30x tail latency improvement** |
| **Timeouts** | 0 / 10 | 0 / 10 | Zero timeouts under 240s threshold |
| **Automated Regression Suite** | 154 passing | **168 passing (+14 new tests)** | 100% test pass rate across repository |

---

## 2. Local Ollama & Hardware Capability Audit

### 2.1 Installed Software & Runtime Environment
- **Ollama Daemon:** `http://localhost:11434` (version `0.17.1`)
- **Evaluated Model:** `phi3.5:latest` (3.8B parameters, quantized)
- **Host Architecture:** Windows 11, Intel CPU (8 worker threads, no GPU acceleration)
- **Ollama API Endpoint:** `/api/generate` with HTTP POST payloads

### 2.2 Structured Output Capabilities & Grammar Constraints
Prior to implementation, an empirical capability probe was conducted against the running daemon. Findings:
1. **JSON Schema Support in `format`:** Ollama `0.17.1` natively supports passing standard JSON Schema dictionaries directly in the `format` field of `/api/generate`.
2. **Dynamic Enum Array Constraints:** The engine successfully compiles schemas where an array's item type is constrained by a dynamic `enum` list, e.g.:
   ```json
   {
     "type": "array",
     "items": {
       "type": "string",
       "enum": ["E1"]
     }
   }
   ```
   When constrained, the model's token sampler restricts logits to only tokens that construct the allowed enum strings, mathematically preventing the generation of tokens such as `"E2"` or `"E99"`.
3. **No External GBNF Files Required:** Grammar restriction is handled in-process by llama.cpp inside the Ollama daemon via the schema conversion layer.

---

## 3. Architecture & Contract Design

### 3.1 Minimal Structured Answer Schema
The schema is defined deterministically using Pydantic in `services/rag/models.py`:

```python
class StructuredClaim(BaseModel):
    text: str = Field(..., min_length=1, description="Substantive legal claim statement.")
    evidence_ids: List[str] = Field(..., min_length=1, description="Exact evidence IDs supporting this claim.")

class StructuredAnswer(BaseModel):
    status: Literal["answer", "abstain"] = Field(..., description="Whether to answer or abstain.")
    claims: List[StructuredClaim] = Field(default_factory=list, description="List of substantive claims.")
    abstention_reason: Optional[str] = Field(None, description="Explanation when abstaining.")
```

### 3.2 Dynamic Evidence ID Enum Generation
Crucially, citation constraints are derived **after passage budgeting** (`max_passages`). If retrieval extracts 4 passages but the prompt budget restricts generation to `max_passages=1`, only `["E1"]` is supplied to the schema generator:

```python
def get_structured_answer_schema(allowed_evidence_ids: List[str]) -> Dict[str, Any]:
    ...
    # If no evidence allowed (e.g. forced abstention), enum is empty
    evidence_enum = allowed_evidence_ids if allowed_evidence_ids else ["NONE"]
    ...
    "claims": {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "evidence_ids": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": evidence_enum
                    },
                    "minItems": 1
                }
            },
            "required": ["text", "evidence_ids"]
        }
    }
```

### 3.3 Strict Application-Level Fail-Closed Validation
Even though the engine enforces grammar, **the application never trusts model output**. `services/rag/validator.py` executes strict structural verification via `validate_structured()`:
1. **Schema Integrity:** Rejects malformed JSON, missing fields, or unrecognized keys.
2. **Abstention Consistency:**
   - If `status == "abstain"`, `claims` MUST be empty. Any generated claim is rejected.
   - If `status == "answer"`, `claims` MUST have at least one substantive item.
3. **Citation Syntactic & Whitelist Membership:**
   - Every `evidence_id` must match `^E\d+$`.
   - Every `evidence_id` must be an exact member of `allowed_evidence_ids` (the active budgeted passages).
   - Claims with empty `evidence_ids` are rejected immediately.
4. **Text Synthesis & Citation Markers:**
   - On valid answer, `RAGPipeline` formats the substantive claims into readable natural language with embedded citation markers (`[E1]`).
   - The original `StructuredAnswer` is preserved on `RAGResult.structured_answer` for programmatic API callers.
   - If validation fails, the pipeline fails closed: `RAGResult.status = "insufficient_evidence"`, `is_valid = False`, returning a safe abstention explanation.

---

## 4. Controlled Benchmark Comparison: 10 Canonical Queries

The 10 canonical queries from Milestone 6.1 were executed under identical CPU resource constraints:
- **Corpus:** 782 Supreme Court of India 2024 judgments.
- **Retrieval:** Hybrid BM25 + dense with score threshold.
- **Budgeting:** `max_passages=1`, `max_chars_per_passage=1000`.
- **Generation:** `phi3.5:latest`, `num_predict=140`, `timeout=240.0s`.

### Side-by-Side Query Results Matrix

| Query ID | Legal Domain | Query Type | Expected | M6.1 Free-Form Status | M7 Structured Status | M7 Latency | Notes on Milestone 7 Structured Behavior |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **M6_001** | Constitutional | Holding | Answerable | Accepted | **Accepted** | 98.88s | 2 claims citing `E1`. Perfectly cited; no trailing un-cited text. |
| **M6_002** | Insolvency | Statutory | Answerable | Rejected (Cleavage) | **Accepted** | 61.68s | 1 claim citing `E1`. Eliminates intro cleavage from M6.1. |
| **M6_004** | Limitation | Statutory | Answerable | Rejected (Cleavage) | **Accepted** | 64.25s | 1 claim citing `E1`. Specific balance sheet holding accurately cited. |
| **M6_005** | NI Act | Statutory | Answerable | Rejected (Cleavage) | **Accepted** | 59.37s | 1 claim citing `E1`. Interim deposit rule accurately cited. |
| **M6_007** | Constitutional | Holding | Answerable | Accepted | **Accepted** | 64.26s | 2 claims citing `E1`. Prison manual caste segregation unconstitutional. |
| **M6_009** | Taxation (CGST)| Statutory | Answerable* | Rejected (Unknown `E2`,`E3`)| **Abstained** | 61.33s | Model voluntary abstention: recognized `E1` lacked CGST s.17(5)(d) details! |
| **M6_017** | DPDP Act | Unanswerable | Abstain | Abstained (Gate) | **Abstained (Gate)** | 0.08s | Gate Fast-Exit: DPDP Act missing from 2024 SC corpus. |
| **M6_018** | Coparcenary | Unanswerable | Abstain | Abstained (Gate) | **Abstained (Gate)** | 0.11s | Gate Fast-Exit: Disjoint contexts between Hindu and Muslim law. |
| **M6_019** | Bail / Contempt | Unanswerable | Abstain | Abstained (Gate) | **Abstained (Gate)** | 0.10s | Gate Fast-Exit: Anticipatory bail disjoint from contempt. |
| **M6_020** | Patent Act 3(j)| Unanswerable | Abstain | Abstained (Gate) | **Abstained (Gate)** | 0.14s | Gate Fast-Exit: Statutory year / GM mustard absent in 2024 corpus. |

*\*Note on M6_009: While M6_009 is categorized as answerable in theory, the active single retrieved passage (budget $k=1$) contained general tax discussion without the specific Section 17(5)(d) functionality holding. In M6.1, the model hallucinated `E2` and `E3`. In M7, the constrained model acknowledged that the supplied evidence was insufficient and emitted `status: "abstain"`. This is ideal defensive RAG behavior.*

### Latency Distribution

```
Gate Fast-Exits (4 queries):
  Min:     0.077 s
  Median:  0.106 s
  Max:     0.144 s

LLM Generations (6 queries):
  Min:    59.371 s
  Median: 62.966 s
  p95:    98.885 s
  Max:    98.885 s
```

---

## 5. Regression Test Suite Verification

A dedicated test suite `tests/test_milestone7_structured.py` was created containing **14 comprehensive test cases** validating:
1. Dynamic schema generation with valid enum constraints.
2. Dynamic schema handling with empty evidence pools (`["NONE"]`).
3. Successful validation of well-formed answers with valid citation IDs.
4. Fail-closed rejection of missing required fields (`claims`, `status`).
5. Fail-closed rejection of substantive claims containing empty citation lists.
6. Fail-closed rejection of hallucinated / out-of-budget evidence IDs (`E2` when only `E1` allowed).
7. Fail-closed rejection of stale / previous-turn evidence IDs.
8. Fail-closed rejection of malformed / truncated JSON strings.
9. Validator compatibility parsing raw JSON strings into structured models.
10. Valid structured abstention acceptance when `claims` is empty.
11. Fail-closed rejection of structured abstentions that smuggle non-empty substantive claims.
12. Mock provider end-to-end integration across all structured modes.
13. Pipeline integration producing human-readable synthesized text with citation markers.
14. End-to-end pipeline fail-closed fallback on malformed model payloads.

### Test Execution Summary
- **Command:** `pytest -q`
- **Result:** **168 passed in 17.21 seconds**
- **Prior Tests Preserved:** 154 / 154 passed.
- **New Tests Added:** 14 / 14 passed.

---

## 6. Known Limitations & Epistemic Boundaries

1. **Syntactic vs. Semantic Grounding Distinction:**
   Enforcing grammar and enum membership guarantees **structural citation integrity** (i.e. every claim cites an existing passage from the active budget, and no un-cited claims escape). It **does not guarantee semantic legal truth**. In `milestone7_structured_comparison_report.json`, semantic legal support remains labeled `not_evaluated`. Claims must undergo expert legal review before being relied upon in practice.
2. **Local CPU Inference Latency:**
   While median generation latency improved from 141.5s to 63.0s (a 2.25x speedup), a 1-minute wait per answer remains noticeable. GPU or NPU acceleration would reduce this to sub-second or single-digit seconds.
3. **Developer-Curated Gold Labels:**
   All 10 benchmark queries and ground-truth expectations remain developer-curated, not independently authored by legal practitioners.
4. **No Legal Advice:**
   NyayaVarta is an experimental research system. Outputs must not be used as professional legal counsel.

---

## 7. Recommended Next Step

**Milestone 8 Candidate: Multi-Passage Context Compression & Evidence Re-Ranking.**  
Currently, single-passage budgeting ($k=1$) is used to manage CPU latency and prevent prompt context bloat. However, complex multi-issue queries (such as `M6_009`) require synthesizing facts across 2–3 distinct judgment paragraphs. Implementing an extractive sentence compressor or localized passage reranker before prompt construction will allow multi-passage grounding without increasing generation latency.
