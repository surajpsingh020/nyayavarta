"""
Controlled Comparison Benchmark Runner for NyayaVarta Milestone 9:
Legal-Structure-Aware Chunking and Efficient Evidence Ranking on Local Ollama (phi3.5:latest).

Compares:
1. Configuration 1: Milestone 8 multi-passage baseline (enable_structure_aware=False, max_passages=2, max_chars_per_passage=750).
2. Configuration 2: Legal-structure-aware chunking without complementary pairing (enable_structure_aware=True, pairing=False, max_passages=2, max_chars_per_passage=750).
3. Configuration 3: Legal-structure-aware chunking with complementary issue-holding pairing & optimized context budgeting (enable_structure_aware=True, pairing=True, max_passages=2, max_chars_per_passage=550, enable_compression=True).

Preserves Milestone 7 & 8 benchmark artifacts intact.
Outputs:
- evaluation/rag/milestone9_structure_aware_comparison_report.json
- evaluation/rag/milestone9_structure_aware_claims.jsonl
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
from services.rag.evidence import EvidenceAssembler
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


def run_configuration_benchmark(
    pipeline: RAGPipeline,
    provider: Any,
    dataset: List[Dict[str, Any]],
    max_passages: int,
    max_chars_per_passage: int,
    config_name: str,
    enable_compression: bool = False,
    enable_issue_holding_pairing: bool = True
) -> Dict[str, Any]:
    print(f"\n=======================================================")
    print(f"--- Running: {config_name} ---")
    print(f"    max_passages={max_passages}, max_chars={max_chars_per_passage}, compression={enable_compression}, pairing={enable_issue_holding_pairing}")
    print(f"=======================================================")
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
    passage_chars_list = []

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
                enable_issue_holding_pairing=enable_issue_holding_pairing,
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
            else:
                abstentions_count += 1

            if val_res.invalid_source_ids:
                unknown_eids_count += len(val_res.invalid_source_ids)

            p_tokens = res.retrieval_metadata.get("llm_usage", {}).get("prompt_tokens", 0)
            e_tokens = res.retrieval_metadata.get("llm_usage", {}).get("eval_tokens", 0)
            if p_tokens:
                prompt_tokens_list.append(p_tokens)
            if e_tokens:
                eval_tokens_list.append(e_tokens)

            tot_chars = sum(len(p.passage_text) for p in res.evidence_passages)
            passage_chars_list.append(tot_chars)

            if res.claims:
                c_recs = extract_claim_review_records(
                    rag_result=res,
                    query_id=qid
                )
                claim_records.extend(c_recs)

            query_evals.append({
                "query_id": qid,
                "question": q_text,
                "expected_answerable": expected_ans,
                "status": res.status,
                "grounding_status": res.grounding_status,
                "is_fast_exit": is_fast_exit,
                "answer_text": res.answer,
                "active_evidence_passages": [
                    {
                        "evidence_id": ep.evidence_id,
                        "document_id": ep.document_id,
                        "structural_label": ep.structural_label,
                        "char_length": len(ep.passage_text),
                        "text_snippet": ep.passage_text[:120].replace("\n", " ")
                    }
                    for ep in res.evidence_passages
                ],
                "citation_validation": {
                    "is_valid": val_res.is_valid,
                    "cited_source_ids": val_res.cited_source_ids,
                    "valid_source_ids": val_res.valid_source_ids,
                    "invalid_source_ids": val_res.invalid_source_ids,
                    "unsupported_sentences": val_res.unsupported_sentences,
                    "has_invalid_citations": val_res.has_invalid_citations,
                    "validation_notes": val_res.validation_notes
                },
                "timing_ms": res.timing_ms,
                "total_latency_sec": q_latency,
                "claims_count": len(res.claims)
            })

        except TimeoutError:
            timeouts_count += 1
            print(f"   -> Timeout on {qid}")
            query_evals.append({
                "query_id": qid,
                "question": q_text,
                "status": "timeout",
                "error": "Execution timed out"
            })
        except Exception as e:
            print(f"   -> Error on {qid}: {e}")
            query_evals.append({
                "query_id": qid,
                "question": q_text,
                "status": "error",
                "error": str(e)
            })

    total_time = round(time.perf_counter() - t_start, 2)
    sorted_gen = sorted(generation_latencies)
    median_gen_latency = sorted_gen[len(sorted_gen) // 2] if sorted_gen else 0.0
    p95_gen_latency = sorted_gen[int(len(sorted_gen) * 0.95)] if sorted_gen else 0.0

    all_latencies = sorted(generation_latencies + fast_exit_latencies)
    median_e2e_latency = all_latencies[len(all_latencies) // 2] if all_latencies else 0.0
    p95_e2e_latency = all_latencies[int(len(all_latencies) * 0.95)] if all_latencies else 0.0

    avg_prompt_tokens = round(sum(prompt_tokens_list) / len(prompt_tokens_list), 1) if prompt_tokens_list else 0.0
    avg_eval_tokens = round(sum(eval_tokens_list) / len(eval_tokens_list), 1) if eval_tokens_list else 0.0
    avg_passage_chars = round(sum(passage_chars_list) / len(passage_chars_list), 1) if passage_chars_list else 0.0

    summary = {
        "config_name": config_name,
        "max_passages": max_passages,
        "max_chars_per_passage": max_chars_per_passage,
        "enable_compression": enable_compression,
        "enable_issue_holding_pairing": enable_issue_holding_pairing,
        "total_queries": len(dataset),
        "gate_fast_exits": gate_fast_exits,
        "llm_invocations": llm_invocations,
        "answers_accepted": answers_accepted,
        "abstentions_count": abstentions_count,
        "valid_structured_rate": round(valid_structured_count / len(dataset), 4) if dataset else 0.0,
        "unknown_evidence_ids_count": unknown_eids_count,
        "timeouts_count": timeouts_count,
        "median_generation_latency_sec": median_gen_latency,
        "p95_generation_latency_sec": p95_gen_latency,
        "median_e2e_latency_sec": median_e2e_latency,
        "p95_e2e_latency_sec": p95_e2e_latency,
        "avg_prompt_tokens": avg_prompt_tokens,
        "avg_eval_tokens": avg_eval_tokens,
        "avg_passage_chars": avg_passage_chars,
        "total_execution_time_sec": total_time
    }

    print(f"\n--- Summary for {config_name} ---")
    print(f"Answers: {answers_accepted}/{len(dataset)} | Fast-Exits: {gate_fast_exits} | Unknown EIDs: {unknown_eids_count}")
    print(f"Median Gen Latency: {median_gen_latency:.2f}s | Median E2E Latency: {median_e2e_latency:.2f}s")
    print(f"Avg Passage Chars: {avg_passage_chars} | Avg Prompt Tokens: {avg_prompt_tokens}")

    return {
        "summary": summary,
        "queries": query_evals,
        "claim_records": [c.model_dump() for c in claim_records]
    }


def main():
    parser = argparse.ArgumentParser(description="Milestone 9 Structure-Aware Chunking and Ranking Comparison Benchmark")
    parser.add_argument("--provider", choices=["ollama", "mock"], default="ollama", help="LLM Provider to use (default: ollama)")
    parser.add_argument("--model", default="phi3.5:latest", help="Ollama model name (default: phi3.5:latest)")
    args = parser.parse_args()

    print(f"NyayaVarta — Milestone 9 Retrieval & Ranking Comparison Benchmark")
    print(f"Provider: {args.provider} | Model: {args.model}")

    dataset = load_dataset()
    print(f"Loaded {len(dataset)} target canonical benchmark queries.")

    if args.provider == "ollama":
        provider = LocalOllamaProvider(model_name=args.model, timeout=180.0)
    else:
        provider = MockLLMProvider()

    # Configuration 1: Milestone 8 Baseline (Legacy paragraph chunker, max_passages=2, max_chars=750, no pairing)
    pipe_c1 = RAGPipeline(
        evidence_assembler=EvidenceAssembler(enable_structure_aware=False),
        llm_provider=provider
    )
    res_c1 = run_configuration_benchmark(
        pipeline=pipe_c1,
        provider=provider,
        dataset=dataset,
        max_passages=2,
        max_chars_per_passage=750,
        config_name="Config 1: Milestone 8 Baseline (Legacy Chunking, k=2, max 750 chars)",
        enable_compression=False,
        enable_issue_holding_pairing=False
    )

    # Configuration 2: Legal-Structure-Aware Chunking without Complementary Pairing
    pipe_c2 = RAGPipeline(
        evidence_assembler=EvidenceAssembler(enable_structure_aware=True),
        llm_provider=provider
    )
    res_c2 = run_configuration_benchmark(
        pipeline=pipe_c2,
        provider=provider,
        dataset=dataset,
        max_passages=2,
        max_chars_per_passage=750,
        config_name="Config 2: Structure-Aware Chunking (No Pairing, k=2, max 750 chars)",
        enable_compression=False,
        enable_issue_holding_pairing=False
    )

    # Configuration 3: Legal-Structure-Aware Chunking with Complementary Issue-Holding Pairing & Optimized Context Budgeting
    pipe_c3 = RAGPipeline(
        evidence_assembler=EvidenceAssembler(enable_structure_aware=True),
        llm_provider=provider
    )
    res_c3 = run_configuration_benchmark(
        pipeline=pipe_c3,
        provider=provider,
        dataset=dataset,
        max_passages=2,
        max_chars_per_passage=550,
        config_name="Config 3: Structure-Aware + Issue-Holding Pairing + Budget Optimization (k=2, max 550 chars, compression=True)",
        enable_compression=True,
        enable_issue_holding_pairing=True
    )

    # Compile Final Report
    report = {
        "metadata": {
            "milestone": "Milestone 9",
            "benchmark": "10-Query Canonical Comparison",
            "provider": args.provider,
            "model_name": args.model if args.provider == "ollama" else "mock",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "target_query_ids": TARGET_QUERY_IDS
        },
        "comparison_table": {
            "config_1_m8_baseline": res_c1["summary"],
            "config_2_structure_aware_no_pairing": res_c2["summary"],
            "config_3_structure_aware_paired_optimized": res_c3["summary"]
        },
        "query_results": {
            "config_1": res_c1["queries"],
            "config_2": res_c2["queries"],
            "config_3": res_c3["queries"]
        }
    }

    report_path = "evaluation/rag/milestone9_structure_aware_comparison_report.json"
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"\n[OK] Comparison report saved to {report_path}")

    # Write Claims JSONL for Config 3
    claims_path = "evaluation/rag/milestone9_structure_aware_claims.jsonl"
    with open(claims_path, "w", encoding="utf-8") as f:
        for rec in res_c3["claim_records"]:
            f.write(json.dumps(rec) + "\n")
    print(f"[OK] {len(res_c3['claim_records'])} claim review records saved to {claims_path}")


if __name__ == "__main__":
    main()
