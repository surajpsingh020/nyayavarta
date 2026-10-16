"""
Controlled Comparison Benchmark Runner for NyayaVarta Milestone 7:
Structured Output vs. Free-Form Generation on Local Ollama (phi3.5:latest).

Executes the 10-query canonical benchmark using structured JSON generation,
loads the Milestone 6.1 baseline results, and computes comparative metrics.
"""
import os
import sys
import time
import json
import argparse
from typing import List, Dict, Any, Optional

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from services.rag.models import RAGResult, StructuredAnswer
from services.rag.pipeline import RAGPipeline
from services.rag.providers import LocalOllamaProvider, MockLLMProvider
from services.rag.claim_reviewer import extract_claim_review_records, ClaimReviewRecord


TARGET_QUERY_IDS = [
    # 6 Answerable queries across categories
    "M6_001",  # Single judgment: Art 142 IIT admission fee glitch
    "M6_002",  # Statutory interpretation: Sec 62 IBC appeal standing
    "M6_004",  # Statutory interpretation: Sec 18 Limitation balance sheet
    "M6_005",  # Statutory interpretation: Sec 148 NI Act signatory deposit
    "M6_007",  # Single judgment: Prison manual caste discrimination
    "M6_009",  # Statutory interpretation: CGST Sec 17(5)(d) plant functionality
    # 4 Abstention / Unanswerable queries
    "M6_017",  # DPDP Act Sec 18 (out of corpus)
    "M6_018",  # Muslim law coparcenary (out of domain)
    "M6_019",  # Anticipatory bail in contempt (statutory exception)
    "M6_020",  # Patents Act Sec 3(j) GM mustard (unresolved controversy)
]


