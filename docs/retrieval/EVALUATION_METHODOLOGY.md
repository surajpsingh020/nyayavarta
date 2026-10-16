# NyayaVarta Retrieval Evaluation Methodology (v3.1)

This document formalizes the evaluation methodology, dataset provenance, metrics definitions, and audit procedures for NyayaVarta's retrieval pipelines.

---

## 1. Evaluation Datasets Overview

NyayaVarta maintains two distinct, decoupled evaluation suites to avoid evaluation confounding:

| Characteristic | Synthetic Evaluation Suite | Manually Reviewed Legal Suite |
|---|---|---|
| **Location** | `evaluation/queries/queries.json` | `evaluation/queries/legal_queries.json` |
| **Gold Standard** | `evaluation/gold/gold.json` | `evaluation/gold/legal_gold.json` |
| **Query Count** | 25 queries (`Q001` - `Q025`) | 35 queries (`LQ001` - `LQ035`) |
| **Creation Method** | Heuristic sentence extraction | Manual legal issue formulating |
| **Query Form** | Verbatim case text excerpts + `?` | Natural language legal queries |
| **Relevance Grading**| Binary (1 for source document) | Graded (2 = Highly Relevant, 1 = Partially Relevant) |
| **Primary Utility** | Exact-text / verbatim phrase stress test | Realistic legal semantic search test |

---

## 2. Dataset 1: Synthetic Evaluation Suite (Audit & Limitations)

### Generation Methodology (`scripts/benchmark/generate_synthetic_eval.py`)
- **Procedure:** The script sampled 25 processed JSON documents at random from `data/processed/aws_sc/`. It split each judgment's `full_text` by sentence (`. `) and found a sentence between 50 and 200 characters containing keywords such as `"Section"`, `"Act"`, `"Constitution"`, or `"appeal"`.
- **Query Construction:** The selected sentence was stripped of newline characters and appended with a question mark `?` (e.g., `"Judges must eschew the tendency to substitute their own subjective values for the values which are protected by the Constitution?"`).
- **Ground Truth Assignment:** The document from which the sentence was sliced was assigned as the sole relevant document (`relevance_grades: {doc_id: 1}`).

### Identified Weaknesses & Confounding:
1. **Lexical Leakage:** Because queries are verbatim excerpts of judgments, BM25 trivially retrieves the source document via exact n-gram matching, inflating BM25 Recall (Recall@10 = 0.880, MRR = 0.773).
2. **Context Truncation Artifact:** Dense models with a 512-token context window (`all-MiniLM-L6-v2`) only encode the opening ~400 words of each judgment. If a synthetic query was sampled from page 15 of a 30-page judgment, the dense model cannot possibly find it in unchunked mode, artificially depressing dense recall (Recall@10 = 0.400, MRR = 0.217).
3. **Artifact Queries:** The naive splitter occasionally produced garbled queries ending in truncated citation tokens (e.g., `"... (Civil Appeal No?"`).

### Role in the System:
The synthetic suite is **strictly preserved** as a regression test for exact-citation and verbatim statute phrase retrieval. It must never be presented as an assessment of semantic legal understanding.

---

## 3. Dataset 2: Manually Reviewed Legal Evaluation Suite

### Construction Methodology
To evaluate realistic legal retrieval without verbatim leakage, 35 domain-grounded questions were formulated by analyzing the substantive issues in the 782 Supreme Court judgments:

