"""
RAG Evaluation Benchmark Runner for NyayaVarta (Milestone 5A).

Evaluates end-to-end evidence-grounded legal question answering:
1. Retrieval Metrics (reported separately): Hit Rate @ 3, Hit Rate @ 5, MRR.
2. Answer Generation & Grounding Metrics:
   - Citation Validity Rate (% citations matching supplied evidence)
   - Hallucinated Citation Rate (% invalid citation IDs)
   - Abstention Accuracy on out-of-corpus / unanswerable queries
   - Evidence Offset Integrity Rate (% passages matching canonical full_text)
   - Latency statistics (retrieval, assembly, generation, validation, total)
3. Per-example failure diagnostics.
"""
import os
import sys
import json
import time
import statistics
from typing import Dict, Any, List

sys.path.insert(0, ".")
from services.rag.pipeline import RAGPipeline
from services.rag.providers import MockLLMProvider
from services.rag.evidence import verify_evidence_offsets

DATASET_PATH = "evaluation/rag/rag_eval_dataset.json"
REPORT_PATH = "evaluation/rag/rag_evaluation_report.json"


def evaluate_rag():
    print("=" * 75)
    print("NyayaVarta Milestone 5A: Evidence-Grounded RAG Benchmark Evaluation")
    print("=" * 75)

    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    pipeline = RAGPipeline(llm_provider=MockLLMProvider())

    retrieval_hits_3 = 0
    retrieval_hits_5 = 0
    reciprocal_ranks = []
    answerable_count = 0

    abstention_correct = 0
    unanswerable_count = 0

    total_citations_generated = 0
    valid_citations_generated = 0
    invalid_citations_generated = 0

    total_passages_verified = 0
    perfect_offset_passages = 0

    latencies_retrieval = []
    latencies_assembly = []
    latencies_generation = []
    latencies_total = []

    per_example_results = []
    failures = []

    for item in dataset:
        qid = item["query_id"]
        q_text = item["question"]
        expected_type = item["expected_answerability"]
        expected_docs = set(item.get("expected_document_ids", []))

        t0 = time.perf_counter()
        result = pipeline.query(query_text=q_text, top_k_judgments=5, max_passages=5)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        latencies_retrieval.append(result.timing_ms.get("retrieval_ms", 0.0))
        latencies_assembly.append(result.timing_ms.get("evidence_assembly_ms", 0.0))
        latencies_generation.append(result.timing_ms.get("generation_ms", 0.0))
        latencies_total.append(result.timing_ms.get("total_ms", elapsed_ms))

        # Check retrieval on answerable queries
        hit_3 = False
        hit_5 = False
        rr = 0.0
        retrieved_ids = [c for c in result.retrieval_metadata.get("top_candidates", [])]

        if expected_type == "answerable":
            answerable_count += 1
            for rank_idx, doc_id in enumerate(retrieved_ids):
                if doc_id in expected_docs:
                    if rank_idx < 3:
                        hit_3 = True
                    if rank_idx < 5:
                        hit_5 = True
                    rr = 1.0 / (rank_idx + 1)
                    break

            if hit_3:
                retrieval_hits_3 += 1
            if hit_5:
                retrieval_hits_5 += 1
            reciprocal_ranks.append(rr)

            if not hit_5:
                failures.append({
                    "query_id": qid,
                    "failure_type": "retrieval_miss",
                    "detail": f"Expected docs {list(expected_docs)} not found in top 5 retrieved: {retrieved_ids[:5]}"
                })
        else:
            unanswerable_count += 1
            # Check abstention behavior on unanswerable queries
            is_abstained = (result.status == "insufficient_evidence") or ("insufficient evidence" in result.answer.lower())
            if is_abstained:
                abstention_correct += 1
            else:
                failures.append({
                    "query_id": qid,
                    "failure_type": "false_answering_on_unanswerable",
                    "detail": f"System attempted to answer out-of-corpus question instead of abstaining: '{result.answer[:100]}...'"
                })

        # Check citation validity
        val = result.citation_validation
        total_citations_generated += len(val.cited_source_ids)
        valid_citations_generated += len(val.valid_source_ids)
        invalid_citations_generated += len(val.invalid_source_ids)

        if val.invalid_source_ids:
            failures.append({
                "query_id": qid,
                "failure_type": "hallucinated_citation",
                "detail": f"Generated invalid citation IDs: {val.invalid_source_ids}"
            })

        # Check passage offset integrity
        if result.evidence_passages:
            verified, errors = verify_evidence_offsets(result.evidence_passages)
            total_passages_verified += len(result.evidence_passages)
            if verified:
                perfect_offset_passages += len(result.evidence_passages)
            else:
                failures.append({
                    "query_id": qid,
                    "failure_type": "offset_mismatch",
                    "detail": f"Offset errors: {errors}"
                })

        per_example_results.append({
            "query_id": qid,
            "question": q_text,
            "domain": item["legal_domain"],
            "expected_answerability": expected_type,
            "status": result.status,
            "answer_preview": result.answer[:120] + "..." if len(result.answer) > 120 else result.answer,
            "retrieved_candidates": retrieved_ids[:3],
            "evidence_count": len(result.evidence_passages),
            "citations_cited": val.cited_source_ids,
            "citations_valid": val.valid_source_ids,
            "citations_invalid": val.invalid_source_ids,
            "timing_ms": result.timing_ms
        })

    # Aggregate metrics
    hr_3 = (retrieval_hits_3 / answerable_count) if answerable_count else 0.0
    hr_5 = (retrieval_hits_5 / answerable_count) if answerable_count else 0.0
    mrr = statistics.mean(reciprocal_ranks) if reciprocal_ranks else 0.0

    abstention_rate = (abstention_correct / unanswerable_count) if unanswerable_count else 0.0
    citation_validity_rate = (valid_citations_generated / total_citations_generated) if total_citations_generated else 1.0
    hallucinated_rate = (invalid_citations_generated / total_citations_generated) if total_citations_generated else 0.0
    offset_fidelity_rate = (perfect_offset_passages / total_passages_verified) if total_passages_verified else 1.0

    med_lat_total = statistics.median(latencies_total) if latencies_total else 0.0
    p95_lat_total = latencies_total[int(len(latencies_total) * 0.95)] if latencies_total else 0.0

    report = {
        "benchmark_title": "NyayaVarta Milestone 5B Evidence-Grounded RAG Benchmark",
        "benchmark_version": "v1.1",
        "benchmark_type": "exploratory_internal",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "provenance_disclosure": {
            "total_queries": len(dataset),
            "answerable_queries": answerable_count,
            "unanswerable_queries": unanswerable_count,
            "source_corpus": "AWS Open Data 782 SC judgments (2024)",
            "generator_mode": "MockLLMProvider (deterministic CPU testing)",
            "benchmark_status": "Developer-authored evaluation benchmark (Milestones 5A/5B); exploratory evaluation not independently verified by legal practitioners."
        },
        "retrieval_metrics": {
            "metric_definitions": {
                "hit_rate_at_3": "% of answerable queries where at least one expected gold judgment appears in top 3 retrieved",
                "hit_rate_at_5": "% of answerable queries where at least one expected gold judgment appears in top 5 retrieved",
                "mrr": "Mean Reciprocal Rank over answerable queries: mean(1 / rank_first_relevant_doc)"
            },
            "hit_rate_at_3": round(hr_3, 4),
            "hit_rate_at_5": round(hr_5, 4),
            "mrr": round(mrr, 4)
        },
        "generation_and_grounding_metrics": {
            "metric_definitions": {
                "abstention_accuracy": "Explicit count of correct abstentions on unanswerable queries divided by total unanswerable queries",
                "citation_reference_validity": "% of cited [E#] tags that match supplied evidence passages",
                "semantic_support_status": "Status of semantic legal verification (distinguished from reference validity)"
            },
            "abstention_count": f"{abstention_correct}/{unanswerable_count}",
            "abstention_accuracy_on_unanswerable": round(abstention_rate, 4),
            "citation_validity_rate": round(citation_validity_rate, 4),
            "hallucinated_citation_rate": round(hallucinated_rate, 4),
            "evidence_offset_fidelity_rate": round(offset_fidelity_rate, 4),
            "semantic_support_status": "not_evaluated",
            "total_citations_evaluated": total_citations_generated,
            "total_passages_verified": total_passages_verified
        },
        "latency_metrics_ms": {
            "retrieval_median_ms": round(statistics.median(latencies_retrieval), 2),
            "evidence_assembly_median_ms": round(statistics.median(latencies_assembly), 2),
            "generation_median_ms": round(statistics.median(latencies_generation), 2),
            "total_median_ms": round(med_lat_total, 2),
            "total_p95_ms": round(p95_lat_total, 2)
        },
        "per_example_failures_count": len(failures),
        "failures": failures,
        "per_example_results": per_example_results
    }

    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4)

    print("\n=== BENCHMARK RESULTS SUMMARY ===")
    print(f"Total Evaluated Queries: {len(dataset)} ({answerable_count} answerable, {unanswerable_count} unanswerable)")
    print(f"Retrieval Hit Rate @ 3: {hr_3:.2%}")
    print(f"Retrieval Hit Rate @ 5: {hr_5:.2%}")
    print(f"Retrieval MRR:          {mrr:.4f} (MRR = mean reciprocal rank of 1st gold hit)")
    print("-" * 50)
    print(f"Abstention Accuracy:    {abstention_rate:.2%} ({abstention_correct}/{unanswerable_count} correct abstentions)")
    print(f"Citation Validity Rate: {citation_validity_rate:.2%} ({valid_citations_generated}/{total_citations_generated} valid)")
    print(f"Hallucinated Citations: {hallucinated_rate:.2%} ({invalid_citations_generated} hallucinated)")
    print(f"Offset Fidelity Rate:   {offset_fidelity_rate:.2%} ({perfect_offset_passages}/{total_passages_verified} exact slices)")
    print(f"Semantic Support Status: not_evaluated (syntactic reference check only)")
    print("-" * 50)
    print(f"Median Total Latency:   {med_lat_total:.2f} ms")
    print(f"p95 Total Latency:      {p95_lat_total:.2f} ms")
    print(f"Total Failures:         {len(failures)}")
    print(f"\nDetailed report saved to: {REPORT_PATH}")


if __name__ == "__main__":
    evaluate_rag()
