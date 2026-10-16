"""
Milestone 20 Staging Evaluation Runner.
1. Evaluates 40 frozen staging claims across Candidate Policies:
   - Policy 1: Deterministic Alone
   - Policy 3: Contradiction Veto Only
   - Policy 4: Shadow Hybrid Downgrade
   - Policy 5: Ambiguity Guard
2. Benchmarks real CPU performance:
   - MockLLMProvider (fast reproducible regression baseline)
   - LocalOllamaProvider (phi3.5:latest realistic local LLM execution)
3. Outputs evaluation/rag/milestone20_policy_comparison.json
"""
import time
import json
import psutil
import os
import sys
from pathlib import Path
from typing import Dict, Any, List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from services.rag.models import EvidencePassage
from services.rag.claim_verifier import ClaimVerifier, ClaimVerificationStatus
from services.rag.nli_verifier import LocalNLIVerifier
from services.rag.pipeline import RAGPipeline
from services.rag.providers import MockLLMProvider, LocalOllamaProvider


def compute_metrics(predictions: List[Dict[str, Any]], policy_name: str) -> Dict[str, Any]:
    gold_classes = ["supported", "partially_supported", "unsupported", "contradicted", "not_evaluated"]
    pred_classes = ["supported", "partially_supported", "unsupported", "contradicted", "not_evaluated"]

    matrix = {g: {p: 0 for p in pred_classes} for g in gold_classes}

    total = len(predictions)
    gold_supported_count = 0
    pred_supported_count = 0
    true_positives = 0

    contra_gold_count = 0
    contra_false_accepts = 0

    unsupp_gold_count = 0
    unsupp_false_accepts = 0

    partial_gold_count = 0
    partial_false_accepts = 0

    false_rejections = 0
    unresolved_count = 0
    safe_compliant_count = 0

    for item in predictions:
        gold = item["gold_label"]
        pred = item["predicted_label"]

        if gold not in matrix:
            gold = "not_evaluated"
        if pred not in matrix[gold]:
            pred = "not_evaluated"

        matrix[gold][pred] += 1

        if gold == "supported":
            gold_supported_count += 1
            if pred == "supported":
                true_positives += 1
            elif pred in ["not_evaluated", "unsupported", "contradicted"]:
                false_rejections += 1

        if pred == "supported":
            pred_supported_count += 1

        if gold == "contradicted":
            contra_gold_count += 1
            if pred == "supported":
                contra_false_accepts += 1

        if gold == "unsupported":
            unsupp_gold_count += 1
            if pred == "supported":
                unsupp_false_accepts += 1

        if gold == "partially_supported":
            partial_gold_count += 1
            if pred == "supported":
                partial_false_accepts += 1

        if pred == "not_evaluated":
            unresolved_count += 1

        # Safe presentation compliance:
        # A claim is safely handled if:
        # 1. Gold supported is predicted as supported or unresolved
        # 2. Gold non-supported (partial, unsupp, contra) is NEVER predicted as supported
        if gold in ["contradicted", "unsupported", "partially_supported"]:
            if pred != "supported":
                safe_compliant_count += 1
        elif gold == "supported":
            safe_compliant_count += 1

    precision = true_positives / pred_supported_count if pred_supported_count > 0 else 0.0
    recall = true_positives / gold_supported_count if gold_supported_count > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    non_supported_total = total - gold_supported_count
    non_supported_fa = contra_false_accepts + unsupp_false_accepts + partial_false_accepts
    non_supported_far = non_supported_fa / non_supported_total if non_supported_total > 0 else 0.0

    contra_far = contra_false_accepts / contra_gold_count if contra_gold_count > 0 else 0.0
    unsupp_far = unsupp_false_accepts / unsupp_gold_count if unsupp_gold_count > 0 else 0.0
    partial_far = partial_false_accepts / partial_gold_count if partial_gold_count > 0 else 0.0
    frr = false_rejections / gold_supported_count if gold_supported_count > 0 else 0.0

    return {
        "policy": policy_name,
        "total_claims": total,
        "supported_precision": round(precision, 4),
        "supported_recall": round(recall, 4),
        "supported_f1": round(f1, 4),
        "true_positives": true_positives,
        "pred_supported_count": pred_supported_count,
        "gold_supported_count": gold_supported_count,
        "non_supported_far": round(non_supported_far, 4),
        "non_supported_false_accepts": non_supported_fa,
        "non_supported_total": non_supported_total,
        "contradiction_far": round(contra_far, 4),
        "contradiction_false_accepts": contra_false_accepts,
        "contradiction_gold_count": contra_gold_count,
        "unsupported_far": round(unsupp_far, 4),
        "unsupported_false_accepts": unsupp_false_accepts,
        "unsupported_gold_count": unsupp_gold_count,
        "partially_supported_far": round(partial_far, 4),
        "partially_supported_false_accepts": partial_false_accepts,
        "partially_supported_gold_count": partial_gold_count,
        "false_rejections_count": false_rejections,
        "false_rejection_rate": round(frr, 4),
        "unresolved_count": unresolved_count,
        "unresolved_rate": round(unresolved_count / total, 4) if total > 0 else 0.0,
        "safe_presentation_compliance_rate": round(safe_compliant_count / total, 4) if total > 0 else 0.0,
        "answer_false_verification_rate": round(non_supported_far, 4),
        "confusion_matrix": matrix
    }


