"""
NyayaVarta Retrieval Benchmark v3.1

Improvements over v3.0:
- Supports multiple evaluation sets (synthetic + legal)
- Computes NDCG@10 with graded relevance
- Reports median, p95, and mean latency
- Evaluates BM25, Dense, Hybrid, and Hybrid + Reranker
- Bounded passage reranking (2048 chars, top 20 candidates)
- Reports index sizes and peak memory
- Warm-up runs before timing
- Hardware disclosure
"""
import os
import json
import time
import math
import platform
import statistics
import psutil
import numpy as np
from datetime import datetime

from services.retrieval.bm25_retriever import BM25Retriever
from services.retrieval.dense_retriever import DenseRetriever
from services.retrieval.hybrid_retriever import HybridRetriever
from services.retrieval.reranker import Reranker
from services.retrieval.config import load_config

PROCESSED_DIR = "data/processed/aws_sc"
INDEX_DIR = "data/indexes"
WARMUP_QUERIES = 2


def load_eval_set(queries_path, gold_path):
    """Load an evaluation set."""
    with open(queries_path, "r", encoding="utf-8") as f:
        queries = json.load(f)
    with open(gold_path, "r", encoding="utf-8") as f:
        gold = json.load(f)
    return queries, gold


def load_doc_texts():
    texts = {}
    for file in os.listdir(PROCESSED_DIR):
        if file.endswith('.json'):
            with open(os.path.join(PROCESSED_DIR, file), "r", encoding="utf-8") as f:
                doc = json.load(f)
                texts[doc["document_id"]] = doc.get("full_text", "")
    return texts


def dcg_at_k(relevances, k):
    """Compute DCG@k."""
    relevances = relevances[:k]
    return sum(rel / math.log2(i + 2) for i, rel in enumerate(relevances))


def ndcg_at_k(retrieved_ids, relevance_grades, k):
    """Compute NDCG@k with graded relevance."""
    actual_rels = [relevance_grades.get(doc_id, 0) for doc_id in retrieved_ids[:k]]
    ideal_rels = sorted(relevance_grades.values(), reverse=True)[:k]

    actual_dcg = dcg_at_k(actual_rels, k)
    ideal_dcg = dcg_at_k(ideal_rels, k)

    if ideal_dcg == 0:
        return 0.0
    return actual_dcg / ideal_dcg


def evaluate_pipeline(name, queries, gold, pipeline_func, top_k=10, warmup=WARMUP_QUERIES):
    """Evaluate a retrieval pipeline with comprehensive metrics."""
    gold_dict = {g["query_id"]: g for g in gold}

    # Warm-up runs (not measured)
    for q in queries[:warmup]:
        pipeline_func(q["query_text"], top_k)

    # Measured runs
    latencies = []
    recall_at_5 = 0
    recall_at_10 = 0
    mrr = 0.0
    ndcg_scores = []

    for q in queries:
        start_q = time.perf_counter()
        results = pipeline_func(q["query_text"], top_k)
        latencies.append(time.perf_counter() - start_q)

        retrieved_ids = [res["document_id"] for res in results]
        gold_entry = gold_dict.get(q["query_id"], {})
        relevant_ids = gold_entry.get("relevant_document_ids", [])
        relevance_grades = gold_entry.get("relevance_grades", {})

        # If no graded relevance, use binary
        if not relevance_grades:
            relevance_grades = {doc_id: 1 for doc_id in relevant_ids}

        # Recall and MRR
        hit_ranks = [i + 1 for i, r_id in enumerate(retrieved_ids) if r_id in relevant_ids]
        if hit_ranks:
            first_hit = hit_ranks[0]
            mrr += 1.0 / first_hit
            if first_hit <= 5:
                recall_at_5 += 1
            if first_hit <= 10:
                recall_at_10 += 1

        # NDCG@10
        ndcg = ndcg_at_k(retrieved_ids, relevance_grades, 10)
        ndcg_scores.append(ndcg)

    num_queries = len(queries)
    latency_ms = [l * 1000 for l in latencies]
    sorted_lats = sorted(latency_ms)
    p95_idx = min(int(len(sorted_lats) * 0.95), len(sorted_lats) - 1)

    return {
        "pipeline": name,
        "num_queries": num_queries,
        "recall_5": recall_at_5 / num_queries if num_queries else 0,
        "recall_10": recall_at_10 / num_queries if num_queries else 0,
        "mrr": mrr / num_queries if num_queries else 0,
        "ndcg_10": sum(ndcg_scores) / num_queries if num_queries else 0,
        "latency_median_ms": statistics.median(latency_ms) if latency_ms else 0,
        "latency_p95_ms": sorted_lats[p95_idx] if latency_ms else 0,
        "latency_mean_ms": statistics.mean(latency_ms) if latency_ms else 0,
    }


