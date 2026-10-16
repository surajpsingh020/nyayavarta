"""
End-to-End Legal Answer Quality & Demonstration Benchmark (Milestone 6).

Evaluates the complete NyayaVarta RAG pipeline across the 22-query Milestone 6 dataset:
- Hybrid BM25/Dense retrieval over 782 canonical 2024 SC judgments.
- Fail-closed offset verification (canonical text slicing invariant).
- PropositionGroundingGate with predicate decomposition and role classification.
- Local LLM generation via Ollama (phi3.5:latest) or reproducible Mock provider.
- Citation syntax and attribution validation.
- Claim-level review record extraction and labeling.

Outputs:
- evaluation/rag/milestone6_e2e_evaluation_report.json
- evaluation/rag/milestone6_claim_review_artifact.jsonl
"""
import os
import sys
import json
import time
import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional

sys.path.insert(0, ".")
from services.rag.pipeline import RAGPipeline
from services.rag.providers import LocalOllamaProvider, MockLLMProvider
from services.rag.claim_reviewer import (
    extract_claim_review_records,
    ClaimReviewRecord,
    export_claim_review_artifact,
    summarize_claim_reviews
)
from services.rag.models import RAGResult

DATASET_PATH = Path("evaluation/rag/milestone6_e2e_eval_dataset.json")
REPORT_PATH = Path("evaluation/rag/milestone6_e2e_evaluation_report.json")
CLAIM_ARTIFACT_PATH = Path("evaluation/rag/milestone6_claim_review_artifact.jsonl")