def load_dataset(dataset_path: str = "evaluation/rag/milestone6_e2e_eval_dataset.json") -> List[Dict[str, Any]]:
    with open(dataset_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    dataset_map = {d["query_id"]: d for d in data}
    return [dataset_map[qid] for qid in TARGET_QUERY_IDS if qid in dataset_map]


def load_baseline_6_1(baseline_path: str = "evaluation/rag/milestone6_1_ollama_eval.json") -> Optional[Dict[str, Any]]:
    if not os.path.exists(baseline_path):
        return None
    with open(baseline_path, "r", encoding="utf-8") as f:
        return json.load(f)


def run_benchmark(
    provider_type: str = "ollama",
    model_name: str = "phi3.5:latest",
    num_predict: int = 140,
    max_chars_per_passage: int = 1000,
    max_passages: int = 1,
    timeout: float = 240.0,
    output_report_path: str = "evaluation/rag/milestone7_structured_comparison_report.json",
    output_claims_path: str = "evaluation/rag/milestone7_structured_claims.jsonl"
):
    print("=" * 80)
    print(f"NyayaVarta Milestone 7: Controlled Comparison Benchmark ({provider_type.upper()})")
    print("=" * 80)

    dataset = load_dataset()
    print(f"Loaded {len(dataset)} targeted benchmark queries.")

    # Initialize Provider
    if provider_type.lower() == "ollama":
        avail = LocalOllamaProvider.check_availability(model_name=model_name)
        if not avail["available"]:
            raise RuntimeError(f"Ollama daemon not reachable at http://localhost:11434: {avail['error']}")
        if not avail["target_model_installed"]:
            raise RuntimeError(f"Model {model_name} is not installed in local Ollama: {avail['models']}")
        print(f"Local Ollama online: {avail['models']}")
        print(f"Using model: {model_name} (timeout={timeout}s, num_predict={num_predict})")
        active_provider = LocalOllamaProvider(
            model_name=model_name,
            timeout=timeout,
            default_options={
                "num_ctx": 2048,
                "num_predict": num_predict,
                "temperature": 0.0,
                "num_thread": 8
            }
        )
    else:
        print("Using deterministic MockLLMProvider in structured mode")
        active_provider = MockLLMProvider()

    pipeline = RAGPipeline()
    structured_query_evals: List[Dict[str, Any]] = []
    all_claim_records: List[ClaimReviewRecord] = []

    gate_fast_exits = 0
    llm_invocations = 0
    structured_valid_count = 0
    unknown_evidence_ids_count = 0
    answers_accepted = 0
    abstentions_count = 0
    timeouts_count = 0

    t_bench_start = time.perf_counter()

    for idx, item in enumerate(dataset, 1):
        qid = item["query_id"]
        qtext = item["question"]
        category = item["category"]
        domain = item["legal_domain"]
        exp_answerable = item["sufficient_evidence_in_corpus"]

        print(f"\n[{idx}/{len(dataset)}] Query {qid} ({category}):", flush=True)
        print(f"  Q: {qtext[:80]}...", flush=True)

        t_q_start = time.perf_counter()
        is_timeout = False
        error_detail = None
        rag_result: Optional[RAGResult] = None

        try:
            rag_result = pipeline.query(
                query_text=qtext,
                top_k_judgments=2,
                max_passages=max_passages,
                enable_graph=False,
                provider=active_provider,
                max_chars_per_passage=max_chars_per_passage,
                structured_output=True
            )
            q_latency = round(time.perf_counter() - t_q_start, 3)

            is_fast_exit = (rag_result.timing_ms.get("generation_ms", 0.0) == 0.0)
            if is_fast_exit:
                gate_fast_exits += 1
            else:
                llm_invocations += 1

            c_summary = rag_result.citation_validation
            is_struct_valid = (rag_result.structured_answer is not None)
            if is_struct_valid:
                structured_valid_count += 1
            if len(c_summary.invalid_source_ids) > 0:
                unknown_evidence_ids_count += 1

            if rag_result.status == "answered":
                answers_accepted += 1
            elif rag_result.status in ["insufficient_evidence", "empty_retrieval"]:
                abstentions_count += 1

            print(f"  Status: {rag_result.status} | Grounding: {rag_result.grounding_status} | Latency: {q_latency:.2f}s", flush=True)
            print(f"  Structured: {'YES' if is_struct_valid else 'NO'} | Validation: {c_summary.validation_status} | Cited={c_summary.cited_source_ids} Invalid={c_summary.invalid_source_ids}", flush=True)

            claims = extract_claim_review_records(rag_result, query_id=qid)
            all_claim_records.extend(claims)

            eval_entry = {
                "query_id": qid,
                "category": category,
                "legal_domain": domain,
                "query": qtext,
                "expected_answerable": exp_answerable,
                "actual_status": rag_result.status,
                "grounding_status": rag_result.grounding_status,
                "gate_only_fast_exit": is_fast_exit,
                "grounding_matches_gold": (rag_result.grounding_decision.get("is_grounded", False) == exp_answerable),
                "timing_ms": rag_result.timing_ms,
                "total_latency_seconds": q_latency,
                "num_evidence_passages": len(rag_result.evidence_passages),
                "structured_answer": rag_result.structured_answer.model_dump() if rag_result.structured_answer else None,
                "citations_summary": {
                    "is_valid": c_summary.is_valid,
                    "validation_status": c_summary.validation_status,
                    "citation_syntax_valid": c_summary.citation_syntax_valid,
                    "citation_existence_valid": c_summary.citation_existence_valid,
                    "attribution_complete": c_summary.attribution_complete,
                    "semantic_support_status": c_summary.semantic_support_status,
                    "cited_ids": c_summary.cited_source_ids,
                    "valid_ids": c_summary.valid_source_ids,
                    "invalid_ids": c_summary.invalid_source_ids,
                    "unsupported_sentences": c_summary.unsupported_sentences,
                    "validation_notes": c_summary.validation_notes
                },
                "llm_usage": rag_result.retrieval_metadata.get("llm_usage", {}),
                "answer_text": rag_result.answer,
                "claims_count": len(claims),
                "timeout": False,
                "error": None
            }
            structured_query_evals.append(eval_entry)

        except TimeoutError as te:
            timeouts_count += 1
            q_latency = round(time.perf_counter() - t_q_start, 3)
            print(f"  TIMEOUT after {q_latency:.2f}s: {te}", flush=True)
            eval_entry = {
                "query_id": qid,
                "category": category,
                "legal_domain": domain,
                "query": qtext,
                "expected_answerable": exp_answerable,
                "actual_status": "timeout",
                "grounding_status": "timeout",
                "gate_only_fast_exit": False,
                "grounding_matches_gold": False,
                "timing_ms": {"total_ms": q_latency * 1000.0},
                "total_latency_seconds": q_latency,
                "num_evidence_passages": 0,
                "structured_answer": None,
                "citations_summary": {"is_valid": False, "validation_status": "invalid"},
                "llm_usage": {},
                "answer_text": "",
                "claims_count": 0,
                "timeout": True,
                "error": str(te)
            }
            structured_query_evals.append(eval_entry)

    total_bench_time = round(time.perf_counter() - t_bench_start, 2)

    # Compute Latency Stats
    fast_exit_latencies = [e["total_latency_seconds"] for e in structured_query_evals if e["gate_only_fast_exit"]]
    generation_latencies = [e["total_latency_seconds"] for e in structured_query_evals if not e["gate_only_fast_exit"] and not e["timeout"]]

    def get_stats(vals: List[float]) -> Dict[str, Any]:
        if not vals:
            return {"count": 0, "min": 0, "median": 0, "p95": 0, "max": 0}
        s = sorted(vals)
        n = len(s)
        med = s[n // 2] if n % 2 == 1 else round((s[n // 2 - 1] + s[n // 2]) / 2, 3)
        p95_idx = min(int(n * 0.95), n - 1)
        return {
            "count": n,
            "min": round(s[0], 3),
            "median": round(med, 3),
            "p95": round(s[p95_idx], 3),
            "max": round(s[-1], 3)
        }

    fast_stats = get_stats(fast_exit_latencies)
    gen_stats = get_stats(generation_latencies)

    # Load Milestone 6.1 Baseline for Comparison
    baseline_6_1 = load_baseline_6_1()

    comparison_report = {
        "benchmark_metadata": {
            "benchmark_name": "NyayaVarta Milestone 7 Controlled Comparison (Structured Output vs. Free-Form)",
            "benchmark_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "provider_type": provider_type,
            "model_name": model_name,
            "queries_tested": len(dataset),
            "total_benchmark_duration_seconds": total_bench_time,
            "context_budget": {
                "max_passages": max_passages,
                "max_chars_per_passage": max_chars_per_passage,
                "num_predict": num_predict,
                "timeout": timeout
            }
        },
        "side_by_side_comparison": {
            "milestone_6_1_free_form": {
                "queries_completed": baseline_6_1["benchmark_metadata"]["total_queries_tested"] if baseline_6_1 else None,
                "gate_fast_exits": baseline_6_1["benchmark_metadata"]["gate_fast_exits_count"] if baseline_6_1 else None,
                "llm_invocations": baseline_6_1["benchmark_metadata"]["llm_invocations_count"] if baseline_6_1 else None,
                "answers_generated": baseline_6_1["benchmark_metadata"]["successful_generations"] if baseline_6_1 else None,
                "correct_abstentions": baseline_6_1["benchmark_metadata"]["correct_abstentions"] if baseline_6_1 else None,
                "unknown_evidence_ids_count": 1,  # M6_009 hallucinated E2, E3
                "generation_latency_median_seconds": baseline_6_1["performance_metrics"]["latency_breakdown"]["llm_generation_seconds"]["median"] if baseline_6_1 else None,
                "generation_latency_p95_seconds": baseline_6_1["performance_metrics"]["latency_breakdown"]["llm_generation_seconds"]["p95"] if baseline_6_1 else None
            },
            "milestone_7_structured": {
                "queries_completed": len(dataset) - timeouts_count,
                "gate_fast_exits": gate_fast_exits,
                "llm_invocations": llm_invocations,
                "valid_structured_output_rate": round(structured_valid_count / llm_invocations, 3) if llm_invocations > 0 else 1.0,
                "unknown_evidence_ids_count": unknown_evidence_ids_count,
                "unknown_evidence_ids_rate": round(unknown_evidence_ids_count / llm_invocations, 3) if llm_invocations > 0 else 0.0,
                "answers_accepted": answers_accepted,
                "abstentions_count": abstentions_count,
                "timeouts_count": timeouts_count,
                "generation_latency_median_seconds": gen_stats["median"],
                "generation_latency_p95_seconds": gen_stats["p95"]
            }
        },
        "latency_breakdown": {
            "fast_exit_seconds": fast_stats,
            "llm_generation_seconds": gen_stats
        },
        "query_evaluations": structured_query_evals
    }

    # Save JSON report
    os.makedirs(os.path.dirname(output_report_path), exist_ok=True)
    with open(output_report_path, "w", encoding="utf-8") as f:
        json.dump(comparison_report, f, indent=2)
    print(f"\nSaved Comparison Report: {output_report_path}")

    # Save claim review records
    os.makedirs(os.path.dirname(output_claims_path), exist_ok=True)
    with open(output_claims_path, "w", encoding="utf-8") as f:
        for cr in all_claim_records:
            f.write(json.dumps(cr.model_dump()) + "\n")
    print(f"Saved Claims Artifact: {output_claims_path}")
    print("=" * 80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Milestone 7 Controlled Comparison Runner")
    parser.add_argument("--provider", default="ollama", choices=["ollama", "mock"])
    parser.add_argument("--model-name", default="phi3.5:latest")
    parser.add_argument("--num-predict", type=int, default=140)
    parser.add_argument("--max-chars", type=int, default=1000)
    parser.add_argument("--max-passages", type=int, default=1)
    parser.add_argument("--timeout", type=float, default=240.0)
    args = parser.parse_args()

    run_benchmark(
        provider_type=args.provider,
        model_name=args.model_name,
        num_predict=args.num_predict,
        max_chars_per_passage=args.max_chars,
        max_passages=args.max_passages,
        timeout=args.timeout
    )
