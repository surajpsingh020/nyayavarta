"""
Controlled Comparison Benchmark Runner for NyayaVarta Milestone 8:
Multi-Passage Evidence Selection and Context Budgeting on Local Ollama (phi3.5:latest).

Compares:
1. Single-Passage Baseline (Milestone 7): max_passages=1, max_chars_per_passage=1000.
2. Two-Passage Selection (Milestone 8 Config 2): max_passages=2, max_chars_per_passage=750.
3. Three-Passage Selection (Milestone 8 Config 3): max_passages=3, max_chars_per_passage=500.

Preserves Milestone 7 benchmark artifacts intact.
Outputs:
- evaluation/rag/milestone8_multipassage_comparison_report.json
- evaluation/rag/milestone8_multipassage_claims.jsonl
"""
import os
import sys
import time
import json
import argparse
from typing import List, Dict, Any, Optional

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


def load_milestone7_baseline(baseline_path: str = "evaluation/rag/milestone7_structured_comparison_report.json") -> Optional[Dict[str, Any]]:
    if not os.path.exists(baseline_path):
        return None
    with open(baseline_path, "r", encoding="utf-8") as f:
        return json.load(f)


def run_configuration_benchmark(
    pipeline: RAGPipeline,
    provider: Any,
    dataset: List[Dict[str, Any]],
    max_passages: int,
    max_chars_per_passage: int,
    config_name: str,
    enable_compression: bool = False
) -> Dict[str, Any]:
    print(f"\n--- Running Configuration: {config_name} (max_passages={max_passages}, max_chars={max_chars_per_passage}) ---")
    t_start = time.perf_counter()
    query_evals: List[Dict[str, Any]] = []
    claim_records: List[ClaimReviewRecord] = []

    gate_fast_exits = 0
    llm_invocations = 0
    valid_structured_count = 0
    answers_accepted = 0
    abstentions_count = 0
    unknown_eids_count = 0
    timeouts_count = 0

    generation_latencies = []
    fast_exit_latencies = []
    prompt_tokens_list = []
    eval_tokens_list = []

    for idx, item in enumerate(dataset, 1):
        qid = item["query_id"]
        q_text = item.get("question") or item.get("query", "")
        expected_ans = item.get("sufficient_evidence_in_corpus", item.get("is_answerable", True))
        print(f"[{idx}/{len(dataset)}] Evaluating {qid} (Expected: {'Answer' if expected_ans else 'Abstain'})...")

        t_q = time.perf_counter()
        try:
            res: RAGResult = pipeline.query(
                query_text=q_text,
                top_k_judgments=3,
                max_passages=max_passages,
                max_chars_per_passage=max_chars_per_passage,
                enable_compression=enable_compression,
                structured_output=True,
                provider=provider
            )
            q_latency = round(time.perf_counter() - t_q, 3)
            is_fast_exit = (res.timing_ms.get("generation_ms") is None or res.timing_ms.get("generation_ms", 0) == 0)

            if is_fast_exit:
                gate_fast_exits += 1
                fast_exit_latencies.append(q_latency)
                print(f"   -> Fast-Exit Abstention in {q_latency:.3f}s: {res.answer[:80]}...")
            else:
                llm_invocations += 1
                gen_sec = round(res.timing_ms.get("generation_ms", 0) / 1000.0, 3)
                generation_latencies.append(gen_sec)
                print(f"   -> LLM Invoked in {gen_sec:.2f}s (Total: {q_latency:.2f}s). Status: {res.status}")

            val_res = res.citation_validation
            is_valid_structured = val_res.is_valid and val_res.citation_syntax_valid

            if is_valid_structured:
                valid_structured_count += 1
            if res.status == "answered":
                answers_accepted += 1
            elif res.status in ["insufficient_evidence", "abstain"]:
                abstentions_count += 1

            if len(val_res.invalid_source_ids) > 0:
                unknown_eids_count += len(val_res.invalid_source_ids)

            llm_usage = res.retrieval_metadata.get("llm_usage", {})
            if llm_usage.get("prompt_eval_count"):
                prompt_tokens_list.append(llm_usage["prompt_eval_count"])
            if llm_usage.get("eval_count"):
                eval_tokens_list.append(llm_usage["eval_count"])

            q_eval_dict = {
                "query_id": qid,
                "category": item.get("category", ""),
                "legal_domain": item.get("legal_domain", ""),
                "query": q_text,
                "expected_answerable": expected_ans,
                "actual_status": res.status,
                "grounding_status": res.grounding_status,
                "gate_only_fast_exit": is_fast_exit,
                "grounding_matches_gold": (res.status == "answered" if expected_ans else res.status in ["insufficient_evidence", "abstain"]),
                "timing_ms": res.timing_ms,
                "total_latency_seconds": q_latency,
                "num_evidence_passages": len(res.evidence_passages),
                "active_evidence_ids": [ep.evidence_id for ep in res.evidence_passages],
                "structured_answer": res.structured_answer.model_dump() if res.structured_answer else None,
                "citations_summary": {
                    "is_valid": val_res.is_valid,
                    "validation_status": val_res.validation_status,
                    "citation_syntax_valid": val_res.citation_syntax_valid,
                    "citation_existence_valid": val_res.citation_existence_valid,
                    "attribution_complete": val_res.attribution_complete,
                    "semantic_support_status": val_res.semantic_support_status,
                    "cited_ids": val_res.cited_source_ids,
                    "valid_ids": val_res.valid_source_ids,
                    "invalid_ids": val_res.invalid_source_ids,
                    "unsupported_sentences": val_res.unsupported_sentences,
                    "validation_notes": val_res.validation_notes
                },
                "llm_usage": llm_usage,
                "answer_text": res.answer,
                "claims_count": len(res.claims) if res.claims else 0,
                "timeout": False,
                "error": None
            }
            query_evals.append(q_eval_dict)

            # Extract claim records for audit logging
            c_recs = extract_claim_review_records(
                rag_result=res,
                query_id=qid
            )
            claim_records.extend(c_recs)

        except Exception as e:
            q_latency = round(time.perf_counter() - t_q, 3)
            print(f"   -> ERROR / TIMEOUT on {qid} after {q_latency:.2f}s: {e}")
            timeouts_count += 1
            query_evals.append({
                "query_id": qid,
                "category": item.get("category", ""),
                "legal_domain": item.get("legal_domain", ""),
                "query": q_text,
                "expected_answerable": expected_ans,
                "actual_status": "error",
                "grounding_status": "error",
                "gate_only_fast_exit": False,
                "grounding_matches_gold": False,
                "timing_ms": {},
                "total_latency_seconds": q_latency,
                "num_evidence_passages": 0,
                "active_evidence_ids": [],
                "structured_answer": None,
                "citations_summary": {
                    "is_valid": False,
                    "validation_status": "error",
                    "invalid_ids": [],
                    "validation_notes": [str(e)]
                },
                "llm_usage": {},
                "answer_text": f"ERROR: {str(e)}",
                "claims_count": 0,
                "timeout": isinstance(e, TimeoutError),
                "error": str(e)
            })

    total_duration = round(time.perf_counter() - t_start, 2)

    def _median(lst):
        if not lst: return 0.0
        s = sorted(lst)
        n = len(s)
        return round(s[n//2] if n % 2 != 0 else (s[n//2 - 1] + s[n//2]) / 2.0, 3)

    def _p95(lst):
        if not lst: return 0.0
        s = sorted(lst)
        idx = int(0.95 * len(s))
        return round(s[min(idx, len(s) - 1)], 3)

    return {
        "config_name": config_name,
        "max_passages": max_passages,
        "max_chars_per_passage": max_chars_per_passage,
        "total_duration_seconds": total_duration,
        "metrics": {
            "queries_completed": len(dataset),
            "gate_fast_exits": gate_fast_exits,
            "llm_invocations": llm_invocations,
            "valid_structured_output_rate": round(valid_structured_count / len(dataset), 3) if dataset else 0.0,
            "unknown_evidence_ids_count": unknown_eids_count,
            "unknown_evidence_ids_rate": round(unknown_eids_count / max(1, valid_structured_count), 3),
            "answers_accepted": answers_accepted,
            "abstentions_count": abstentions_count,
            "timeouts_count": timeouts_count,
            "generation_latency_median_seconds": _median(generation_latencies),
            "generation_latency_p95_seconds": _p95(generation_latencies),
            "fast_exit_median_seconds": _median(fast_exit_latencies),
            "fast_exit_p95_seconds": _p95(fast_exit_latencies),
            "prompt_tokens_median": _median(prompt_tokens_list),
            "prompt_tokens_p95": _p95(prompt_tokens_list),
            "eval_tokens_median": _median(eval_tokens_list),
            "eval_tokens_p95": _p95(eval_tokens_list)
        },
        "query_evaluations": query_evals,
        "claim_records": claim_records
    }


def main():
    parser = argparse.ArgumentParser(description="NyayaVarta Milestone 8 Multi-Passage Benchmark Runner")
    parser.add_argument("--config", default="all", choices=["all", "two_passages", "three_passages"], help="Which configuration(s) to benchmark")
    parser.add_argument("--provider", default="ollama", choices=["ollama", "mock"], help="LLM provider type")
    parser.add_argument("--model", default="phi3.5:latest", help="Ollama model name")
    parser.add_argument("--timeout", type=float, default=240.0, help="Per-query timeout in seconds")
    parser.add_argument("--num-predict", type=int, default=140, help="Maximum generated tokens")
    args = parser.parse_args()

    dataset = load_dataset()
    m7_baseline = load_milestone7_baseline()

    out_report_path = "evaluation/rag/milestone8_multipassage_comparison_report.json"
    out_claims_path = "evaluation/rag/milestone8_multipassage_claims.jsonl"

    # Load existing report if available to allow merging/updating configs
    existing_report = {}
    if os.path.exists(out_report_path):
        try:
            with open(out_report_path, "r", encoding="utf-8") as f:
                existing_report = json.load(f)
        except Exception:
            existing_report = {}

    if args.provider.lower() == "ollama":
        avail = LocalOllamaProvider.check_availability(model_name=args.model)
        if not avail["available"]:
            raise RuntimeError(f"Ollama daemon unreachable: {avail['error']}")
        provider = LocalOllamaProvider(
            model_name=args.model,
            timeout=args.timeout,
            default_options={
                "num_ctx": 2048,
                "num_predict": args.num_predict,
                "temperature": 0.0,
                "num_thread": 8
            }
        )
    else:
        provider = MockLLMProvider()

    pipeline = RAGPipeline()

    m7_metrics = {}
    if m7_baseline and "side_by_side_comparison" in m7_baseline:
        m7_metrics = m7_baseline["side_by_side_comparison"].get("milestone_7_structured", {})

    report = {
        "benchmark_metadata": {
            "benchmark_name": "NyayaVarta Milestone 8 Multi-Passage Evidence Selection Benchmark",
            "benchmark_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "provider_type": args.provider,
            "model_name": args.model,
            "queries_tested": len(dataset),
            "epistemic_status": "developer_curated (no independent legal practitioner review)",
            "configurations_evaluated": [
                {"name": "milestone_7_baseline", "max_passages": 1, "max_chars_per_passage": 1000},
                {"name": "milestone_8_two_passages", "max_passages": 2, "max_chars_per_passage": 750},
                {"name": "milestone_8_three_passages", "max_passages": 3, "max_chars_per_passage": 500}
            ]
        },
        "side_by_side_comparison": {
            "milestone_7_single_passage_baseline": m7_metrics,
            "milestone_8_two_passages": existing_report.get("side_by_side_comparison", {}).get("milestone_8_two_passages", {}),
            "milestone_8_three_passages": existing_report.get("side_by_side_comparison", {}).get("milestone_8_three_passages", {})
        },
        "query_evaluations_two_passages": existing_report.get("query_evaluations_two_passages", []),
        "query_evaluations_three_passages": existing_report.get("query_evaluations_three_passages", [])
    }

    all_claim_records = []

    # 1. Config 2: 2 Passages (budgeted at 750 chars per passage)
    if args.config in ["all", "two_passages"]:
        res_cfg2 = run_configuration_benchmark(
            pipeline=pipeline,
            provider=provider,
            dataset=dataset,
            max_passages=2,
            max_chars_per_passage=750,
            config_name="milestone8_two_passages",
            enable_compression=False
        )
        report["side_by_side_comparison"]["milestone_8_two_passages"] = res_cfg2["metrics"]
        report["query_evaluations_two_passages"] = res_cfg2["query_evaluations"]
        all_claim_records.extend(res_cfg2["claim_records"])

        with open(out_report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        print(f"[Checkpointed] Report updated with Config 2: {out_report_path}")

    # 2. Config 3: 3 Passages (budgeted at 500 chars per passage)
    if args.config in ["all", "three_passages"]:
        res_cfg3 = run_configuration_benchmark(
            pipeline=pipeline,
            provider=provider,
            dataset=dataset,
            max_passages=3,
            max_chars_per_passage=500,
            config_name="milestone8_three_passages",
            enable_compression=False
        )
        report["side_by_side_comparison"]["milestone_8_three_passages"] = res_cfg3["metrics"]
        report["query_evaluations_three_passages"] = res_cfg3["query_evaluations"]
        all_claim_records.extend(res_cfg3["claim_records"])

        with open(out_report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        print(f"[Checkpointed] Report updated with Config 3: {out_report_path}")

    # Write claim review records to JSONL
    if all_claim_records:
        with open(out_claims_path, "w", encoding="utf-8") as f:
            for cr in all_claim_records:
                f.write(json.dumps(cr.model_dump(), ensure_ascii=False) + "\n")
        print(f"[Saved] Claim Review JSONL: {out_claims_path} ({len(all_claim_records)} records)")


if __name__ == "__main__":
    main()
