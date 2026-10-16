# NyayaVarta Retrieval System Design (v3.1)

This document details the architecture, optimization engineering, and design decisions for NyayaVarta's CPU-first legal retrieval system.

---

## 1. Architectural Overview

NyayaVarta implements a multi-stage, hybrid retrieval pipeline designed strictly for commodity CPU execution without dependencies on paid commercial APIs, GPUs, or external vector databases:

```
[ Natural Language Legal Query ]
               │
               ▼
   [ Query Normalizer / Sanitizer ]
   (Normalizes legal acronyms: Cr.P.C. -> CrPC)
               │
       ┌───────┴───────┐
       ▼               ▼
[ Sparse Retrieval ] [ Dense Retrieval ]
(SQLite FTS5 BM25)   (FAISS CPU + all-MiniLM-L6-v2)
  - Persistent WAL     - ONNX fastembed
  - 256 MB mmap        - Explicit L2 normalization
  - AND-first match    - Cosine / IndexFlatIP
  - Bounded OR          Latency: ~6 ms (med)
  Latency: ~36 ms
       │               │
       └───────┬───────┘
               ▼
     [ Hybrid Rank Fusion ]
     (Reciprocal Rank Fusion, k=60)
     Latency: ~45 ms (med), ~67 ms (p95)
     Recall@10: 1.000, MRR: 0.900 (Legal benchmark)
               │
               ▼
 [ Optional Cross-Encoder Reranker ]
 (jina-reranker-v1-turbo-en, bounded 2048 chars)
 *DISABLED BY DEFAULT on CPU to preserve SLA*
 Latency: ~3300 ms (med)
```

---

## 2. Component Specifications

### 2.1 Sparse Retrieval (BM25 via SQLite FTS5)
- **Engine:** SQLite virtual table using the FTS5 extension (`services/retrieval/bm25_retriever.py`).
- **Tokenization:** `porter unicode61`.
- **Indexed Fields:** `case_title` and canonical `full_text`.
- **Milestone 3.1 Latency Optimization:**
  - **Connection Overhead Elimination:** Replaced per-query connection open/close with a lazy, persistent connection.
  - **SQLite Performance Pragmas:** Enabled `PRAGMA journal_mode=WAL`, `PRAGMA cache_size=-64000` (64 MB page cache), `PRAGMA mmap_size=268435456` (256 MB memory-mapped I/O), and `PRAGMA synchronous=NORMAL`.
  - **Query Strategy:** The naive Milestone 3 approach joined all query tokens with `OR`, triggering combinatorial query explosion on long queries (causing 6,668 ms latency). Milestone 3.1 uses **AND-first evaluation** (median execution ~2.0 ms) with bounded OR fallback (capped at 15 unique tokens) only when AND produces fewer than `top_k` results.
  - **Legal Term Preservation:** Dot-collapsed legal acronyms (`Cr.P.C.` $\to$ `CrPC`, `I.P.C.` $\to$ `IPC`), preserved hyphens (`anti-defection`), and single-letter uppercase/digit terms (`Section 6A`, `Article 21A`, `Order XXI Rule 99`).
  - **Measured Speedup:** Latency dropped from **6,668.6 ms** to **36.7 ms median / 55.9 ms p95** (~180x speedup), comfortably meeting PRD SLAs.

### 2.2 Dense Retrieval (FAISS CPU + fastembed)
- **Model:** `sentence-transformers/all-MiniLM-L6-v2` (384 dimensions).
- **Inference Runtime:** ONNX Runtime via `fastembed` (CPU SIMD vectorized, eliminating PyTorch wheel build issues on Windows).
- **Index:** `faiss.IndexFlatIP` (exact inner product search, no quantization distortion).
- **Normalization Guarantee:**
  - Both document embeddings during indexing (`index_dense.py`) and query vectors during retrieval (`dense_retriever.py`) undergo explicit `faiss.normalize_L2()`.
  - Inner product on unit vectors strictly equals cosine similarity: $\mathbf{u} \cdot \mathbf{v} = \cos(\theta)$.
