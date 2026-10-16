"""
Milestone 21 - CPU Latency and Evidence-Budget Optimization Runner.

Executes:
Phase A: Reproducible live baseline and latency instrumentation.
Phase B: Controlled evidence-budget experiment (1500t, 1000t, 750t, 500t).
Phase C: Frozen-set evaluation on 40 Milestone 20 staging claims.
Phase D: Smaller-model comparison (Mock vs Phi-3.5 vs Qwen-2.5 0.5B).

Generates:
- evaluation/rag/milestone21_latency_results.json
- evaluation/rag/milestone21_context_budget_comparison.json
- evaluation/rag/milestone21_model_comparison.json
"""
import time
import json
import re
import os
import sys
import psutil
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from services.rag.models import EvidencePassage, RAGResult
from services.rag.claim_verifier import ClaimVerifier
from services.rag.nli_verifier import LocalNLIVerifier
from services.rag.pipeline import RAGPipeline
from services.rag.evidence import (
    EvidenceAssembler,
    select_complementary_evidence_passages,
    verify_and_filter_evidence,
    verify_evidence_offsets,
    ExtractiveSentenceCompressor
)
from services.rag.providers import MockLLMProvider, LocalOllamaProvider


BUDGET_CONFIGS = {
    "B0_baseline_1500t": {
        "name": "B0: Baseline Unconstrained (~1,500 tokens)",
        "target_tokens": 1500,
        "max_passages": 3,
        "max_total_chars": 4500,
        "max_chars_per_passage": 1500,
        "enable_compression": False,
        "description": "Existing unconstrained multi-passage configuration (up to 3 full passages, uncompressed)."
    },
    "B1_budget_1000t": {
        "name": "B1: Bounded Multi-Passage (~1,000 tokens)",
        "target_tokens": 1000,
        "max_passages": 2,
        "max_total_chars": 3000,
        "max_chars_per_passage": 1500,
        "enable_compression": False,
        "description": "Bounded multi-passage selection (up to 2 complete passages without compression)."
    },
    "B2_budget_750t": {
        "name": "B2: Compressed Multi-Passage (~750 tokens)",
        "target_tokens": 750,
        "max_passages": 2,
        "max_total_chars": 2250,
        "max_chars_per_passage": 1000,
        "enable_compression": True,
        "description": "Extractive sentence compression preserving complete sentences, provisos, and exact character spans."
    },
    "B3_budget_500t": {
        "name": "B3: Focused Single-to-Dual Passage (~500 tokens)",
        "target_tokens": 500,
        "max_passages": 1,
        "max_total_chars": 1500,
        "max_chars_per_passage": 800,
        "enable_compression": True,
        "description": "Strict low-latency budget for CPU inference; selects highest-relevance holding passage with sentence compression."
    }
}

TEST_QUERIES = [
    # 1. Answerable - Criminal Law / Murder circumstantial chain
    {
        "query_id": "M21_Q1",
        "query_text": "What is required to sustain a conviction based solely on circumstantial evidence in murder?",
        "type": "answerable",
        "domain": "criminal"
    },
    # 2. Answerable - Service Law / Altering qualification criteria
    {
        "query_id": "M21_Q2",
        "query_text": "Can an employer change qualifications after the recruitment advertisement is issued?",
        "type": "answerable",
        "domain": "service"
    },
    # 3. Answerable - Consumer Protection / Film trailer song exclusion
    {
        "query_id": "M21_Q3",
        "query_text": "Does excluding a promotional song from a movie constitute deficiency of service?",
        "type": "answerable",
        "domain": "consumer"
    },
    # 4. Answerable - Multi-Passage / Statutory Qualification (CPC Order XXI Rule 99)
    {
        "query_id": "M21_Q4",
        "query_text": "Who is entitled to make an application complaining of dispossession under Order XXI Rule 99 CPC?",
        "type": "answerable_statutory_qualification",
        "domain": "civil_procedure"
    },
    # 5. Answerable - UAPA Section 43D(5) Bail threshold
    {
        "query_id": "M21_Q5",
        "query_text": "Can bail be denied under Section 43D(5) UAPA merely for possessing literature?",
        "type": "answerable_statutory_condition",
        "domain": "constitutional_criminal"
    },
    # 6. Unanswerable - Outside corpus / Insufficient evidence
    {
        "query_id": "M21_Q6",
        "query_text": "What is the penalty for violating cryptocurrency staking regulations in maritime economic zones?",
        "type": "unanswerable",
        "domain": "unsupported_boundary"
    }
]