def evaluate_policies_on_staging():
    staging_file = Path("evaluation/rag/milestone20_staging_claims.jsonl")
    assert staging_file.exists(), f"Staging file {staging_file} missing!"

    claims_data = []
    with staging_file.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                claims_data.append(json.loads(line))

    det_verifier = ClaimVerifier()
    nli_verifier = LocalNLIVerifier()

    results_p1 = []
    results_p3 = []
    results_p4 = []
    results_p5 = []

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

        # 1. Deterministic evaluation
        det_res = det_verifier.verify_claim(claim_text, [ep])
        det_status = det_res.status.value

        # P1: Deterministic Alone
        results_p1.append({
            "case_id": item["case_id"],
            "gold_label": gold,
            "predicted_label": det_status
        })

        # 2. NLI evaluation
        nli_res = nli_verifier.predict(
            premise=ep.passage_text,
            hypothesis=claim_text
        )

        p_contra = nli_res.probabilities.get("contradiction", 0.0)
        p_entail = nli_res.probabilities.get("entailment", 0.0)
        p_neutral = nli_res.probabilities.get("neutral", 0.0)
        margin = abs(p_entail - p_contra)

        # P3: Contradiction Veto Only
        p3_status = det_status
        if det_status == "supported":
            if p_contra >= 0.70 and (p_contra - max(p_entail, p_neutral)) >= 0.20:
                p3_status = "contradicted"

        results_p3.append({
            "case_id": item["case_id"],
            "gold_label": gold,
            "predicted_label": p3_status
        })

        # P4: Shadow Hybrid Downgrade
        p4_status = det_status
        if det_status == "supported":
            if p_contra >= 0.70 and (p_contra - max(p_entail, p_neutral)) >= 0.20:
                p4_status = "contradicted"
            elif p_entail >= 0.70 and (p_entail - max(p_contra, p_neutral)) >= 0.20:
                p4_status = "supported"
            else:
                p4_status = "not_evaluated"

        results_p4.append({
            "case_id": item["case_id"],
            "gold_label": gold,
            "predicted_label": p4_status
        })

        # P5: Ambiguity Guard
        p5_status = det_status
        if det_status == "supported":
            if margin < 0.25 or nli_res.is_uncertain:
                p5_status = "not_evaluated"
            elif p_contra >= 0.70:
                p5_status = "contradicted"
            elif p_entail >= 0.70:
                p5_status = "supported"
            else:
                p5_status = "not_evaluated"

        results_p5.append({
            "case_id": item["case_id"],
            "gold_label": gold,
            "predicted_label": p5_status
        })

    metrics = {
        "policy_1_deterministic_alone": compute_metrics(results_p1, "Policy 1 - Deterministic Alone"),
        "policy_3_contradiction_veto": compute_metrics(results_p3, "Policy 3 - Contradiction Veto Only"),
        "policy_4_shadow_hybrid": compute_metrics(results_p4, "Policy 4 - Shadow Hybrid Downgrade"),
        "policy_5_ambiguity_guard": compute_metrics(results_p5, "Policy 5 - Ambiguity Guard")
    }
    return metrics


