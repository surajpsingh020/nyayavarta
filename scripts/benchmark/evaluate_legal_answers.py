"""
Legal Answer Quality Evaluation Runner for NyayaVarta (Milestone 5C).

Evaluates RAG pipeline across the 20-question developer-curated evaluation dataset
(evaluation/rag/legal_answer_eval_dataset.json).
Outputs:
1. Comprehensive evaluation metrics report: evaluation/rag/legal_answer_evaluation_report.json
2. Human-in-the-loop claim review artifact: evaluation/rag/claim_review_artifact.jsonl
"""
import os
import sys
import json
import time
import argparse
from typing import Dict, Any, List

sys.path.insert(0, ".")
from services.rag.pipeline import RAGPipeline
from services.rag.providers import MockLLMProvider, LocalOllamaProvider, get_llm_provider
from services.rag.claim_reviewer import (
    extract_claim_review_records,
    export_claim_review_artifact,
    summarize_claim_reviews,
    ClaimReviewRecord
)

DATASET_PATH = "evaluation/rag/legal_answer_eval_dataset.json"
REPORT_PATH = "evaluation/rag/legal_answer_evaluation_report.json"
REVIEW_ARTIFACT_PATH = "evaluation/rag/claim_review_artifact.jsonl"


def evaluate_legal_answers(
    provider_type: str = "mock",
    model_name: str = "mock-grounded-cpu-v1",
    max_passages: int = 5,
    top_k: int = 5
) -> Dict[str, Any]:
    print("=" * 80)
    print("NyayaVarta Milestone 5C: Legal Answer Quality & Evidence Evaluation")
    print("=" * 80)

    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    if provider_type == "ollama":
        provider = LocalOllamaProvider(model_name=model_name, timeout=90.0)
    else:
        provider = MockLLMProvider()

    pipeline = RAGPipeline(llm_provider=provider)

    total_queries = len(dataset)
    answerable_count = 0
    unanswerable_count = 0

    retrieval_hits_3 = 0
    retrieval_hits_5 = 0
    reciprocal_ranks = []

    correct_abstentions = 0
    total_unanswerable_expected = 0

    total_citations_generated = 0
    valid_citations_generated = 0
    invalid_citations_generated = 0

    total_passages_verified = 0
    perfect_offset_passages = 0

    latencies_retrieval = []
    latencies_assembly = []
    latencies_generation = []
    latencies_total = []

    all_claim_records: List[ClaimReviewRecord] = []
    per_query_results = []

    for idx, item in enumerate(dataset, 1):
        qid = item["query_id"]
        q_text = item["question"]
        is_answerable = item["sufficient_evidence_in_corpus"]
        expected_docs = set(item.get("expected_document_ids", []))
        category = item.get("category", "unspecified")

        if is_answerable:
            answerable_count += 1
        else:
            total_unanswerable_expected += 1

        t0 = time.perf_counter()
        result = pipeline.query(
            query_text=q_text,
            top_k_judgments=top_k,
            max_passages=max_passages
        )
        wall_ms = (time.perf_counter() - t0) * 1000.0

        latencies_retrieval.append(result.timing_ms.get("retrieval_ms", 0.0))
        latencies_assembly.append(result.timing_ms.get("evidence_assembly_ms", 0.0))
        latencies_generation.append(result.timing_ms.get("generation_ms", 0.0))
        latencies_total.append(result.timing_ms.get("total_ms", wall_ms))

        # Retrieval evaluation for answerable queries
        hit_3 = False
        hit_5 = False
        retrieved_ids = result.retrieval_metadata.get("top_candidates", [])
        if is_answerable and expected_docs:
            rr = 0.0
            for rank_idx, doc_id in enumerate(retrieved_ids[:top_k], 1):
                if doc_id in expected_docs:
                    if rank_idx <= 3:
                        hit_3 = True
                    if rank_idx <= 5:
                        hit_5 = True
                    if rr == 0.0:
                        rr = 1.0 / rank_idx
            reciprocal_ranks.append(rr)
            if hit_3:
                retrieval_hits_3 += 1
            if hit_5:
                retrieval_hits_5 += 1

        # Abstention evaluation
        is_abstention = (result.status == "insufficient_evidence" or
                         "insufficient evidence" in result.answer.lower() or
                         result.status == "empty_retrieval")
        if not is_answerable:
            if is_abstention:
                correct_abstentions += 1

        # Citation validation stats
        val = result.citation_validation
        num_valid = len(val.valid_source_ids)
        num_invalid = len(val.invalid_source_ids)
        valid_citations_generated += num_valid
        invalid_citations_generated += num_invalid
        total_citations_generated += (num_valid + num_invalid)

        # Offset fidelity
        for ep in result.evidence_passages:
            total_passages_verified += 1
            doc_file = os.path.join("data", "processed", "aws_sc", f"{ep.document_id}.json")
            if os.path.exists(doc_file):
                try:
                    with open(doc_file, "r", encoding="utf-8") as f_doc:
                        full_txt = json.load(f_doc).get("full_text", "")
                        if full_txt[ep.start_char:ep.end_char] == ep.passage_text:
                            perfect_offset_passages += 1
                except Exception:
                    pass

        # Extract claims for review artifact
        claims_for_item = extract_claim_review_records(result, query_id=qid)
        all_claim_records.extend(claims_for_item)

        per_query_results.append({
            "query_id": qid,
            "category": category,
            "expected_answerable": is_answerable,
            "actual_status": result.status,
            "hit_top3": hit_3 if is_answerable else None,
            "hit_top5": hit_5 if is_answerable else None,
            "abstained_properly": is_abstention if not is_answerable else None,
            "citations_valid_count": num_valid,
            "citations_invalid_count": num_invalid,
            "claims_count": len(result.claims),
            "timing_ms": result.timing_ms,
            "answer_preview": result.answer[:120].replace("\n", " ") + "..."
        })

    # Summary Metrics
    hit_rate_3 = (retrieval_hits_3 / answerable_count) if answerable_count > 0 else 0.0
    hit_rate_5 = (retrieval_hits_5 / answerable_count) if answerable_count > 0 else 0.0
    mrr = (sum(reciprocal_ranks) / len(reciprocal_ranks)) if reciprocal_ranks else 0.0
    abstention_accuracy = (correct_abstentions / total_unanswerable_expected) if total_unanswerable_expected > 0 else 0.0
    citation_validity_rate = (valid_citations_generated / total_citations_generated) if total_citations_generated > 0 else 1.0
    hallucination_rate = (invalid_citations_generated / total_citations_generated) if total_citations_generated > 0 else 0.0
    offset_fidelity_rate = (perfect_offset_passages / total_passages_verified) if total_passages_verified > 0 else 1.0

    import statistics
    median_retrieval = statistics.median(latencies_retrieval) if latencies_retrieval else 0.0
    median_assembly = statistics.median(latencies_assembly) if latencies_assembly else 0.0
    median_generation = statistics.median(latencies_generation) if latencies_generation else 0.0
    median_total = statistics.median(latencies_total) if latencies_total else 0.0

    # Export review artifact
    export_claim_review_artifact(all_claim_records, output_path=REVIEW_ARTIFACT_PATH)
    claim_summary = summarize_claim_reviews(all_claim_records)

    report = {
        "benchmark_title": "NyayaVarta Milestone 5C Legal Answer Evaluation",
        "benchmark_version": "v2.0_developer_curated",
        "curation_notice": "Developer-curated dataset over 2024 Supreme Court judgments. Not independently validated by legal practitioners.",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "provider_info": {
            "provider_type": provider_type,
            "model_name": model_name
        },
        "dataset_summary": {
            "total_queries": total_queries,
            "answerable_queries": answerable_count,
            "unanswerable_queries": total_unanswerable_expected
        },
        "retrieval_metrics": {
            "hit_rate_at_3": round(hit_rate_3, 4),
            "hit_rate_at_5": round(hit_rate_5, 4),
            "mrr": round(mrr, 4),
            "mrr_definition": "Mean reciprocal rank of first relevant gold document among answerable queries"
        },
        "generation_metrics": {
            "abstention_accuracy": round(abstention_accuracy, 4),
            "abstention_counts": f"{correct_abstentions}/{total_unanswerable_expected}",
            "citation_validity_rate": round(citation_validity_rate, 4),
            "citation_counts": f"{valid_citations_generated}/{total_citations_generated}",
            "hallucinated_citation_rate": round(hallucination_rate, 4),
            "offset_fidelity_rate": round(offset_fidelity_rate, 4),
            "semantic_support_status": "not_evaluated",
            "semantic_support_notice": "Syntactic citation verification only; substantive legal support requires human claim review."
        },
        "claim_review_summary": claim_summary,
        "latency_metrics_ms": {
            "median_retrieval_ms": round(median_retrieval, 2),
            "median_evidence_assembly_ms": round(median_assembly, 2),
            "median_generation_ms": round(median_generation, 2),
            "median_total_ms": round(median_total, 2)
        },
        "per_query_results": per_query_results
    }

    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print("\n=== BENCHMARK RESULTS SUMMARY ===")
    print(f"Total Queries: {total_queries} ({answerable_count} answerable, {total_unanswerable_expected} unanswerable)")
    print(f"Retrieval Hit Rate @ 3: {hit_rate_3 * 100:.2f}%")
    print(f"Retrieval Hit Rate @ 5: {hit_rate_5 * 100:.2f}%")
    print(f"Retrieval MRR:          {mrr:.4f}")
    print("-" * 50)
    print(f"Abstention Accuracy:    {abstention_accuracy * 100:.2f}% ({correct_abstentions}/{total_unanswerable_expected})")
    print(f"Citation Validity Rate: {citation_validity_rate * 100:.2f}% ({valid_citations_generated}/{total_citations_generated})")
    print(f"Offset Fidelity Rate:   {offset_fidelity_rate * 100:.2f}% ({perfect_offset_passages}/{total_passages_verified})")
    print(f"Claim Review Records:   {claim_summary['total_claims']} generated ({claim_summary['pending_review_claims']} pending review)")
    print(f"Median Total Latency:   {median_total:.2f} ms")
    print(f"Report saved to: {REPORT_PATH}")
    print(f"Review artifact saved to: {REVIEW_ARTIFACT_PATH}")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate legal answer quality.")
    parser.add_argument("--provider", type=str, default="mock", choices=["mock", "ollama"])
    parser.add_argument("--model", type=str, default="mock-grounded-cpu-v1")
    args = parser.parse_args()

    evaluate_legal_answers(provider_type=args.provider, model_name=args.model)