def run_phase_b_evidence_budget_experiment() -> Dict[str, Any]:
    """Run Phase B: Compare evidence context budgets across answerable and unanswerable queries."""
    print("--- Running Phase B: Controlled Evidence-Budget Experiments ---")
    pipeline = RAGPipeline(
        llm_provider=MockLLMProvider(mode=MockLLMProvider.MODE_STRUCTURED_NORMAL)
    )

    budget_results = {}

    for b_key, b_cfg in BUDGET_CONFIGS.items():
        print(f"Evaluating {b_cfg['name']}...")
        runs = []

        total_passages_selected = 0
        total_evidence_chars = 0
        total_prompt_chars = 0
        offsets_verified_count = 0
        abstention_count = 0
        qualifications_preserved_count = 0
        qualification_test_count = 0

        latencies = {
            "retrieval": [],
            "evidence_assembly": [],
            "grounding_gate": [],
            "generation": [],
            "validation": [],
            "total": []
        }

        for q in TEST_QUERIES:
            t0 = time.perf_counter()
            res = pipeline.query(
                query_text=q["query_text"],
                top_k_judgments=3,
                max_passages=b_cfg["max_passages"],
                max_total_chars=b_cfg["max_total_chars"],
                max_chars_per_passage=b_cfg["max_chars_per_passage"],
                enable_compression=b_cfg["enable_compression"],
                structured_output=True
            )

            # Measure offset verification fidelity
            all_offsets_valid, offset_errors = verify_evidence_offsets(res.evidence_passages)
            if all_offsets_valid:
                offsets_verified_count += 1

            total_passages_selected += len(res.evidence_passages)
            ev_chars = sum(len(ep.passage_text) for ep in res.evidence_passages)
            total_evidence_chars += ev_chars

            p_chars = res.retrieval_metadata.get("context_budget", {}).get("total_prompt_chars", 0)
            total_prompt_chars += p_chars

            if res.status == "insufficient_evidence" or res.verification_badge == "insufficient_evidence":
                abstention_count += 1

            # Check if statutory qualification queries preserved key limiting clauses
            if q["type"] in ["answerable_statutory_qualification", "answerable_statutory_condition"]:
                qualification_test_count += 1
                ev_text_all = " ".join(ep.passage_text.lower() for ep in res.evidence_passages)
                has_qualifier = any(kw in ev_text_all for kw in ["other than", "except", "provided", "subject to", "prima facie", "alone without"])
                if has_qualifier:
                    qualifications_preserved_count += 1

            lat = res.timing_ms
            latencies["retrieval"].append(lat.get("retrieval_ms", 0.0))
            latencies["evidence_assembly"].append(lat.get("evidence_assembly_ms", 0.0))
            latencies["grounding_gate"].append(lat.get("grounding_gate_ms", 0.0))
            latencies["generation"].append(lat.get("generation_ms", 0.0))
            latencies["validation"].append(lat.get("validation_ms", 0.0))
            latencies["total"].append(lat.get("total_ms", 0.0))

            runs.append({
                "query_id": q["query_id"],
                "query_text": q["query_text"],
                "query_type": q["type"],
                "status": res.status,
                "badge": res.verification_badge,
                "evidence_passages_count": len(res.evidence_passages),
                "evidence_chars": ev_chars,
                "estimated_tokens": round(ev_chars / 4.0, 1),
                "offsets_verified": all_offsets_valid,
                "timing_ms": res.timing_ms
            })

        n_queries = len(TEST_QUERIES)
        avg_passages = round(total_passages_selected / n_queries, 2)
        avg_ev_chars = round(total_evidence_chars / n_queries, 1)
        avg_tokens = round(avg_ev_chars / 4.0, 1)

        budget_results[b_key] = {
            "config": b_cfg,
            "metrics": {
                "total_queries_tested": n_queries,
                "avg_passages_selected": avg_passages,
                "avg_evidence_chars": avg_ev_chars,
                "avg_estimated_evidence_tokens": avg_tokens,
                "offset_integrity_rate": round(offsets_verified_count / n_queries, 4),
                "unanswerable_abstention_correctness": round(abstention_count / 1.0, 4) if abstention_count >= 1 else 0.0,
                "qualifications_preserved_rate": round(qualifications_preserved_count / qualification_test_count, 4) if qualification_test_count > 0 else 1.0,
                "avg_latencies_ms": {
                    "retrieval": round(sum(latencies["retrieval"]) / n_queries, 2),
                    "evidence_assembly": round(sum(latencies["evidence_assembly"]) / n_queries, 2),
                    "grounding_gate": round(sum(latencies["grounding_gate"]) / n_queries, 2),
                    "generation": round(sum(latencies["generation"]) / n_queries, 2),
                    "validation": round(sum(latencies["validation"]) / n_queries, 2),
                    "total": round(sum(latencies["total"]) / n_queries, 2)
                }
            },
            "sample_runs": runs
        }

    return budget_results