def evaluate_milestone6(
    provider_type: str = "ollama",
    model_name: str = "phi3.5:latest",
    dataset_path: Path = DATASET_PATH,
    output_report_path: Path = REPORT_PATH,
    output_claim_path: Path = CLAIM_ARTIFACT_PATH,
    max_queries: Optional[int] = None,
    query_ids: Optional[List[str]] = None,
    max_chars_per_passage: Optional[int] = None,
    top_k: int = 2,
    max_passages: int = 1,
    timeout: float = 240.0,
    num_predict: int = 180
) -> Dict[str, Any]:
    print("=" * 80, flush=True)
    print(f"NyayaVarta Milestone 6: End-to-End Legal Answer Benchmark ({provider_type.upper()})", flush=True)
    print("=" * 80, flush=True)

    with open(dataset_path, "r", encoding="utf-8") as f:
        dataset: List[Dict[str, Any]] = json.load(f)

    if query_ids:
        qid_set = set(query_ids)
        dataset = [d for d in dataset if d["query_id"] in qid_set]

    if max_queries:
        dataset = dataset[:max_queries]

    print(f"Loaded {len(dataset)} evaluation queries from {dataset_path}", flush=True)

    # Initialize Provider
    if provider_type.lower() == "ollama":
        avail = LocalOllamaProvider.check_availability(model_name=model_name)
        if not avail["available"]:
            raise RuntimeError(f"Ollama daemon not reachable at http://localhost:11434: {avail['error']}")
        if not avail["target_model_installed"]:
            raise RuntimeError(f"Model {model_name} is not installed in local Ollama: {avail['models']}")
        print(f"Local Ollama online: {avail['models']}", flush=True)
        print(f"Using model: {model_name} (timeout={timeout}s, num_predict={num_predict})", flush=True)
        active_provider = LocalOllamaProvider(
            model_name=model_name,
            timeout=timeout,
            default_options={"num_ctx": 2048, "num_predict": num_predict, "num_thread": 8}
        )
    else:
        print("Using deterministic MockLLMProvider", flush=True)
        active_provider = MockLLMProvider()

    pipeline = RAGPipeline()
    query_evaluations: List[Dict[str, Any]] = []
    all_claim_records: List[ClaimReviewRecord] = []

    total_t0 = time.perf_counter()
    timeouts_count = 0
    errors_count = 0

    for idx, item in enumerate(dataset, 1):
        qid = item["query_id"]
        qtext = item["question"]
        category = item["category"]
        domain = item["legal_domain"]
        exp_grounded = item["sufficient_evidence_in_corpus"]

        print(f"\n[{idx}/{len(dataset)}] Query {qid} ({category}):")
        print(f"  Q: {qtext[:80]}...")

        t_query_start = time.perf_counter()
        try:
            rag_result = pipeline.query(
                query_text=qtext,
                top_k_judgments=top_k,
                max_passages=max_passages,
                enable_graph=False,
                provider=active_provider,
                max_chars_per_passage=max_chars_per_passage
            )
            query_latency = round(time.perf_counter() - t_query_start, 3)
            print(f"  Status: {rag_result.status} | Grounding: {rag_result.grounding_status} | Latency: {query_latency:.2f}s")
            
            c_summary = rag_result.citation_validation
            valid_tag = "[VALID]" if c_summary.is_valid else "[INVALID]"
            print(f"  Citations: {valid_tag} Cited={c_summary.cited_source_ids} Valid={c_summary.valid_source_ids} Invalid={c_summary.invalid_source_ids}")
            
            # Extract Claim Review Records
            claims = extract_claim_review_records(rag_result, query_id=qid)
            all_claim_records.extend(claims)

            eval_entry = {
                "query_id": qid,
                "category": category,
                "legal_domain": domain,
                "query": qtext,
                "expected_answerable": exp_grounded,
                "actual_status": rag_result.status,
                "grounding_status": rag_result.grounding_status,
                "grounding_is_grounded": rag_result.grounding_decision.get("is_grounded", False),
                "grounding_rationale": rag_result.grounding_decision.get("rationale", ""),
                "grounding_matches_gold": (rag_result.grounding_decision.get("is_grounded", False) == exp_grounded),
                "timing_ms": rag_result.timing_ms,
                "total_latency_seconds": query_latency,
                "num_evidence_passages": len(rag_result.evidence_passages),
                "offsets_verified": rag_result.retrieval_metadata.get("offsets_verified", True),
                "citations_summary": {
                    "is_valid": c_summary.is_valid,
                    "citation_syntax_valid": c_summary.citation_syntax_valid,
                    "citation_existence_valid": c_summary.citation_existence_valid,
                    "attribution_complete": c_summary.attribution_complete,
                    "cited_ids": c_summary.cited_source_ids,
                    "valid_ids": c_summary.valid_source_ids,
                    "invalid_ids": c_summary.invalid_source_ids,
                    "unsupported_sentences": c_summary.unsupported_sentences
                },
                "llm_usage": rag_result.retrieval_metadata.get("llm_usage", {}),
                "claims_count": len(claims),
                "answer_text": rag_result.answer
            }
            query_evaluations.append(eval_entry)

        except TimeoutError as te:
            query_latency = round(time.perf_counter() - t_query_start, 3)
            timeouts_count += 1
            print(f"  [TIMEOUT] {te} ({query_latency:.2f}s)")
            query_evaluations.append({
                "query_id": qid,
                "category": category,
                "legal_domain": domain,
                "query": qtext,
                "expected_answerable": exp_grounded,
                "actual_status": "timeout",
                "grounding_status": "timeout",
                "total_latency_seconds": query_latency,
                "error": str(te)
            })
        except Exception as e:
            query_latency = round(time.perf_counter() - t_query_start, 3)
            errors_count += 1
            print(f"  [ERROR] {e} ({query_latency:.2f}s)")
            query_evaluations.append({
                "query_id": qid,
                "category": category,
                "legal_domain": domain,
                "query": qtext,
                "expected_answerable": exp_grounded,
                "actual_status": "error",
                "grounding_status": "error",
                "total_latency_seconds": query_latency,
                "error": str(e)
            })

    total_duration = round(time.perf_counter() - total_t0, 2)

    # Export Claim Review Records
    export_claim_review_artifact(all_claim_records, str(output_claim_path))
    claim_summary = summarize_claim_reviews(all_claim_records)

    # Compute aggregate metrics
    completed = [q for q in query_evaluations if q.get("actual_status") in ["answered", "insufficient_evidence", "empty_retrieval"]]
    answers_generated = sum(1 for q in completed if q["actual_status"] == "answered")
    abstentions = sum(1 for q in completed if q["actual_status"] in ["insufficient_evidence", "empty_retrieval"])
    grounding_matches = sum(1 for q in completed if q.get("grounding_matches_gold") is True)

    valid_citations_count = sum(1 for q in completed if q.get("citations_summary", {}).get("is_valid", False))
    latencies = [q["total_latency_seconds"] for q in completed]
    latencies.sort()

    median_lat = latencies[len(latencies) // 2] if latencies else 0.0
    p95_lat = latencies[int(len(latencies) * 0.95)] if latencies else 0.0

    report = {
        "benchmark_metadata": {
            "benchmark_name": f"NyayaVarta Milestone 6 End-to-End Legal Answer Benchmark ({provider_type.upper()})",
            "benchmark_timestamp": datetime.now(timezone.utc).isoformat(),
            "provider_type": provider_type,
            "model_name": model_name,
            "total_queries_tested": len(dataset),
            "total_queries_completed": len(completed),
            "answers_generated": answers_generated,
            "abstentions": abstentions,
            "timeouts": timeouts_count,
            "errors": errors_count,
            "total_benchmark_duration_seconds": total_duration,
            "context_budget": {
                "top_k": top_k,
                "max_passages": max_passages,
                "max_chars_per_passage": max_chars_per_passage
            }
        },
        "performance_metrics": {
            "grounding_gate_accuracy": round(grounding_matches / len(completed), 4) if completed else 0.0,
            "citation_validity_rate": round(valid_citations_count / len(completed), 4) if completed else 0.0,
            "latency_seconds": {
                "min": min(latencies) if latencies else 0.0,
                "median": median_lat,
                "p95": p95_lat,
                "max": max(latencies) if latencies else 0.0,
                "total": total_duration
            }
        },
        "claim_review_summary": claim_summary,
        "query_evaluations": query_evaluations
    }

    os.makedirs(output_report_path.parent, exist_ok=True)
    with open(output_report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 80)
    print("BENCHMARK COMPLETED")
    print(f"Total Queries: {len(dataset)} | Completed: {len(completed)} | Timeouts: {timeouts_count} | Errors: {errors_count}")
    print(f"Answers: {answers_generated} | Abstentions: {abstentions}")
    print(f"Grounding Gate Accuracy: {report['performance_metrics']['grounding_gate_accuracy']*100:.1f}%")
    print(f"Citation Validity Rate: {report['performance_metrics']['citation_validity_rate']*100:.1f}%")
    print(f"Median Latency: {median_lat:.2f}s | P95 Latency: {p95_lat:.2f}s")
    print(f"Claims Extracted: {claim_summary['total_claims']}")
    print(f"Report saved to: {output_report_path}")
    print(f"Claim artifact saved to: {output_claim_path}")
    print("=" * 80)

    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Milestone 6 End-to-End Evaluation Runner")
    parser.add_argument("--provider", default="ollama", choices=["ollama", "mock"], help="LLM provider")
    parser.add_argument("--model-name", default="phi3.5:latest", help="Model name")
    parser.add_argument("--max-queries", type=int, default=None, help="Limit number of queries")
    parser.add_argument("--query-ids", type=str, default=None, help="Comma-separated query IDs (e.g. M6_001,M6_002)")
    parser.add_argument("--max-chars", type=int, default=None, help="Max chars per passage (None for full passage)")
    parser.add_argument("--max-passages", type=int, default=1, help="Max passages per query (default 1)")
    parser.add_argument("--num-predict", type=int, default=180, help="Max generation tokens for Ollama (default 180)")
    parser.add_argument("--output-report", default="evaluation/rag/milestone6_e2e_evaluation_report.json")
    parser.add_argument("--output-claims", default="evaluation/rag/milestone6_claim_review_artifact.jsonl")

    args = parser.parse_args()
    qids = [x.strip() for x in args.query_ids.split(",")] if args.query_ids else None
    evaluate_milestone6(
        provider_type=args.provider,
        model_name=args.model_name,
        max_queries=args.max_queries,
        query_ids=qids,
        max_chars_per_passage=args.max_chars,
        max_passages=args.max_passages,
        num_predict=args.num_predict,
        output_report_path=Path(args.output_report),
        output_claim_path=Path(args.output_claims)
    )