- **Latency & Accuracy:** Median latency is **6.1 ms** (p95: 8.5 ms). On the legal questions evaluation set, dense retrieval achieves **Recall@10 of 1.000** and **MRR of 0.872**.

### 2.3 Hybrid Score Fusion (Reciprocal Rank Fusion)
- **Method:** Reciprocal Rank Fusion (RRF) with constant $k=60$:
  $$\text{RRF Score}(d) = \sum_{m \in \{\text{BM25}, \text{Dense}\}} \frac{1}{60 + \text{rank}_m(d)}$$
- **Candidate Pool:** Both BM25 and Dense retrieve $3 \times \text{top\_k}$ candidates (e.g., top 30 candidates for top 10 output).
- **Performance:** Hybrid retrieval outperforms both individual retrievers on the legal benchmark, achieving:
  - **Recall@5:** 0.971
  - **Recall@10:** 1.000
  - **MRR:** 0.900
  - **NDCG@10:** 0.876
  - **Median Latency:** 45.9 ms (p95: 67.2 ms)

### 2.4 Cross-Encoder Reranker Investigation
- **Model:** `jinaai/jina-reranker-v1-turbo-en` via FastEmbed.
- **Passage Bounding:** Evaluated on the first 2,048 characters of candidates rather than entire 50-page judgments.
- **Empirical Findings:**
  - **Quality on Legal Set:** MRR modestly improves from 0.900 to 0.948 (+0.048), and NDCG@10 from 0.876 to 0.910 (+0.034).
  - **Quality on Synthetic Set:** Degradation occurred (Recall@10 fell from 0.920 to 0.840) because 2048-char truncation cuts off verbatim sentences sampled from the body of long judgments.
  - **Latency Penalty:** Latency increases from **45.9 ms** to **3,307.9 ms** (~72x slower on CPU), exceeding the 3-second SLA.
- **Production Decision:** **Disabled by default in production configuration** (`"enabled": false` in `retrieval_config.json`). It remains available as an optional asynchronous deep-research toggle.

---

## 3. Configuration Management

All retrieval settings are governed by `data/indexes/retrieval_config.json` and programmatically accessed through `services/retrieval/config.py`:

- **Single Source of Truth:** Eliminates discrepancies between indexers, retrievers, and benchmark runners.
- **Selection Rule:** Documented rule prioritizing Recall@10, with single-query latency as tie-breaker.
- **Determinism:** Seeded random states, explicit warm-ups, and recorded hardware platforms.

---

## 4. Index Storage Footprint

Index files stored under `data/indexes/` for the 782-judgment development corpus:

| File | Type | Size |
|---|---|---|
| `data/indexes/bm25.db` | SQLite FTS5 database | 97.88 MB |
| `data/indexes/bm25.db-shm` | Shared memory index | 0.03 MB |
| `data/indexes/bm25.db-wal` | Write-ahead log | 0.00 MB |
| `data/indexes/dense.faiss` | FAISS IndexFlatIP binary | 1.15 MB |
| `data/indexes/dense_doc_ids.json` | Position-to-ID mapping | 0.02 MB |
| `data/indexes/retrieval_config.json` | Centralized config | < 0.01 MB |
| **Total Index Footprint** | | **99.07 MB** |

**Peak Process RAM:** ~1.65 GB during full benchmark execution (including model weights, SQLite memory maps, and document caches).

---

## 5. Recommended Production Configuration for Milestone 4

For the upcoming Milestone 4 (Knowledge Graph / Legal Entity & Citation Extraction):
1. **Primary Retrieval Engine:** Hybrid RRF (BM25 + FAISS Dense) with `k=60`.
2. **Dense Model:** `sentence-transformers/all-MiniLM-L6-v2` with explicit L2 normalization and 512-token context.
3. **Sparse Model:** SQLite FTS5 with persistent connection, WAL mode, and AND-first evaluation.
4. **Reranker:** Kept **OFF** for standard interactive queries to preserve sub-100ms response times.
5. **Next Upgrade Path:** In Milestone 4/5, introduce structure-aware passage chunking (Headnotes, Facts, Ratio, Disposition) to extend dense retrieval across entire 50-page judgments.