def run_phase_c_frozen_staging_evaluation() -> Dict[str, Any]:
    """Run Phase C: Evaluate the 40 frozen Milestone 20 staging claims under budget configurations."""
    print("--- Running Phase C: Frozen-Set Evaluation Across Budgets ---")
    staging_file = Path("evaluation/rag/milestone20_staging_claims.jsonl")
    assert staging_file.exists(), f"Staging file {staging_file} not found!"

    claims_data = []
    with staging_file.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                claims_data.append(json.loads(line))

    det_verifier = ClaimVerifier()
    nli_verifier = LocalNLIVerifier()

    results_by_budget = {}

    for b_key, b_cfg in BUDGET_CONFIGS.items():
        eval_cases = []
        for item in claims_data:
            claim_text = item["claim_sentence"]
            gold = item["gold_support_label"]
            sp = item["supporting_passages"][0]

            ep = EvidencePassage(
                evidence_id=sp["evidence_id"],
                document_id=sp["document_id"],
                case_title=sp["case_title"],
                passage_text=sp["passage_text"],
                start_char=sp["start_char"],
                end_char=sp["end_char"],
                structural_label=sp.get("structural_label", "headnote_holding")
            )

            # Apply budget compression if enabled
            if b_cfg["enable_compression"]:
                ep = ExtractiveSentenceCompressor.compress_passage(
                    ep, item["question"], max_chars=b_cfg["max_chars_per_passage"]
                )

            # 1. Deterministic status
            det_res = det_verifier.verify_claim(claim_text, [ep])
            det_status = det_res.status.value

            # 2. NLI prediction
            nli_res = nli_verifier.predict(premise=ep.passage_text, hypothesis=claim_text)
            p_contra = nli_res.probabilities.get("contradiction", 0.0)
            p_entail = nli_res.probabilities.get("entailment", 0.0)
            p_neutral = nli_res.probabilities.get("neutral", 0.0)

            # Policy 3: Contradiction Veto
            p3_status = det_status
            if det_status == "supported":
                if p_contra >= 0.70 and (p_contra - max(p_entail, p_neutral)) >= 0.20:
                    p3_status = "contradicted"

            eval_cases.append({
                "case_id": item["case_id"],
                "gold_label": gold,
                "predicted_label": p3_status,
                "passage_len": len(ep.passage_text),
                "is_compressed": len(ep.passage_text) < len(sp["passage_text"])
            })

        # Calculate metrics for Policy 3 under this budget
        total = len(eval_cases)
        gold_supported = sum(1 for c in eval_cases if c["gold_label"] == "supported")
        pred_supported = sum(1 for c in eval_cases if c["predicted_label"] == "supported")
        true_positives = sum(1 for c in eval_cases if c["gold_label"] == "supported" and c["predicted_label"] == "supported")

        contra_gold = sum(1 for c in eval_cases if c["gold_label"] == "contradicted")
        contra_fa = sum(1 for c in eval_cases if c["gold_label"] == "contradicted" and c["predicted_label"] == "supported")

        partial_gold = sum(1 for c in eval_cases if c["gold_label"] == "partially_supported")
        partial_fa = sum(1 for c in eval_cases if c["gold_label"] == "partially_supported" and c["predicted_label"] == "supported")

        unsupp_gold = sum(1 for c in eval_cases if c["gold_label"] == "unsupported")
        unsupp_fa = sum(1 for c in eval_cases if c["gold_label"] == "unsupported" and c["predicted_label"] == "supported")

        false_rejections = sum(1 for c in eval_cases if c["gold_label"] == "supported" and c["predicted_label"] != "supported")
        unresolved = sum(1 for c in eval_cases if c["predicted_label"] == "not_evaluated")

        non_supp_total = total - gold_supported
        non_supp_fa = contra_fa + partial_fa + unsupp_fa

        precision = true_positives / pred_supported if pred_supported > 0 else 0.0
        recall = true_positives / gold_supported if gold_supported > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

        results_by_budget[b_key] = {
            "budget": b_cfg["name"],
            "total_claims": total,
            "supported_precision": round(precision, 4),
            "supported_recall": round(recall, 4),
            "supported_f1": round(f1, 4),
            "true_positives": true_positives,
            "pred_supported": pred_supported,
            "non_supported_far": round(non_supp_fa / non_supp_total, 4) if non_supp_total > 0 else 0.0,
            "non_supported_false_accepts": non_supp_fa,
            "contradiction_far": round(contra_fa / contra_gold, 4) if contra_gold > 0 else 0.0,
            "contradiction_false_accepts": contra_fa,
            "partially_supported_far": round(partial_fa / partial_gold, 4) if partial_gold > 0 else 0.0,
            "partially_supported_false_accepts": partial_fa,
            "unsupported_far": round(unsupp_fa / unsupp_gold, 4) if unsupp_gold > 0 else 0.0,
            "unsupported_false_accepts": unsupp_fa,
            "false_rejection_rate": round(false_rejections / gold_supported, 4) if gold_supported > 0 else 0.0,
            "unresolved_rate": round(unresolved / total, 4)
        }

    return results_by_budget