def get_index_sizes():
    """Measure index file sizes."""
    sizes = {}
    for fname in os.listdir(INDEX_DIR):
        fpath = os.path.join(INDEX_DIR, fname)
        if os.path.isfile(fpath):
            sizes[fname] = os.path.getsize(fpath)
    return sizes


def get_hardware_info():
    """Collect hardware details for reproducibility."""
    return {
        "os": platform.platform(),
        "cpu": platform.processor(),
        "cpu_count": psutil.cpu_count(logical=True),
        "ram_total_gb": round(psutil.virtual_memory().total / (1024**3), 1),
        "python": platform.python_version(),
        "timestamp": datetime.now().isoformat()
    }


def main():
    config = load_config()
    print("=" * 60)
    print("NyayaVarta Retrieval Benchmark v3.1")
    print("=" * 60)

    hw = get_hardware_info()
    print(f"OS: {hw['os']}")
    print(f"CPU: {hw['cpu']} ({hw['cpu_count']} logical cores)")
    print(f"RAM: {hw['ram_total_gb']} GB")
    print()

    # Discover evaluation sets
    eval_sets = {}

    # Synthetic eval
    syn_q = "evaluation/queries/queries.json"
    syn_g = "evaluation/gold/gold.json"
    if os.path.exists(syn_q) and os.path.exists(syn_g):
        eval_sets["synthetic"] = (syn_q, syn_g)

    # Legal eval
    legal_q = "evaluation/queries/legal_queries.json"
    legal_g = "evaluation/gold/legal_gold.json"
    if os.path.exists(legal_q) and os.path.exists(legal_g):
        eval_sets["legal"] = (legal_q, legal_g)

    if not eval_sets:
        print("ERROR: No evaluation sets found.")
        return

    print(f"Evaluation sets found: {list(eval_sets.keys())}")

    # Load model config
    model_name = config["embedding"]["model_name"]
    print(f"Dense model: {model_name}")

    doc_texts = load_doc_texts()
    print(f"Corpus size: {len(doc_texts)} documents")

    # Initialize retrievers
    print("\nInitializing retrievers...")
    bm25 = BM25Retriever(config["bm25"]["db_path"])
    dense = DenseRetriever(
        model_name,
        os.path.join(INDEX_DIR, "dense.faiss"),
        os.path.join(INDEX_DIR, "dense_doc_ids.json")
    )
    hybrid = HybridRetriever(k=config["hybrid"]["rrf_k"])

    print("Initializing cross-encoder reranker for evaluation comparison...")
    reranker = Reranker(
        model_name=config["reranker"]["model_name"],
        max_passage_length=config["reranker"].get("max_passage_length", 2048)
    )

    # Build pipeline functions
    def run_bm25(q, k):
        res, _ = bm25.search(q, top_k=k)
        return res

    def run_dense(q, k):
        res, _ = dense.search(q, top_k=k)
        return res

    def run_hybrid(q, k):
        fetch_k = k * config["hybrid"]["bm25_fetch_multiplier"]
        b_res, _ = bm25.search(q, top_k=fetch_k)
        d_res, _ = dense.search(q, top_k=fetch_k)
        return hybrid.combine(b_res, d_res, top_k=k)

    def run_hybrid_reranked(q, k):
        # Fetch top 20 candidates for reranking
        raw_candidates = run_hybrid(q, 20)
        candidates = [dict(c) for c in raw_candidates]
        return reranker.rerank(q, candidates, doc_texts, top_k=k)

    pipelines = [
        ("BM25", run_bm25),
        ("Dense", run_dense),
        ("Hybrid", run_hybrid),
        ("Hybrid + Reranker", run_hybrid_reranked),
    ]

    # Run benchmarks per eval set
    all_results = {}
    for eval_name, (q_path, g_path) in eval_sets.items():
        queries, gold = load_eval_set(q_path, g_path)
        print(f"\n--- Running Benchmark on {eval_name.upper()} evaluation set ({len(queries)} queries) ---")

        results = []
        for pipe_name, pipe_func in pipelines:
            print(f"  Evaluating {pipe_name}...")
            res = evaluate_pipeline(pipe_name, queries, gold, pipe_func)
            results.append(res)
            print(f"    Recall@5={res['recall_5']:.3f}  Recall@10={res['recall_10']:.3f}  "
                  f"MRR={res['mrr']:.3f}  NDCG@10={res['ndcg_10']:.3f}  "
                  f"Latency(med)={res['latency_median_ms']:.1f}ms  "
                  f"Latency(p95)={res['latency_p95_ms']:.1f}ms")

        all_results[eval_name] = results

    # Collect index sizes
    index_sizes = get_index_sizes()
    peak_ram_mb = psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024)

    # Save JSON results
    output = {
        "hardware": hw,
        "config_version": config["version"],
        "embedding_model": model_name,
        "reranker_default_enabled": config["reranker"]["enabled"],
        "corpus_size": len(doc_texts),
        "index_sizes_bytes": index_sizes,
        "peak_ram_mb": round(peak_ram_mb, 1),
        "results_by_eval_set": all_results
    }

    os.makedirs("docs/retrieval", exist_ok=True)
    with open("docs/retrieval/RETRIEVAL_BENCHMARK.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=4)

    # Write Markdown
    md = "# Retrieval Pipeline Benchmark (v3.1)\n\n"
    md += f"**Benchmark Date:** {hw['timestamp'][:19]}  \n"
    md += f"**Platform:** {hw['os']}  \n"
    md += f"**CPU:** {hw['cpu']} ({hw['cpu_count']} cores)  \n"
    md += f"**RAM:** {hw['ram_total_gb']} GB  \n"
    md += f"**Embedding Model:** `{model_name}` (dim={config['embedding']['dimension']}, normalized={config['embedding']['normalize']})  \n"
    md += f"**Corpus Size:** {len(doc_texts)} judgments  \n"
    md += f"**Reranker in Production:** {'Enabled' if config['reranker']['enabled'] else 'Disabled by default (CPU latency preservation)'}  \n"
    md += f"**Warm-up:** {WARMUP_QUERIES} queries discarded prior to latency measurement  \n\n"

    md += "## 1. Index Storage and Memory\n\n"
    md += "| File / Component | Size / Value |\n|---|---|\n"
    for fname, size in sorted(index_sizes.items()):
        md += f"| `data/indexes/{fname}` | {size / (1024*1024):.2f} MB |\n"
    total_idx = sum(index_sizes.values())
    md += f"| **Total On-Disk Index Storage** | **{total_idx / (1024*1024):.2f} MB** |\n"
    md += f"| **Peak Process RAM** | **{peak_ram_mb:.1f} MB** |\n\n"

    for eval_name, results in all_results.items():
        title = "Synthetic Evaluation Set (Verbatim Text Segments)" if eval_name == "synthetic" else "Manually Reviewed Legal Evaluation Set (Independent Natural Language Questions)"
        md += f"## 2. Evaluation Set: {title}\n\n"
        md += f"- **Query Count:** {results[0]['num_queries']} queries\n\n"
        md += "| Pipeline | Recall@5 | Recall@10 | MRR | NDCG@10 | Latency (med) | Latency (p95) | Latency (mean) |\n"
        md += "|---|---|---|---|---|---|---|---|\n"
        for r in results:
            md += (f"| **{r['pipeline']}** | {r['recall_5']:.3f} | {r['recall_10']:.3f} | "
                   f"{r['mrr']:.3f} | {r['ndcg_10']:.3f} | "
                   f"{r['latency_median_ms']:.1f} ms | {r['latency_p95_ms']:.1f} ms | {r['latency_mean_ms']:.1f} ms |\n")
        md += "\n"

    with open("docs/retrieval/RETRIEVAL_BENCHMARK.md", "w", encoding="utf-8") as f:
        f.write(md)

    bm25.close()
    print(f"\nBenchmark complete. Saved to docs/retrieval/RETRIEVAL_BENCHMARK.md and docs/retrieval/RETRIEVAL_BENCHMARK.json")


if __name__ == "__main__":
    main()
