"""
Benchmark comparing Baseline Hybrid Retrieval vs Hybrid + Graph Expansion (Milestone 4B).

Runs both retrieval methods across the 35 curated queries in evaluation/queries/legal_queries.json
against gold relevant documents in evaluation/gold/legal_gold.json.

Measures:
- Hit Rate @ 5 (HR@5): Fraction of queries with >= 1 relevant document in top 5
- Hit Rate @ 10 (HR@10): Fraction of queries with >= 1 relevant document in top 10
- Mean Reciprocal Rank (MRR): 1 / rank of first relevant document
- Latency (median, p95, mean)
- Query-level comparison

Explicit metric definitions included.
"""
import os
import sys
import json
import time
import statistics
from typing import Dict, Any, List

sys.path.insert(0, ".")
from services.graph.graph_retriever import GraphExpandedRetriever

QUERIES_PATH = "evaluation/queries/legal_queries.json"
GOLD_PATH = "evaluation/gold/legal_gold.json"
OUT_JSON = "evaluation/graph/graph_retrieval_benchmark_v2.json"
V1_BASELINE_JSON = "evaluation/graph/graph_retrieval_benchmark_v1.json"


def evaluate_run(retriever: GraphExpandedRetriever, queries: List[Dict], gold_by_id: Dict, enable_graph: bool) -> Dict[str, Any]:
    latencies = []
    hits_at_5 = 0
    hits_at_10 = 0
    reciprocal_ranks = []
    query_results = []

    # Warm-up query
    retriever.retrieve(queries[0]["query_text"], top_k=10, enable_graph=enable_graph)

    for q in queries:
        qid = q["query_id"]
        qtext = q["query_text"]
        gold_docs = set(gold_by_id.get(qid, {}).get("relevant_document_ids", []))

        t0 = time.perf_counter()
        results = retriever.retrieve(qtext, top_k=10, enable_graph=enable_graph)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        latencies.append(elapsed_ms)

        retrieved_ids = [r["document_id"] for r in results]

        # Hit Rate @ 5: Top 5 contains >= 1 gold document
        top5_hit = any(doc_id in gold_docs for doc_id in retrieved_ids[:5])
        if top5_hit:
            hits_at_5 += 1

        # Hit Rate @ 10: Top 10 contains >= 1 gold document
        top10_hit = any(doc_id in gold_docs for doc_id in retrieved_ids[:10])
        if top10_hit:
            hits_at_10 += 1

        # Reciprocal Rank: 1 / rank of first relevant document
        rr = 0.0
        first_rel_rank = None
        for rank_idx, doc_id in enumerate(retrieved_ids):
            if doc_id in gold_docs:
                first_rel_rank = rank_idx + 1
                rr = 1.0 / first_rel_rank
                break
        reciprocal_ranks.append(rr)

        query_results.append({
            "query_id": qid,
            "query_text": qtext[:80] + "...",
            "legal_domain": q.get("legal_domain"),
            "gold_doc_ids": list(gold_docs),
            "top5_retrieved": retrieved_ids[:5],
            "first_relevant_rank": first_rel_rank,
            "hit_at_5": top5_hit,
            "hit_at_10": top10_hit,
            "reciprocal_rank": round(rr, 4),
            "latency_ms": round(elapsed_ms, 2)
        })

    num_q = len(queries)
    hr_5 = hits_at_5 / num_q if num_q > 0 else 0
    hr_10 = hits_at_10 / num_q if num_q > 0 else 0
    mrr = statistics.mean(reciprocal_ranks) if reciprocal_ranks else 0

    latencies.sort()
    med_lat = statistics.median(latencies)
    p95_lat = latencies[int(len(latencies) * 0.95)] if latencies else 0
    mean_lat = statistics.mean(latencies) if latencies else 0

    return {
        "method_name": "hybrid_plus_graph_expansion" if enable_graph else "hybrid_baseline",
        "queries_evaluated": num_q,
        "metrics": {
            "hit_rate_at_5": round(hr_5, 4),
            "hit_rate_at_10": round(hr_10, 4),
            "mrr": round(mrr, 4),
            "latency_median_ms": round(med_lat, 2),
            "latency_p95_ms": round(p95_lat, 2),
            "latency_mean_ms": round(mean_lat, 2)
        },
        "query_results": query_results
    }


