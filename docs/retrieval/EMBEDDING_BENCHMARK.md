# Embedding Model Benchmark and Selection Analysis (v3.1)

This document provides the benchmark comparison, selection criteria, and architectural rationale for NyayaVarta's baseline dense retrieval model.

## 1. Candidate Models Evaluated

In accordance with NyayaVarta's freeware, CPU-first, and zero-paid-API constraints, two open-source compact embedding models were benchmarked:
1. **`sentence-transformers/all-MiniLM-L6-v2`** (384-dimensional dense representations, 22.7M parameters)
2. **`BAAI/bge-small-en-v1.5`** (384-dimensional dense representations, 33.4M parameters)

Both models were run via **`fastembed`** using the **ONNX Runtime** on CPU to avoid large PyTorch compilation overheads and maximize CPU SIMD vector utilization.

---

## 2. Empirical Benchmark Results

Evaluated over the 782 Supreme Court judgments (year 2024 development corpus):

| Model | Embedding Dim | Peak Model RAM | Index Time (782 docs) | Query Latency (CPU) | Recall@5 | Recall@10 | MRR |
|---|---|---|---|---|---|---|---|
| **`sentence-transformers/all-MiniLM-L6-v2`** | **384** | **123.2 MB** | **112.7 s** | **18.7 ms** | **0.360** | **0.400** | **0.231** |
| `BAAI/bge-small-en-v1.5` | 384 | 121.8 MB | 499.3 s | 163.6 ms | 0.240 | 0.400 | 0.230 |

*Source Data: `docs/retrieval/EMBEDDING_BENCHMARK.json`*

---

## 3. Discrepancy Audit & Correction

During the Milestone 3.1 audit, an inconsistency was identified in the previous Milestone 3 documentation:
- The initial summary table reported `all-MiniLM-L6-v2` MRR as `0.217` and erroneously claimed `BGE-small` scored higher on MRR.
- The underlying machine-readable benchmark JSON (`docs/retrieval/EMBEDDING_BENCHMARK.json`) recorded an MRR of `0.2310` for `all-MiniLM-L6-v2` and `0.2302` for `BGE-small`.
- The erroneous `0.217` value had been transcribed from the downstream multi-stage pipeline evaluation rather than the standalone embedding test.
- This correction confirms that `all-MiniLM-L6-v2` outperformed `bge-small-en-v1.5` on both Recall@5 (0.360 vs 0.240) and MRR (0.231 vs 0.230), while matching Recall@10 (0.400).

---

## 4. Selection Rule Specification

To ensure deterministic and reproducible model selection without ad-hoc overrides, Milestone 3.1 establishes the following formal decision rule:

```
Selection Priority:
  1. Primary Metric: Legal Recall@10 (Higher is better)
  2. Tie-Breaker Metric: Single-Query Latency in milliseconds (Lower is better)
  3. Secondary Guardrail: Peak RAM <= 500 MB, Index Construction Rate >= 5 docs/sec
```

### Application of Rule:
1. **Primary Metric (Recall@10):** Both models achieved an identical Recall@10 of `0.4000`.
2. **Tie-Breaker Metric (Latency):**
   - `all-MiniLM-L6-v2`: **18.7 ms**
   - `bge-small-en-v1.5`: **163.6 ms** (~8.7x slower)
3. **Indexing Throughput:**
   - `all-MiniLM-L6-v2`: **6.94 docs/sec** (112.7 s total)
   - `bge-small-en-v1.5`: **1.57 docs/sec** (499.3 s total, ~4.4x slower)

**Winning Model:** `sentence-transformers/all-MiniLM-L6-v2` is selected as the canonical V1 embedding model for NyayaVarta.

---

## 5. Single Source of Truth Configuration

All embedding and retrieval parameters are stored in a single configuration file:
`data/indexes/retrieval_config.json` (managed via `services/retrieval/config.py`).

```json
{
  "embedding": {
    "model_name": "sentence-transformers/all-MiniLM-L6-v2",
    "dimension": 384,
    "normalize": true,
    "similarity_metric": "cosine",
    "backend": "fastembed-onnx",
    "batch_size": 32,
    "max_seq_length": 512
  },
  "bm25": {
    "tokenizer": "porter unicode61",
    "default_top_k": 10,
    "query_mode": "AND",
    "db_path": "data/indexes/bm25.db"
  },
  "hybrid": {
    "rrf_k": 60,
    "bm25_fetch_multiplier": 3,
    "dense_fetch_multiplier": 3
  },
  "reranker": {
    "enabled": false,
    "model_name": "jinaai/jina-reranker-v1-turbo-en",
    "backend": "fastembed-onnx",
    "max_candidates": 30,
    "max_passage_length": 2048
  },
  "selection_rule": {
    "primary_metric": "recall_10",
    "tiebreaker_metric": "query_latency_ms",
    "tiebreaker_direction": "lower_is_better"
  },
  "version": "3.1.0"
}
```

### Normalization & Compatibility Guarantee:
- **Indexing (`scripts/index/index_dense.py`):** Explicitly applies `faiss.normalize_L2(doc_embeddings)` before insertion into `faiss.IndexFlatIP`.
- **Query Time (`services/retrieval/dense_retriever.py`):** Explicitly applies `faiss.normalize_L2(q_emb)` before calling `index.search()`.
- **Mathematical Invariant:** For two L2-normalized unit vectors $\mathbf{u}$ and $\mathbf{v}$, their inner product $\mathbf{u} \cdot \mathbf{v}$ is strictly equal to their cosine similarity:
  $$\cos(\theta) = \frac{\mathbf{u} \cdot \mathbf{v}}{\|\mathbf{u}\|_2 \|\mathbf{v}\|_2} = \mathbf{u} \cdot \mathbf{v}$$
  This ensures compatibility between query representations and the FAISS `IndexFlatIP` index.
