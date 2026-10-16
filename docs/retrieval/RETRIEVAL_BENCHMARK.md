# Retrieval Pipeline Benchmark (v3.1)

**Benchmark Date:** 2026-10-12T00:03:27  
**Platform:** Windows-11-10.0.26300-SP0  
**CPU:** Intel64 Family 6 Model 154 Stepping 4, GenuineIntel (12 cores)  
**RAM:** 15.7 GB  
**Embedding Model:** `sentence-transformers/all-MiniLM-L6-v2` (dim=384, normalized=True)  
**Corpus Size:** 782 judgments  
**Reranker in Production:** Disabled by default (CPU latency preservation)  
**Warm-up:** 2 queries discarded prior to latency measurement  

## 1. Index Storage and Memory

| File / Component | Size / Value |
|---|---|
| `data/indexes/bm25.db` | 97.88 MB |
| `data/indexes/bm25.db-shm` | 0.03 MB |
| `data/indexes/bm25.db-wal` | 0.00 MB |
| `data/indexes/dense.faiss` | 1.15 MB |
| `data/indexes/dense_doc_ids.json` | 0.02 MB |
| `data/indexes/dense_model_config.json` | 0.00 MB |
| `data/indexes/retrieval_config.json` | 0.00 MB |
| **Total On-Disk Index Storage** | **99.07 MB** |
| **Peak Process RAM** | **1654.0 MB** |

## 2. Evaluation Set: Synthetic Evaluation Set (Verbatim Text Segments)

- **Query Count:** 25 queries

| Pipeline | Recall@5 | Recall@10 | MRR | NDCG@10 | Latency (med) | Latency (p95) | Latency (mean) |
|---|---|---|---|---|---|---|---|
| **BM25** | 0.840 | 0.880 | 0.773 | 0.799 | 18.1 ms | 48.3 ms | 22.2 ms |
| **Dense** | 0.360 | 0.400 | 0.217 | 0.262 | 5.4 ms | 8.1 ms | 5.8 ms |
| **Hybrid** | 0.880 | 0.920 | 0.573 | 0.657 | 39.3 ms | 68.8 ms | 39.4 ms |
| **Hybrid + Reranker** | 0.720 | 0.840 | 0.547 | 0.615 | 3301.2 ms | 3536.4 ms | 3269.6 ms |

## 2. Evaluation Set: Manually Reviewed Legal Evaluation Set (Independent Natural Language Questions)

- **Query Count:** 35 queries

| Pipeline | Recall@5 | Recall@10 | MRR | NDCG@10 | Latency (med) | Latency (p95) | Latency (mean) |
|---|---|---|---|---|---|---|---|
| **BM25** | 0.914 | 0.943 | 0.687 | 0.699 | 36.7 ms | 55.9 ms | 37.0 ms |
| **Dense** | 0.971 | 1.000 | 0.872 | 0.861 | 6.1 ms | 8.5 ms | 6.3 ms |
| **Hybrid** | 0.971 | 1.000 | 0.900 | 0.876 | 45.9 ms | 67.2 ms | 46.3 ms |
| **Hybrid + Reranker** | 0.971 | 1.000 | 0.948 | 0.910 | 3307.9 ms | 3597.6 ms | 3328.1 ms |