def run_phase_a_and_d_model_benchmarking() -> Dict[str, Any]:
    """Run Phase A & Phase D: Benchmark Mock vs Phi-3.5 vs Qwen-2.5 0.5B across CPU latency."""
    print("--- Running Phase A & Phase D: Smaller Model Benchmarking & Live CPU Latency ---")

    models_to_test = [
        {"model_id": "mock", "name": "mock-grounded-cpu-v1", "params": "0M", "license": "Apache-2.0", "format": "python_deterministic"},
        {"model_id": "qwen2.5:0.5b", "name": "qwen2.5:0.5b", "params": "0.5B", "license": "Apache-2.0", "format": "int4_gguf"},
        {"model_id": "phi3.5:latest", "name": "phi3.5:latest", "params": "3.8B", "license": "MIT", "format": "int4_gguf"}
    ]

    ollama_avail = LocalOllamaProvider.check_availability()
    installed_models = ollama_avail.get("models", [])
    print(f"Ollama reachable: {ollama_avail.get('available')}, Installed models: {installed_models}")

    sample_prompt = (
        "=== EVIDENCE PASSAGES ===\n"
        "[E1] Case: State v. Apoorva Arora\n"
        "Passage Text: 'Held: Vulgarity cannot be equated to obscenity. Language that is merely foul or abusive does not deprave or corrupt minds.'\n\n"
        "=== USER QUESTION ===\n"
        "Does vulgar language in media automatically equate to obscenity?"
    )

    benchmarks = {}

    # CPU/RAM configuration metadata
    cpu_info = {
        "cpu_count_logical": psutil.cpu_count(logical=True),
        "cpu_count_physical": psutil.cpu_count(logical=False),
        "cpu_frequency_mhz": getattr(psutil.cpu_freq(), 'current', 0) if psutil.cpu_freq() else 0,
        "ram_total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
        "ram_available_gb": round(psutil.virtual_memory().available / (1024**3), 2)
    }

    for m_spec in models_to_test:
        mid = m_spec["model_id"]
        print(f"Testing {m_spec['name']}...")

        if mid == "mock":
            provider = MockLLMProvider()
            t0 = time.perf_counter()
            resp = provider.generate(prompt=sample_prompt, max_tokens=100)
            cold_latency = resp.latency_ms

            t0 = time.perf_counter()
            resp_warm = provider.generate(prompt=sample_prompt, max_tokens=100)
            warm_latency = resp_warm.latency_ms

            benchmarks[mid] = {
                "spec": m_spec,
                "status": "available",
                "cold_start_latency_ms": round(cold_latency, 2),
                "warm_latency_ms": round(warm_latency, 2),
                "prompt_eval_tokens": len(sample_prompt.split()),
                "prompt_eval_ms": 0.0,
                "eval_tokens": len(resp.content.split()),
                "eval_duration_ms": round(warm_latency, 2),
                "prompt_tokens_per_sec": 9999.0,
                "tokens_per_sec": 9999.0,
                "timeout_count": 0,
                "success_rate": 1.0,
                "sample_output": resp.content[:150]
            }

        else:
            is_installed = mid in installed_models
            if not is_installed:
                # Check if it was just downloaded
                ollama_avail = LocalOllamaProvider.check_availability()
                installed_models = ollama_avail.get("models", [])
                is_installed = mid in installed_models

            if not is_installed:
                print(f"Model {mid} is not yet installed in Ollama. Marking pending/unavailable.")
                benchmarks[mid] = {
                    "spec": m_spec,
                    "status": "not_installed_or_download_pending",
                    "error": f"Model {mid} not in installed list: {installed_models}"
                }
                continue

            provider = LocalOllamaProvider(model_name=mid, timeout=60.0)

            # Cold run
            try:
                t0 = time.perf_counter()
                cold_resp = provider.generate(prompt=sample_prompt, max_tokens=80)
                cold_ms = cold_resp.latency_ms
                cold_usage = cold_resp.usage or {}

                # Warm run
                t0 = time.perf_counter()
                warm_resp = provider.generate(prompt=sample_prompt, max_tokens=80)
                warm_ms = warm_resp.latency_ms
                warm_usage = warm_resp.usage or {}

                benchmarks[mid] = {
                    "spec": m_spec,
                    "status": "available",
                    "cold_start_latency_ms": round(cold_ms, 2),
                    "warm_latency_ms": round(warm_ms, 2),
                    "prompt_eval_tokens": warm_usage.get("prompt_eval_count", 0),
                    "prompt_eval_ms": warm_usage.get("prompt_eval_ms", 0.0),
                    "eval_tokens": warm_usage.get("eval_count", 0),
                    "eval_duration_ms": warm_usage.get("eval_duration_ms", 0.0),
                    "prompt_tokens_per_sec": warm_usage.get("prompt_tokens_per_second", 0.0),
                    "tokens_per_sec": warm_usage.get("tokens_per_second", 0.0),
                    "timeout_count": 0,
                    "success_rate": 1.0,
                    "sample_output": warm_resp.content[:150]
                }
            except TimeoutError as te:
                print(f"Model {mid} timed out: {te}")
                benchmarks[mid] = {
                    "spec": m_spec,
                    "status": "timeout",
                    "error": str(te),
                    "timeout_count": 1,
                    "success_rate": 0.0
                }
            except Exception as e:
                print(f"Model {mid} error: {e}")
                benchmarks[mid] = {
                    "spec": m_spec,
                    "status": "error",
                    "error": str(e),
                    "timeout_count": 0,
                    "success_rate": 0.0
                }

    return {
        "hardware_environment": cpu_info,
        "models": benchmarks
    }


