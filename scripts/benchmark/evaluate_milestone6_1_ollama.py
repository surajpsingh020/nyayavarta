"""
Milestone 6.1 Bounded Live Local Ollama Evaluation Runner.

Runs a focused, bounded evaluation of NyayaVarta over:
- 6 genuinely answerable queries (single-holding, multi-passage, statutory interpretation)
- 4 unanswerable/corpus-boundary queries requiring abstention

Separates:
- Gate-only fast exits vs. LLM generation latency
- Syntactic validity vs. semantic support
- Detailed token counts and CPU inference speeds

Outputs:
- evaluation/rag/milestone6_1_ollama_eval.json
- evaluation/rag/milestone6_1_claim_review_artifact.jsonl
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
OUTPUT_REPORT_PATH = Path("evaluation/rag/milestone6_1_ollama_eval.json")
OUTPUT_CLAIMS_PATH = Path("evaluation/rag/milestone6_1_claim_review_artifact.jsonl")

# 6 genuinely answerable + 4 abstention queries
SELECTED_QUERY_IDS = [
    # 6 Answerable
    "M6_001",  # Single-holding: Atul Kumar Art 142 IIT admission fee glitch
    "M6_002",  # Single-holding: Glas Trust Sec 62 IBC appeal standing
    "M6_004",  # Multi-passage: Prem Prakash Sec 45 PMLA twin conditions
    "M6_005",  # Multi-passage: Renjith K.G. Order XXI Rule 99 stranger redelivery
    "M6_007",  # Statutory interpretation: IDBI Bank Rule 9(4) 90-day extension
    "M6_009",  # Statutory interpretation: Shyam Narayan Ram Sec 294 CrPC admission
    # 4 Abstentions
    "M6_017",  # Corpus boundary: FCRA 2010 Sec 18 suspension
    "M6_018",  # Contradictory / Negation: Hindu joint family coparcenary to Muslims
    "M6_019",  # Doctrinal abstention: Anticipatory bail in contempt (LAQ015 baseline)
    "M6_020",  # Corpus boundary: Patents Act Sec 3(j) GM mustard (LAQ016 baseline)
]


def run_milestone6_1_eval(
    provider_type: str = "ollama",
    model_name: str = "phi3.5:latest",
    query_ids: Optional[List[str]] = None,
    max_passages: int = 1,
    max_chars_per_passage: int = 1000,
    num_predict: int = 160,
    timeout: float = 240.0,
    output_report_path: Path = OUTPUT_REPORT_PATH,
    output_claims_path: Path = OUTPUT_CLAIMS_PATH
) -> Dict[str, Any]:
    print("=" * 80, flush=True)
    print(f"NyayaVarta Milestone 6.1: Local Ollama Evaluation ({provider_type.upper()})", flush=True)
    print("=" * 80, flush=True)

    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        full_dataset = json.load(f)

    target_qids = query_ids or SELECTED_QUERY_IDS
    qid_set = set(target_qids)
    dataset = [d for d in full_dataset if d["query_id"] in qid_set]

    # Preserve order of target_qids
    dataset_map = {d["query_id"]: d for d in dataset}
    dataset = [dataset_map[qid] for qid in target_qids if qid in dataset_map]

    print(f"Loaded {len(dataset)} evaluation queries for Milestone 6.1.", flush=True)

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
            default_options={
                "num_ctx": 2048,
                "num_predict": num_predict,
                "temperature": 0.0,
                "num_thread": 8
            }
        )
    else:
        print("Using deterministic MockLLMProvider", flush=True)
        active_provider = MockLLMProvider()

    pipeline = RAGPipeline()
    query_evaluations: List[Dict[str, Any]] = []
    all_claim_records: List[ClaimReviewRecord] = []

    total_start_time = time.perf_counter()
    timeouts_count = 0
    errors_count = 0
    gate_fast_exits = 0
    llm_invocations = 0

    for idx, item in enumerate(dataset, 1):
        qid = item["query_id"]
        qtext = item["question"]
        category = item["category"]
        domain = item["legal_domain"]
        exp_answerable = item["sufficient_evidence_in_corpus"]

        print(f"\n[{idx}/{len(dataset)}] Query {qid} ({category}):", flush=True)
        print(f"  Q: {qtext[:80]}...", flush=True)

        t_query_start = time.perf_counter()
        is_timeout = False
        is_error = False
        error_detail = None
        rag_result: Optional[RAGResult] = None

        try:
            rag_result = pipeline.query(
                query_text=qtext,
                top_k_judgments=2,
                max_passages=max_passages,
                enable_graph=False,
                provider=active_provider,
                max_chars_per_passage=max_chars_per_passage
            )
            query_latency = round(time.perf_counter() - t_query_start, 3)

            is_fast_exit = (rag_result.timing_ms.get("generation_ms", 0.0) == 0.0)
            if is_fast_exit:
                gate_fast_exits += 1
            else:
                llm_invocations += 1

            c_summary = rag_result.citation_validation
            print(f"  Status: {rag_result.status} | Grounding: {rag_result.grounding_status} | Latency: {query_latency:.2f}s", flush=True)
            print(f"  Validation Status: {c_summary.validation_status} (is_valid={c_summary.is_valid}) | Cited={c_summary.cited_source_ids} Valid={c_summary.valid_source_ids} Invalid={c_summary.invalid_source_ids}", flush=True)

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
                "grounding_decision": rag_result.grounding_decision,
                "timing_ms": rag_result.timing_ms,
                "total_latency_seconds": query_latency,
                "num_evidence_passages": len(rag_result.evidence_passages),
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

        except TimeoutError as te:
            query_latency = round(time.perf_counter() - t_query_start, 3)
            timeouts_count += 1
            llm_invocations += 1
            print(f"  [TIMEOUT] Query timed out after {query_latency:.2f}s: {te}", flush=True)
            eval_entry = {
                "query_id": qid,
                "category": category,
                "legal_domain": domain,
                "query": qtext,
                "expected_answerable": exp_answerable,
                "actual_status": "timeout",
                "grounding_status": "generation_failed",
                "gate_only_fast_exit": False,
                "grounding_matches_gold": False,
                "timing_ms": {"total_ms": query_latency * 1000.0},
                "total_latency_seconds": query_latency,
                "num_evidence_passages": 0,
                "citations_summary": {"is_valid": False, "validation_status": "invalid"},
                "answer_text": None,
                "claims_count": 0,
                "timeout": True,
                "error": str(te)
            }
        except Exception as e:
            query_latency = round(time.perf_counter() - t_query_start, 3)
            errors_count += 1
            print(f"  [ERROR] Query failed with exception after {query_latency:.2f}s: {e}", flush=True)
            eval_entry = {
                "query_id": qid,
                "category": category,
                "legal_domain": domain,
                "query": qtext,
                "expected_answerable": exp_answerable,
                "actual_status": "error",
                "grounding_status": "generation_failed",
                "gate_only_fast_exit": False,
                "grounding_matches_gold": False,
                "timing_ms": {"total_ms": query_latency * 1000.0},
                "total_latency_seconds": query_latency,
                "num_evidence_passages": 0,
                "citations_summary": {"is_valid": False, "validation_status": "invalid"},
                "answer_text": None,
                "claims_count": 0,
                "timeout": False,
                "error": str(e)
            }

        query_evaluations.append(eval_entry)

    total_benchmark_time = round(time.perf_counter() - total_start_time, 2)

    # Compute separated latency statistics
    gate_latencies = [e["total_latency_seconds"] for e in query_evaluations if e.get("gate_only_fast_exit", False)]
    llm_latencies = [e["total_latency_seconds"] for e in query_evaluations if not e.get("gate_only_fast_exit", False) and not e.get("timeout", False)]
    all_latencies = [e["total_latency_seconds"] for e in query_evaluations]

    def calc_stats(lats: List[float]) -> Dict[str, float]:
        if not lats:
            return {"min": 0.0, "median": 0.0, "p95": 0.0, "max": 0.0, "count": 0}
        s = sorted(lats)
        return {
            "min": round(s[0], 3),
            "median": round(s[len(s) // 2], 3),
            "p95": round(s[int(len(s) * 0.95)], 3),
            "max": round(s[-1], 3),
            "count": len(s)
        }

    # Aggregate accuracy metrics
    completed = [e for e in query_evaluations if not e.get("timeout") and not e.get("error")]
    correct_grounding = sum(1 for e in completed if e.get("grounding_matches_gold", False))
    grounding_acc = round(correct_grounding / len(completed), 4) if completed else 0.0

    answers_generated = sum(1 for e in completed if e.get("actual_status") == "answered")
    validation_failed_count = sum(1 for e in completed if e.get("actual_status") == "validation_failed")
    abstentions = sum(1 for e in completed if e.get("actual_status") == "insufficient_evidence")

    # Correct vs False abstentions
    correct_abstentions = sum(1 for e in completed if e.get("actual_status") == "insufficient_evidence" and not e.get("expected_answerable"))
    false_abstentions = sum(1 for e in completed if e.get("actual_status") == "insufficient_evidence" and e.get("expected_answerable"))
    unsupported_answers = sum(1 for e in completed if e.get("actual_status") == "answered" and not e.get("expected_answerable"))

    # Citation metrics
    answered_evals = [e for e in completed if e.get("actual_status") in ["answered", "validation_failed"]]
    syntax_valid_count = sum(1 for e in answered_evals if e.get("citations_summary", {}).get("citation_syntax_valid", False))
    syntax_rate = round(syntax_valid_count / len(answered_evals), 4) if answered_evals else 0.0

    overall_valid_count = sum(1 for e in answered_evals if e.get("citations_summary", {}).get("is_valid", False))
    overall_valid_rate = round(overall_valid_count / len(answered_evals), 4) if answered_evals else 0.0

    export_claim_review_artifact(all_claim_records, str(output_claims_path))
    claim_summary = summarize_claim_reviews(all_claim_records)

    report = {
        "benchmark_metadata": {
            "benchmark_name": f"NyayaVarta Milestone 6.1 Bounded Live Evaluation ({provider_type.upper()})",
            "benchmark_timestamp": datetime.now(timezone.utc).isoformat(),
            "provider_type": provider_type,
            "model_name": model_name,
            "total_queries_tested": len(dataset),
            "answerable_queries_count": sum(1 for d in dataset if d["sufficient_evidence_in_corpus"]),
            "unsupported_queries_count": sum(1 for d in dataset if not d["sufficient_evidence_in_corpus"]),
            "gate_fast_exits_count": gate_fast_exits,
            "llm_invocations_count": llm_invocations,
            "successful_generations": answers_generated,
            "validation_failed_generations": validation_failed_count,
            "correct_abstentions": correct_abstentions,
            "false_abstentions": false_abstentions,
            "unsupported_answers": unsupported_answers,
            "timeouts": timeouts_count,
            "errors": errors_count,
            "total_benchmark_duration_seconds": total_benchmark_time,
            "generation_parameters": {
                "max_passages": max_passages,
                "max_chars_per_passage": max_chars_per_passage,
                "num_predict": num_predict,
                "temperature": 0.0,
                "timeout": timeout
            }
        },
        "performance_metrics": {
            "grounding_gate_accuracy": grounding_acc,
            "citation_syntax_validity_rate": syntax_rate,
            "overall_citation_validity_rate": overall_valid_rate,
            "latency_breakdown": {
                "gate_only_fast_exit_seconds": calc_stats(gate_latencies),
                "llm_generation_seconds": calc_stats(llm_latencies),
                "total_pipeline_seconds": calc_stats(all_latencies)
            }
        },
        "claim_review_summary": claim_summary,
        "query_evaluations": query_evaluations
    }

    os.makedirs(output_report_path.parent, exist_ok=True)
    with open(output_report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 80, flush=True)
    print("MILESTONE 6.1 EVALUATION COMPLETED", flush=True)
    print(f"Total: {len(dataset)} | Answerable: {report['benchmark_metadata']['answerable_queries_count']} | Unsupported: {report['benchmark_metadata']['unsupported_queries_count']}", flush=True)
    print(f"Gate Fast-Exits: {gate_fast_exits} | LLM Invocations: {llm_invocations}", flush=True)
    print(f"Answers: {answers_generated} | Validation Failed: {validation_failed_count} | Correct Abstentions: {correct_abstentions} | Timeouts: {timeouts_count}", flush=True)
    print(f"Gate Fast-Exit Latency: median {calc_stats(gate_latencies)['median']}s | max {calc_stats(gate_latencies)['max']}s", flush=True)
    if llm_latencies:
        print(f"LLM Generation Latency: median {calc_stats(llm_latencies)['median']}s | p95 {calc_stats(llm_latencies)['p95']}s", flush=True)
    print(f"Claims Extracted: {claim_summary['total_claims']}", flush=True)
    print(f"Saved Report: {output_report_path}", flush=True)
    print(f"Saved Claims: {output_claims_path}", flush=True)
    print("=" * 80, flush=True)

    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Milestone 6.1 Evaluation Runner")
    parser.add_argument("--provider", default="ollama", choices=["ollama", "mock"], help="LLM provider")
    parser.add_argument("--model-name", default="phi3.5:latest", help="Model name")
    parser.add_argument("--query-ids", type=str, default=None, help="Comma-separated query IDs")
    parser.add_argument("--num-predict", type=int, default=160, help="Max prediction tokens")
    parser.add_argument("--max-chars", type=int, default=1000, help="Max chars per passage")
    parser.add_argument("--max-passages", type=int, default=1, help="Max passages")
    parser.add_argument("--timeout", type=float, default=240.0, help="Socket timeout")
    parser.add_argument("--output-report", default=str(OUTPUT_REPORT_PATH))
    parser.add_argument("--output-claims", default=str(OUTPUT_CLAIMS_PATH))

    args = parser.parse_args()
    qids = [x.strip() for x in args.query_ids.split(",")] if args.query_ids else None
    run_milestone6_1_eval(
        provider_type=args.provider,
        model_name=args.model_name,
        query_ids=qids,
        num_predict=args.num_predict,
        max_chars_per_passage=args.max_chars,
        max_passages=args.max_passages,
        timeout=args.timeout,
        output_report_path=Path(args.output_report),
        output_claims_path=Path(args.output_claims)
    )