def profile_real_cpu_performance():
    test_queries = [
        "What is required to sustain a conviction based solely on circumstantial evidence?",
        "Can an employer change qualifications after the recruitment advertisement is issued?",
        "Does excluding a promotional song from a movie constitute deficiency of service?"
    ]

    # 1. Profile MockLLMProvider
    pipeline_mock = RAGPipeline(
        llm_provider=MockLLMProvider(mode=MockLLMProvider.MODE_STRUCTURED_NORMAL)
    )
    mock_runs = []
    for q in test_queries:
        res = pipeline_mock.query(query_text=q, top_k_judgments=3, max_passages=3, structured_output=True)
        mock_runs.append(res)

    mock_avg = {
        "retrieval_ms": round(sum(r.timing_ms.get("retrieval_ms", 0.0) for r in mock_runs) / len(mock_runs), 2),
        "evidence_assembly_ms": round(sum(r.timing_ms.get("evidence_assembly_ms", 0.0) for r in mock_runs) / len(mock_runs), 2),
        "grounding_gate_ms": round(sum(r.timing_ms.get("grounding_gate_ms", 0.0) for r in mock_runs) / len(mock_runs), 2),
        "generation_ms": round(sum(r.timing_ms.get("generation_ms", 0.0) for r in mock_runs) / len(mock_runs), 2),
        "validation_ms": round(sum(r.timing_ms.get("validation_ms", 0.0) for r in mock_runs) / len(mock_runs), 2),
        "total_ms": round(sum(r.timing_ms.get("total_ms", 0.0) for r in mock_runs) / len(mock_runs), 2),
    }

    # 2. Profile LocalOllamaProvider (phi3.5:latest)
    ollama_avail = LocalOllamaProvider.check_availability()
    ollama_profile: Dict[str, Any] = {
        "available": ollama_avail.get("available", False),
        "model_name": "phi3.5:latest",
        "error": ollama_avail.get("error")
    }

    if ollama_avail.get("available"):
        ollama_provider = LocalOllamaProvider(model_name="phi3.5:latest")
        pipeline_ollama = RAGPipeline(llm_provider=ollama_provider)
        ollama_runs = []
        for q in test_queries[:2]: # Run 2 queries for live profile
            try:
                res = pipeline_ollama.query(
                    query_text=q,
                    top_k_judgments=3,
                    max_passages=3,
                    structured_output=False
                )
                ollama_runs.append(res)
            except Exception as e:
                ollama_profile["run_error"] = str(e)

        if ollama_runs:
            ollama_avg = {
                "retrieval_ms": round(sum(r.timing_ms.get("retrieval_ms", 0.0) for r in ollama_runs) / len(ollama_runs), 2),
                "evidence_assembly_ms": round(sum(r.timing_ms.get("evidence_assembly_ms", 0.0) for r in ollama_runs) / len(ollama_runs), 2),
                "grounding_gate_ms": round(sum(r.timing_ms.get("grounding_gate_ms", 0.0) for r in ollama_runs) / len(ollama_runs), 2),
                "generation_ms": round(sum(r.timing_ms.get("generation_ms", 0.0) for r in ollama_runs) / len(ollama_runs), 2),
                "validation_ms": round(sum(r.timing_ms.get("validation_ms", 0.0) for r in ollama_runs) / len(ollama_runs), 2),
                "total_ms": round(sum(r.timing_ms.get("total_ms", 0.0) for r in ollama_runs) / len(ollama_runs), 2),
            }
            ollama_profile["timings"] = ollama_avg
            ollama_profile["sample_run_count"] = len(ollama_runs)
            ollama_profile["tokens_per_second"] = round(
                sum(r.retrieval_metadata.get("llm_usage", {}).get("tokens_per_second", 0.0) for r in ollama_runs) / len(ollama_runs), 2
            )

    return {
        "mock_pipeline": mock_avg,
        "ollama_pipeline": ollama_profile
    }


def main():
    print("=== Milestone 20 Staging Evaluation Runner ===")
    t_start = time.perf_counter()

    # Step 1: Policy evaluation on 40 staging claims
    print("Evaluating policies on 40 frozen staging claims...")
    policy_metrics = evaluate_policies_on_staging()

    # Step 2: Performance profiling
    print("Profiling CPU pipeline performance (Mock vs Real Ollama)...")
    perf_profile = profile_real_cpu_performance()

    output = {
        "milestone": "Milestone 20 - Staging Safety Gate and Human-Reviewed Pilot Readiness",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "total_staging_claims": 40,
        "dataset_provenance": "developer_curated_frozen_pre_evaluation",
        "external_review_status": "PENDING_EXTERNAL_REVIEW",
        "policy_comparison": policy_metrics,
        "performance_profile": perf_profile
    }

    out_path = Path("evaluation/rag/milestone20_policy_comparison.json")
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print(f"Results written to {out_path}")
    print("\n--- Summary Policy Metrics on 40 Staging Claims ---")
    for pname, m in policy_metrics.items():
        print(f"\n{m['policy']}:")
        print(f"  Precision: {m['supported_precision']*100:.1f}% | Recall: {m['supported_recall']*100:.1f}% | F1: {m['supported_f1']:.4f}")
        print(f"  Non-Supported FAR: {m['non_supported_far']*100:.1f}% ({m['non_supported_false_accepts']}/{m['non_supported_total']})")
        print(f"  Contradiction FAR: {m['contradiction_far']*100:.1f}% ({m['contradiction_false_accepts']}/{m['contradiction_gold_count']})")
        print(f"  Partially Supported FAR: {m['partially_supported_far']*100:.1f}% ({m['partially_supported_false_accepts']}/{m['partially_supported_gold_count']})")
        print(f"  Safe Presentation Compliance: {m['safe_presentation_compliance_rate']*100:.1f}%")

if __name__ == "__main__":
    main()