1. **Independent Formulation:** Questions are written in standard natural legal language (the way advocates, law clerks, or citizens formulate queries), avoiding direct copy-pasting of text from any judgment.
2. **Substantive Domain Coverage:**
   - **Criminal Law (11 queries):** PMLA Section 45 bail twin conditions, reversal of acquittal standards under Section 378/386 CrPC, remission conditions under Section 432 CrPC, mens rea for Section 306 IPC abetment of suicide, POCSO online possession, Section 482 CrPC quashing of OTS-settled disputes, Section 498A omnibus cruelty allegations, Section 319 CrPC additional accused summoning.
   - **Constitutional Law (6 queries):** Article 265 taxation without explicit statutory authority, Article 142 equitable relief for marginalized students, reasonable classification in single-entity legislation under Article 14, caste-based labor in state prison manuals (Articles 14/15/17/21), constitutional validity of Section 6A of Citizenship Act 1955, uniform service conditions for High Court judges (Articles 216/221).
   - **Commercial & Insolvency Law (5 queries):** SARFAESI Rule 9(4) balance purchase deposit deadline, IBC Section 18 limitation extension via balance sheet entries, Section 36 Arbitration Act stay standards for public vs private bodies, Section 62 IBC locus and CIRP withdrawal abuse, Section 148 Negotiable Instruments Act interim deposit liability.
   - **Civil Procedure & Evidence (4 queries):** Order XXI Rule 99 CPC dispossession claims by strangers/transferees, standard of care in medical negligence, Aadhaar card vs school leaving certificate for date of birth, time as essence of contract in specific performance suits.
   - **Property Law (2 queries):** Land Acquisition Act 1894 comparable sales method, Section 126 Transfer of Property Act unilateral gift deed revocation.
   - **Administrative Law (2 queries):** Scrapping recruitment and changing rules of the game post-selection list, regulatory authorities appealing against appellate tribunal orders.
   - **Tax Law (2 queries):** Income Tax Section 148 reassessments post-April 2021 with TOLA, CGST Section 17(5)(d) Input Tax Credit for commercial mall construction.
   - **Family Law (2 queries):** Pan-India guidelines for Prohibition of Child Marriage Act, Section 25(2) Domestic Violence Act alteration of maintenance.
   - **Labor Law (1 query):** Definition of 'workman' vs supervisory functions under Section 2(s) Industrial Disputes Act.

### Relevance Annotation & Verification:
- **Corpus Verification:** Every referenced document ID was verified to exist in `data/processed/aws_sc/`.
- **Graded Relevance:**
  - `Grade 2 (Highly Relevant)`: The judgment directly addresses, analyzes, and rules on the specific legal proposition or statutory section asked in the query.
  - `Grade 1 (Partially Relevant)`: The judgment addresses an adjacent or related facet of the same legal provision or general doctrine.
- **Annotation Method:** Documented as `"topic_matching"`. Every entry in `evaluation/gold/legal_gold.json` includes an `annotation_note` explaining the ratio and substantive holding connecting the document to the query.

---

## 4. Evaluation Metrics Definitions

All retrieval pipelines are evaluated using standard information retrieval metrics:

### 1. Recall@K ($K \in \{5, 10\}$)
Measures the proportion of queries for which at least one relevant document was retrieved in the top $K$ positions:
$$\text{Recall@}K = \frac{1}{|Q|} \sum_{q \in Q} \mathbb{I}\left( \text{rank}(q) \le K \right)$$

### 2. Mean Reciprocal Rank (MRR)
Measures the reciprocal rank of the first relevant document retrieved:
$$\text{MRR} = \frac{1}{|Q|} \sum_{q \in Q} \frac{1}{\text{rank}_1(q)}$$
where $\text{rank}_1(q)$ is the position of the first relevant document (or $\infty$ if no relevant document is retrieved in top $K$).

### 3. Normalized Discounted Cumulative Gain (NDCG@10)
Accounts for graded relevance ($r_i \in \{0, 1, 2\}$) and rewards ranking highly relevant documents at higher positions:
$$\text{DCG@10} = \sum_{i=1}^{10} \frac{r_i}{\log_2(i + 1)}, \quad \text{NDCG@10} = \frac{\text{DCG@10}}{\text{IDCG@10}}$$
where $\text{IDCG@10}$ is the ideal DCG obtained by sorting true relevance grades in descending order.

### 4. Latency Profiling
- **Warm-Up:** The benchmark executes 2 unmeasured warm-up queries to initialize ONNX runtime sessions and SQLite cache buffers before collecting timing metrics.
- **High-Precision Timing:** Measured using `time.perf_counter()`.
- **Distribution Reporting:** Reports **Median**, **P95**, and **Mean** latency in milliseconds, guarding against outlier skew.

---

## 5. Automated Regression Test Suite

Regression testing is codified in `tests/test_retrieval.py` and run via `pytest`:
- **BM25 Functional Tests:** Exact search, empty queries, special characters/punctuations, query deduplication, token limits, legal term preservation (`Section 302/34`, `anti-defection`, `Order XXI Rule 99`).
- **Connection Optimization Tests:** Persistent SQLite connection reuse and pragma verification.
- **Hybrid Fusion Tests:** Reciprocal Rank Fusion behavior when documents appear in both lists vs single lists.
- **Configuration Integrity:** Verification of `retrieval_config.json` single-source-of-truth invariants.
- **Dataset Validation:** Integrity checks verifying non-empty queries, valid gold mappings, and file existence.
- **Index File Integrity:** Verifies existence and non-zero size of `bm25.db`, `dense.faiss`, `dense_doc_ids.json`, and `retrieval_config.json`.