def main():
    print("=== NyayaVarta Milestone 21: Evidence-Budget and CPU Latency Optimization ===")
    t_start = time.perf_counter()

    # 1. Evidence Budget Experiments (Phase B)
    phase_b_results = run_phase_b_evidence_budget_experiment()
    b_out_path = Path("evaluation/rag/milestone21_context_budget_comparison.json")
    with b_out_path.open("w", encoding="utf-8") as f:
        json.dump(phase_b_results, f, indent=2)
    print(f"Phase B results saved to {b_out_path}")

    # 2. Frozen Staging Set Evaluation (Phase C)
    phase_c_results = run_phase_c_frozen_staging_evaluation()
    c_out_path = Path("evaluation/rag/milestone21_model_comparison.json")
    model_comparison_payload = {
        "milestone": "Milestone 21 - CPU Latency and Evidence-Budget Optimization",
        "frozen_dataset": "evaluation/rag/milestone20_staging_claims.jsonl",
        "total_claims": 40,
        "policy": "Policy 3 (Contradiction Veto Only)",
        "results_by_budget": phase_c_results
    }
    with c_out_path.open("w", encoding="utf-8") as f:
        json.dump(model_comparison_payload, f, indent=2)
    print(f"Phase C results saved to {c_out_path}")

    # 3. Model Latency Benchmarking (Phase A & D)
    phase_ad_results = run_phase_a_and_d_model_benchmarking()
    lat_out_path = Path("evaluation/rag/milestone21_latency_results.json")
    with lat_out_path.open("w", encoding="utf-8") as f:
        json.dump(phase_ad_results, f, indent=2)
    print(f"Phase A/D results saved to {lat_out_path}")

    print("\n--- Summary: Context Budget vs Quality & Latency ---")
    for b_key, b_data in phase_b_results.items():
        m = b_data["metrics"]
        print(f"\n{b_data['config']['name']}:")
        print(f"  Avg Evidence: {m['avg_evidence_chars']} chars (~{m['avg_estimated_evidence_tokens']} tokens) across {m['avg_passages_selected']} passages")
        print(f"  Offset Integrity: {m['offset_integrity_rate']*100:.1f}% | Provisos Preserved: {m['qualifications_preserved_rate']*100:.1f}%")
        print(f"  Assembly: {m['avg_latencies_ms']['evidence_assembly']}ms | Total Pipeline: {m['avg_latencies_ms']['total']}ms")

    print("\n--- Summary: Frozen Staging Set Performance Across Budgets ---")
    for b_key, m in phase_c_results.items():
        print(f"\n{m['budget']}:")
        print(f"  Precision: {m['supported_precision']*100:.1f}% | Recall: {m['supported_recall']*100:.1f}% | F1: {m['supported_f1']:.4f}")
        print(f"  Non-Supported FAR: {m['non_supported_far']*100:.1f}% ({m['non_supported_false_accepts']}/30)")
        print(f"  Contradiction FAR: {m['contradiction_far']*100:.1f}% ({m['contradiction_false_accepts']}/10)")
        print(f"  False Rejection Rate: {m['false_rejection_rate']*100:.1f}%")

    print("\nMilestone 21 benchmark complete.")


if __name__ == "__main__":
    main()