def main():
    print("=" * 70)
    print("Benchmarking Hybrid Baseline vs. Hybrid + Graph Expansion (Milestone 4B.1)")
    print("=" * 70)

    with open(QUERIES_PATH, "r", encoding="utf-8") as f:
        queries = json.load(f)

    with open(GOLD_PATH, "r", encoding="utf-8") as f:
        gold_data = json.load(f)

    gold_by_id = {g["query_id"]: g for g in gold_data}

    retriever = GraphExpandedRetriever()

    # 1. Run Baseline
    print(f"Running Hybrid Baseline on {len(queries)} legal queries...")
    baseline_run = evaluate_run(retriever, queries, gold_by_id, enable_graph=False)

    # 2. Run Graph Expansion
    print(f"Running Hybrid + Graph Expansion on {len(queries)} legal queries...")
    graph_run = evaluate_run(retriever, queries, gold_by_id, enable_graph=True)

    print("\n=== BENCHMARK COMPARISON ===")
    print(f"{'Metric':<25} | {'Hybrid Baseline':<18} | {'Hybrid + Graph Exp':<20} | {'Delta':<10}")
    print("-" * 75)

    b_m = baseline_run["metrics"]
    g_m = graph_run["metrics"]

    def row(name, b_val, g_val, fmt="{:.4f}"):
        delta = g_val - b_val
        d_str = f"{delta:+.4f}" if isinstance(b_val, float) and "lat" not in name else f"{delta:+.2f}ms"
        b_str = fmt.format(b_val)
        g_str = fmt.format(g_val)
        print(f"{name:<25} | {b_str:<18} | {g_str:<20} | {d_str:<10}")

    row("Hit Rate @ 5 (HR@5)", b_m["hit_rate_at_5"], g_m["hit_rate_at_5"])
    row("Hit Rate @ 10 (HR@10)", b_m["hit_rate_at_10"], g_m["hit_rate_at_10"])
    row("MRR", b_m["mrr"], g_m["mrr"])
    row("Median Latency (ms)", b_m["latency_median_ms"], g_m["latency_median_ms"], "{:.2f}")
    row("p95 Latency (ms)", b_m["latency_p95_ms"], g_m["latency_p95_ms"], "{:.2f}")
    row("Mean Latency (ms)", b_m["latency_mean_ms"], g_m["latency_mean_ms"], "{:.2f}")

    # Query-by-Query rank comparison
    rank_changes = []
    improved = 0
    degraded = 0
    unchanged = 0
    for b_q, g_q in zip(baseline_run["query_results"], graph_run["query_results"]):
        b_rank = b_q["first_relevant_rank"]
        g_rank = g_q["first_relevant_rank"]
        delta = None
        if b_rank and g_rank:
            delta = b_rank - g_rank  # positive means improved rank (e.g. from 7 to 6)
            if delta > 0:
                improved += 1
            elif delta < 0:
                degraded += 1
            else:
                unchanged += 1
        else:
            unchanged += 1

        rank_changes.append({
            "query_id": b_q["query_id"],
            "baseline_rank": b_rank,
            "graph_rank": g_rank,
            "rank_delta": delta,
            "latency_hybrid_ms": b_q["latency_ms"],
            "latency_graph_ms": g_q["latency_ms"]
        })

    benchmark_export = {
        "benchmark_title": "NyayaVarta Milestone 4B.1 Graph Retrieval Optimization Benchmark",
        "benchmark_version": "v2",
        "benchmark_type": "exploratory",
        "code_version": "1.1.0",
        "graph_version": "v2",
        "corpus_version": "aws_sc_782",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "provenance_disclosure": {
            "queries_count": len(queries),
            "source_file": QUERIES_PATH,
            "gold_file": GOLD_PATH,
            "status": "Internally authored evaluation set (Milestone 3.1); exploratory evaluation."
        },
        "optimizations_applied": [
            "in_memory_index_preloading",
            "idf_statutory_provision_filtering",
            "ubiquitous_umbrella_provision_suppression",
            "statutory_vs_constitutional_weight_calibration",
            "provenance_tracking_on_candidates",
            "disabled_by_default_retrieval_guardrail"
        ],
        "metric_definitions": {
            "hit_rate_at_5": "Fraction of queries where Top-5 contains at least one gold relevant document (distinct from full recall).",
            "hit_rate_at_10": "Fraction of queries where Top-10 contains at least one gold relevant document.",
            "mrr": "Mean Reciprocal Rank of the first relevant document in top-k results.",
            "latency": "Elapsed wall-clock time in milliseconds from query receipt to ranked result emission."
        },
        "comparison_summary": {
            "improved_queries": improved,
            "degraded_queries": degraded,
            "unchanged_queries": unchanged,
            "baseline_mrr": b_m["mrr"],
            "graph_mrr": g_m["mrr"],
            "baseline_median_latency_ms": b_m["latency_median_ms"],
            "graph_median_latency_ms": g_m["latency_median_ms"],
            "latency_speedup_factor": round(11333.99 / max(g_m["latency_median_ms"], 1.0), 1)
        },
        "rank_changes_query_by_query": rank_changes,
        "baseline_hybrid": baseline_run,
        "hybrid_plus_graph": graph_run
    }

    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(benchmark_export, f, indent=4)

    print(f"\nSaved benchmark results to {OUT_JSON}")


if __name__ == "__main__":
    main()
