"""
Milestone 11 Task 9: Isolated Graph-Expansion Experiment.

Evaluates the impact of Graph V2's verified cross-document citation links on retrieval quality
over the Milestone 10 42-query benchmark (`evaluation/rag/milestone10_eval_dataset.json`).

Compares:
1. Baseline Hybrid (Dense + BM25 via RRF, no graph expansion)
2. Hybrid + Graph V2 Verified Cross-Document Citation Links (CITES edges only)
3. Hybrid + Graph V2 Combined (CITES + Grounded Statutory Provisions)

Measures:
- HitRate@1, HitRate@3, HitRate@5, HitRate@10
- Mean Reciprocal Rank (MRR)
- Additional relevant documents retrieved via graph expansion
- Irrelevant graph expansions (false positive drift)
- False links traversed (hallucinated / out-of-corpus links)
- Latency (median, mean, p95 in ms)
- Number of edges traversed per query

Strictly verifies that the production RAG pipeline query path remains untouched.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import json
import time
import statistics
from typing import Dict, Any, List, Set
from collections import defaultdict

from services.graph.sqlite_store import SQLiteGraphStore
from services.graph.graph_retriever import GraphExpandedRetriever
from services.rag.pipeline import RAGPipeline

EVAL_DATASET_PATH = "evaluation/rag/milestone10_eval_dataset.json"
OUTPUT_REPORT_PATH = "evaluation/graph/milestone11_graph_expansion_eval.json"
GRAPH_V2_DB = "data/processed/graph/v2/graph.db"


def run_graph_expansion_evaluation():
    print("=" * 70)
    print("Milestone 11 Task 9: Isolated Graph-Expansion Evaluation")
    print("=" * 70)

    # 1. Verify Production RAG Safety Invariants
    print("\n--- Verifying Production RAG Safety ---")
    pipeline = RAGPipeline()
    import inspect
    sig = inspect.signature(pipeline.query)
    assert sig.parameters["enable_graph"].default is False, "CRITICAL: pipeline.query default enable_graph is not False!"
    print(" Verified: Production pipeline.query() defaults to enable_graph=False.")

    retriever_default = GraphExpandedRetriever()
    sig_ret = inspect.signature(retriever_default.retrieve)
    assert sig_ret.parameters["enable_graph"].default is False, "CRITICAL: GraphExpandedRetriever.retrieve default is not False!"
    print(" Verified: GraphExpandedRetriever.retrieve() defaults to enable_graph=False.")

    # 2. Load Evaluation Dataset
    assert os.path.exists(EVAL_DATASET_PATH), f"Eval dataset not found at {EVAL_DATASET_PATH}"
    with open(EVAL_DATASET_PATH, "r", encoding="utf-8") as f:
        queries = json.load(f)

    total_queries = len(queries)
    answerable_queries = [q for q in queries if q.get("sufficient_evidence_in_corpus", False)]
    unanswerable_queries = [q for q in queries if not q.get("sufficient_evidence_in_corpus", False)]
    print(f"Loaded {total_queries} queries: {len(answerable_queries)} answerable, {len(unanswerable_queries)} unanswerable.")

    # 3. Initialize Isolated Graph Store V2 & Retrievers
    print(f"\n--- Loading Graph V2 from {GRAPH_V2_DB} ---")
    graph_store_v2 = SQLiteGraphStore(db_path=GRAPH_V2_DB, preload_index=True)
    stats = graph_store_v2.get_graph_stats()
    print(f"Graph V2 loaded into memory. Total nodes: {stats['total_nodes']}, Total edges: {stats['total_edges']}")
    print(f"CITES edges: {stats['edges_by_type'].get('CITES', 0)}, MENTIONS_PROVISION edges: {stats['edges_by_type'].get('MENTIONS_PROVISION', 0)}")

    # Configurations to evaluate
    configs = {
        "baseline_hybrid": {
            "name": "Baseline Hybrid (No Graph)",
            "retriever": GraphExpandedRetriever(graph_store=graph_store_v2),
            "enable_graph": False,
            "statute_weight": 0.0,
            "citation_weight": 0.0
        },
        "graph_v2_citations_only": {
            "name": "Hybrid + Graph V2 Cross-Doc Citations Only",
            "retriever": GraphExpandedRetriever(
                graph_store=graph_store_v2,
                citation_weight=0.85,
                statute_weight=0.0,
                alpha=0.25,
                seed_k=5
            ),
            "enable_graph": True,
            "statute_weight": 0.0,
            "citation_weight": 0.85
        },
        "graph_v2_combined": {
            "name": "Hybrid + Graph V2 Combined (Citations + Grounded Statutes)",
            "retriever": GraphExpandedRetriever(
                graph_store=graph_store_v2,
                citation_weight=0.70,
                statute_weight=0.30,
                alpha=0.20,
                seed_k=5
            ),
            "enable_graph": True,
            "statute_weight": 0.30,
            "citation_weight": 0.70
        }
    }

    # Warmup
    print("\nWarming up retrievers...")
    warmup_q = queries[0]["question"]
    for cfg in configs.values():
        cfg["retriever"].retrieve(warmup_q, top_k=10, enable_graph=cfg["enable_graph"])

    results_by_config = {}

    for cfg_key, cfg in configs.items():
        print(f"\nRunning evaluation for: {cfg['name']}...")
        latencies_ms = []
        hits_at_1 = 0
        hits_at_3 = 0
        hits_at_5 = 0
        hits_at_10 = 0
        reciprocal_ranks = []
        per_query_data = []

        total_edges_traversed = 0
        total_additional_relevant = 0
        total_irrelevant_expansions = 0
        total_false_links = 0

        retriever = cfg["retriever"]
        enable_graph = cfg["enable_graph"]

        for q in queries:
            qid = q["query_id"]
            question = q["question"]
            gold_docs = set(q.get("expected_document_ids", []))
            is_answerable = q.get("sufficient_evidence_in_corpus", False)

            t0 = time.perf_counter()
            ret_docs = retriever.retrieve(question, top_k=10, enable_graph=enable_graph)
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            latencies_ms.append(elapsed_ms)

            retrieved_ids = [d["document_id"] for d in ret_docs]

            # Metric evaluation (only evaluated for answerable queries with gold docs)
            q_hit_1 = False
            q_hit_3 = False
            q_hit_5 = False
            q_hit_10 = False
            rr = 0.0

            if is_answerable and gold_docs:
                if any(doc_id in gold_docs for doc_id in retrieved_ids[:1]):
                    q_hit_1 = True
                    hits_at_1 += 1
                if any(doc_id in gold_docs for doc_id in retrieved_ids[:3]):
                    q_hit_3 = True
                    hits_at_3 += 1
                if any(doc_id in gold_docs for doc_id in retrieved_ids[:5]):
                    q_hit_5 = True
                    hits_at_5 += 1
                if any(doc_id in gold_docs for doc_id in retrieved_ids[:10]):
                    q_hit_10 = True
                    hits_at_10 += 1

                for rank_idx, doc_id in enumerate(retrieved_ids):
                    if doc_id in gold_docs:
                        rr = 1.0 / (rank_idx + 1)
                        break
                reciprocal_ranks.append(rr)

            # Analyze graph expansion behavior
            edges_traversed_query = 0
            additional_relevant_query = []
            irrelevant_expansions_query = []
            false_links_query = []

            if enable_graph:
                for doc in ret_docs:
                    provs = doc.get("expansion_provenance", [])
                    is_graph_disc = doc.get("is_graph_discovered", False)
                    doc_id = doc["document_id"]

                    for p in provs:
                        p_type = p.get("type")
                        if p_type in ["citation_expansion", "statutory_expansion"]:
                            edges_traversed_query += 1
                            # Check for false links: link targeting invalid or non-corpus doc
                            if not doc_id.startswith("2024_"):
                                false_links_query.append(doc_id)

                    if is_graph_disc:
                        if doc_id in gold_docs:
                            additional_relevant_query.append(doc_id)
                        else:
                            irrelevant_expansions_query.append(doc_id)

            total_edges_traversed += edges_traversed_query
            total_additional_relevant += len(additional_relevant_query)
            total_irrelevant_expansions += len(irrelevant_expansions_query)
            total_false_links += len(false_links_query)

            per_query_data.append({
                "query_id": qid,
                "question": question,
                "is_answerable": is_answerable,
                "gold_docs": list(gold_docs),
                "top_5_retrieved": retrieved_ids[:5],
                "first_gold_rank": int(1.0 / rr) if rr > 0 else None,
                "hit_at_5": q_hit_5,
                "latency_ms": round(elapsed_ms, 2),
                "edges_traversed": edges_traversed_query,
                "additional_relevant_docs": additional_relevant_query,
                "irrelevant_expansions": irrelevant_expansions_query,
                "false_links": false_links_query
            })

        num_eval_queries = len(answerable_queries)
        hr1 = round(hits_at_1 / num_eval_queries, 4) if num_eval_queries else 0.0
        hr3 = round(hits_at_3 / num_eval_queries, 4) if num_eval_queries else 0.0
        hr5 = round(hits_at_5 / num_eval_queries, 4) if num_eval_queries else 0.0
        hr10 = round(hits_at_10 / num_eval_queries, 4) if num_eval_queries else 0.0
        mrr = round(statistics.mean(reciprocal_ranks), 4) if reciprocal_ranks else 0.0

        lat_median = round(statistics.median(latencies_ms), 2)
        lat_mean = round(statistics.mean(latencies_ms), 2)
        latencies_sorted = sorted(latencies_ms)
        p95_idx = int(0.95 * len(latencies_sorted))
        lat_p95 = round(latencies_sorted[min(p95_idx, len(latencies_sorted) - 1)], 2)

        results_by_config[cfg_key] = {
            "config_name": cfg["name"],
            "total_queries": total_queries,
            "answerable_queries": num_eval_queries,
            "hit_rate_at_1": hr1,
            "hit_rate_at_3": hr3,
            "hit_rate_at_5": hr5,
            "hit_rate_at_10": hr10,
            "mrr": mrr,
            "median_latency_ms": lat_median,
            "mean_latency_ms": lat_mean,
            "p95_latency_ms": lat_p95,
            "total_edges_traversed": total_edges_traversed,
            "additional_relevant_docs_retrieved": total_additional_relevant,
            "irrelevant_graph_expansions": total_irrelevant_expansions,
            "false_links_traversed": total_false_links,
            "per_query_data": per_query_data
        }

    # 4. Print Summary Comparison Table
    print("\n" + "=" * 80)
    print(f"{'Metric':<35} | {'Baseline Hybrid':<14} | {'Graph Citations':<15} | {'Graph Combined':<15}")
    print("-" * 80)
    b = results_by_config["baseline_hybrid"]
    c = results_by_config["graph_v2_citations_only"]
    g = results_by_config["graph_v2_combined"]

    print(f"{'Hit Rate @ 1 (HR@1)':<35} | {b['hit_rate_at_1']:<14.4f} | {c['hit_rate_at_1']:<15.4f} | {g['hit_rate_at_1']:<15.4f}")
    print(f"{'Hit Rate @ 3 (HR@3)':<35} | {b['hit_rate_at_3']:<14.4f} | {c['hit_rate_at_3']:<15.4f} | {g['hit_rate_at_3']:<15.4f}")
    print(f"{'Hit Rate @ 5 (HR@5)':<35} | {b['hit_rate_at_5']:<14.4f} | {c['hit_rate_at_5']:<15.4f} | {g['hit_rate_at_5']:<15.4f}")
    print(f"{'Hit Rate @ 10 (HR@10)':<35} | {b['hit_rate_at_10']:<14.4f} | {c['hit_rate_at_10']:<15.4f} | {g['hit_rate_at_10']:<15.4f}")
    print(f"{'Mean Reciprocal Rank (MRR)':<35} | {b['mrr']:<14.4f} | {c['mrr']:<15.4f} | {g['mrr']:<15.4f}")
    print(f"{'Median Latency (ms)':<35} | {b['median_latency_ms']:<14.2f} | {c['median_latency_ms']:<15.2f} | {g['median_latency_ms']:<15.2f}")
    print(f"{'P95 Latency (ms)':<35} | {b['p95_latency_ms']:<14.2f} | {c['p95_latency_ms']:<15.2f} | {g['p95_latency_ms']:<15.2f}")
    print(f"{'Total Edges Traversed':<35} | {b['total_edges_traversed']:<14} | {c['total_edges_traversed']:<15} | {g['total_edges_traversed']:<15}")
    print(f"{'Additional Relevant Docs Found':<35} | {b['additional_relevant_docs_retrieved']:<14} | {c['additional_relevant_docs_retrieved']:<15} | {g['additional_relevant_docs_retrieved']:<15}")
    print(f"{'Irrelevant Graph Expansions':<35} | {b['irrelevant_graph_expansions']:<14} | {c['irrelevant_graph_expansions']:<15} | {g['irrelevant_graph_expansions']:<15}")
    print(f"{'False Links Traversed':<35} | {b['false_links_traversed']:<14} | {c['false_links_traversed']:<15} | {g['false_links_traversed']:<15}")
    print("=" * 80)

    # 5. Export JSON Report
    os.makedirs(os.path.dirname(OUTPUT_REPORT_PATH), exist_ok=True)
    report = {
        "benchmark_name": "Milestone 11 Isolated Graph Expansion Evaluation",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "dataset_path": EVAL_DATASET_PATH,
        "total_queries": total_queries,
        "answerable_queries": len(answerable_queries),
        "unanswerable_queries": len(unanswerable_queries),
        "production_safety_verified": True,
        "summary": {
            "baseline_hybrid": {
                "hr1": b["hit_rate_at_1"],
                "hr3": b["hit_rate_at_3"],
                "hr5": b["hit_rate_at_5"],
                "hr10": b["hit_rate_at_10"],
                "mrr": b["mrr"],
                "median_latency_ms": b["median_latency_ms"]
            },
            "graph_v2_citations_only": {
                "hr1": c["hit_rate_at_1"],
                "hr3": c["hit_rate_at_3"],
                "hr5": c["hit_rate_at_5"],
                "hr10": c["hit_rate_at_10"],
                "mrr": c["mrr"],
                "median_latency_ms": c["median_latency_ms"],
                "edges_traversed": c["total_edges_traversed"],
                "additional_relevant": c["additional_relevant_docs_retrieved"],
                "irrelevant_expansions": c["irrelevant_graph_expansions"],
                "false_links": c["false_links_traversed"]
            },
            "graph_v2_combined": {
                "hr1": g["hit_rate_at_1"],
                "hr3": g["hit_rate_at_3"],
                "hr5": g["hit_rate_at_5"],
                "hr10": g["hit_rate_at_10"],
                "mrr": g["mrr"],
                "median_latency_ms": g["median_latency_ms"],
                "edges_traversed": g["total_edges_traversed"],
                "additional_relevant": g["additional_relevant_docs_retrieved"],
                "irrelevant_expansions": g["irrelevant_graph_expansions"],
                "false_links": g["false_links_traversed"]
            }
        },
        "configurations": results_by_config
    }

    with open(OUTPUT_REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"\nReport successfully exported to {OUTPUT_REPORT_PATH}")
    return report


if __name__ == "__main__":
    run_graph_expansion_evaluation()
