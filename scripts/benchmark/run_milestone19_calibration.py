"""
Milestone 19: NLI Calibration, Policy Comparison & End-to-End Safety Evaluation.

Evaluates 5 conservative decision policies:
1. Policy 1: Deterministic Verifier alone.
2. Policy 2: NLI as Diagnostic Signal Only.
3. Policy 3: NLI Contradiction Veto Only (veto if P_contra >= 0.80).
4. Policy 4: NLI Contradiction / Neutral Downgrade (Shadow Hybrid).
5. Policy 5: Conservative Ambiguity Guard (Policy 4 + Margin Gate).

Evaluated across:
- Diagnostic Set: 42 claims (Milestone 17: 30 claims, Milestone 18: 12 claims).
- Untouched Held-Out Set: 30 claims (Milestone 19 Unseen Claims).

Outputs:
- evaluation/rag/milestone19_policy_comparison.json
- evaluation/rag/milestone19_disagreement_audit.jsonl
"""
import os
import sys
import json
import time
import psutil
from typing import Dict, Any, List, Tuple, Optional
from pathlib import Path
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.rag.models import EvidencePassage, ClaimAttribution, CitationValidationResult
from services.rag.claim_verifier import ClaimVerifier, ClaimVerificationStatus
from services.rag.nli_verifier import LocalNLIVerifier, DEFAULT_NLI_MODEL_ID
from services.rag.pipeline import RAGPipeline
from services.rag.providers import MockLLMProvider


def evaluate_policy(
    policy_id: str,
    deterministic_status: str,
    nli_label: str,
    nli_confidence: float,
    nli_probs: Dict[str, float]
) -> str:
    """Evaluate one of the 5 candidate policies on a single claim."""
    p_contra = nli_probs.get("contradiction", 0.0)
    p_entail = nli_probs.get("entailment", 0.0)
    p_neut = nli_probs.get("neutral", 0.0)

    # Policy 1: Deterministic alone
    if policy_id == "policy_1_deterministic_alone":
        return deterministic_status

    # Policy 2: NLI Diagnostic Only (deterministic drives outcome)
    elif policy_id == "policy_2_diagnostic_only":
        return deterministic_status

    # Policy 3: NLI Contradiction Veto Only
    elif policy_id == "policy_3_contradiction_veto":
        if deterministic_status == "supported" and p_contra >= 0.80:
            return "contradicted"
        if deterministic_status in ["partially_supported", "not_evaluated"] and p_contra >= 0.85:
            return "contradicted"
        return deterministic_status

    # Policy 4: NLI Contradiction / Neutral Downgrade (Shadow Hybrid)
    elif policy_id == "policy_4_shadow_hybrid":
        if deterministic_status == "contradicted":
            return "contradicted"
        if deterministic_status == "unsupported":
            return "unsupported"
        if deterministic_status == "supported":
            if p_contra >= 0.80:
                return "contradicted"
            elif nli_label == "neutral" or p_entail < 0.60:
                return "not_evaluated"
            else:
                return "supported"
        else:  # partially_supported or not_evaluated
            if p_contra >= 0.80:
                return "contradicted"
            # Never promote unconfirmed claims to supported
            return deterministic_status

    # Policy 5: Conservative Ambiguity Guard (Policy 4 + Margin Gate)
    elif policy_id == "policy_5_ambiguity_guard":
        if deterministic_status == "contradicted":
            return "contradicted"
        if deterministic_status == "unsupported":
            return "unsupported"

        sorted_probs = sorted(nli_probs.values(), reverse=True)
        top1 = sorted_probs[0] if len(sorted_probs) > 0 else 0.0
        top2 = sorted_probs[1] if len(sorted_probs) > 1 else 0.0
        margin = top1 - top2

        # If model is ambiguous (low confidence or small margin between top classes)
        if top1 < 0.70 or margin < 0.25:
            if deterministic_status == "supported":
                return "not_evaluated"  # Preserve uncertainty
            return deterministic_status

        # Otherwise apply Policy 4 rules
        if deterministic_status == "supported":
            if p_contra >= 0.80:
                return "contradicted"
            elif nli_label == "neutral" or p_entail < 0.60:
                return "not_evaluated"
            else:
                return "supported"
        else:
            if p_contra >= 0.80:
                return "contradicted"
            return deterministic_status

    return deterministic_status


def compute_policy_metrics(records: List[Dict[str, Any]], pred_key: str) -> Dict[str, Any]:
    """Compute detailed precision, recall, disaggregated FARs, and false rejections."""
    total = len(records)
    classes = ["supported", "partially_supported", "unsupported", "contradicted", "not_evaluated"]
    gold_counts = {c: 0 for c in classes}
    matrix = {g: {p: 0 for p in classes} for g in classes}

    for r in records:
        gold = r["gold_support_label"]
        pred = r[pred_key]
        gold_counts[gold] = gold_counts.get(gold, 0) + 1
        if gold in matrix and pred in matrix[gold]:
            matrix[gold][pred] += 1

    tp_sup = matrix["supported"]["supported"]
    pred_sup = sum(matrix[g]["supported"] for g in classes)
    true_sup = gold_counts["supported"]

    sup_prec = round(tp_sup / pred_sup, 4) if pred_sup > 0 else 0.0
    sup_rec = round(tp_sup / true_sup, 4) if true_sup > 0 else 0.0
    sup_f1 = round(2 * sup_prec * sup_rec / (sup_prec + sup_rec), 4) if (sup_prec + sup_rec) > 0 else 0.0

    contra_fa = matrix["contradicted"]["supported"]
    contra_total = gold_counts["contradicted"]
    contra_far = round(contra_fa / contra_total, 4) if contra_total > 0 else 0.0

    unsup_fa = matrix["unsupported"]["supported"]
    unsup_total = gold_counts["unsupported"]
    unsup_far = round(unsup_fa / unsup_total, 4) if unsup_total > 0 else 0.0

    part_fa = matrix["partially_supported"]["supported"]
    part_total = gold_counts["partially_supported"]
    part_far = round(part_fa / part_total, 4) if part_total > 0 else 0.0

    non_sup_total = contra_total + unsup_total + part_total
    non_sup_fa = contra_fa + unsup_fa + part_fa
    non_sup_far = round(non_sup_fa / non_sup_total, 4) if non_sup_total > 0 else 0.0

    # False rejection rate: fraction of gold supported claims NOT predicted as supported
    false_rejections = true_sup - tp_sup
    false_rejection_rate = round(false_rejections / true_sup, 4) if true_sup > 0 else 0.0

    # Claims unresolved or downgraded to not_evaluated
    unresolved_count = sum(matrix[g]["not_evaluated"] for g in classes)
    unresolved_rate = round(unresolved_count / total, 4) if total > 0 else 0.0

    # Safe presentation compliance: answers not falsely verified
    safe_answers = total - non_sup_fa
    safe_rate = round(safe_answers / total, 4) if total > 0 else 0.0

    # Answer-level false verification rate (fraction of non-supported answers receiving verified badge)
    ans_false_verification_rate = non_sup_far

    return {
        "total_claims": total,
        "supported_precision": sup_prec,
        "supported_recall": sup_rec,
        "supported_f1": sup_f1,
        "non_supported_far": non_sup_far,
        "contradiction_far": contra_far,
        "contradiction_false_accepts": contra_fa,
        "unsupported_far": unsup_far,
        "unsupported_false_accepts": unsup_fa,
        "partially_supported_far": part_far,
        "partially_supported_false_accepts": part_fa,
        "false_rejections_count": false_rejections,
        "false_rejection_rate": false_rejection_rate,
        "unresolved_count": unresolved_count,
        "unresolved_rate": unresolved_rate,
        "safe_presentation_compliance_rate": safe_rate,
        "answer_false_verification_rate": ans_false_verification_rate,
        "confusion_matrix": matrix
    }


def assign_error_category(gold: str, pred_det: str, nli_label: str, claim: str, passage: str) -> str:
    """Categorize the linguistic/structural nature of an error."""
    c_low = claim.lower()
    p_low = passage.lower()

    if gold == "contradicted":
        if "other than" in p_low or "excluding" in p_low:
            return "exclusionary_clause_inversion"
        if any(w in c_low for w in ["cannot", "barred", "not entitled", "no power", "dismissed"]) and any(w in p_low for w in ["allowed", "entitled", "has power"]):
            return "holding_inversion"
        if any(w in c_low for w in ["empowered", "authorized", "absolute authority", "always"]) and any(w in p_low for w in ["impermissible", "cannot", "no authority", "not open"]):
            return "holding_inversion"
        return "holding_inversion"

    if gold == "partially_supported":
        if "other than" in p_low or "excluding" in p_low:
            return "exclusionary_clause_inversion"
        if any(w in c_low for w in ["without", "unconditionally", "freely"]):
            return "missing_statutory_condition"
        if any(w in c_low for w in ["all", "every", "automatically", "in all cases"]):
            return "overgeneralization"
        return "partial_support"

    if gold == "unsupported":
        return "ambiguous_or_insufficient_evidence"

    if gold == "supported":
        if "learned counsel" in p_low or "appellant submitted" in p_low:
            return "party_submission_vs_holding"
        if "earlier decision" in p_low or "quoted" in p_low:
            return "quoted_precedent"
        return "none_correct"

    return "general_classification"


def run_e2e_performance_benchmark(
    nli_verifier: LocalNLIVerifier,
    pipeline: RAGPipeline
) -> Dict[str, Any]:
    """Measure warm and cold end-to-end performance across pipeline components."""
    process = psutil.Process(os.getpid())
    mem_baseline_mb = process.memory_info().rss / (1024 * 1024)

    # 1. Measure Cold vs Warm NLI model load time
    t0_cold = time.perf_counter()
    cold_verifier = LocalNLIVerifier(lazy_load=False)
    cold_load_ms = round((time.perf_counter() - t0_cold) * 1000.0, 2)

    t0_warm = time.perf_counter()
    warm_avail = cold_verifier.is_available
    warm_check_ms = round((time.perf_counter() - t0_warm) * 1000.0, 2)

    mem_after_model_mb = process.memory_info().rss / (1024 * 1024)
    model_mem_delta_mb = round(mem_after_model_mb - mem_baseline_mb, 2)

    # 2. Run representative end-to-end pipeline queries
    test_queries = [
        "What are the essential elements required to establish abetment of suicide under Section 306 IPC?",
        "Can a High Court decide a second appeal without formulating substantial questions of law?",
        "Does ad-hoc service count towards regular seniority in judicial service?"
    ]

    pipeline_results = []
    for q in test_queries:
        res = pipeline.query(
            query_text=q,
            top_k_judgments=3,
            max_passages=3,
            enable_graph=False,
            structured_output=True
        )
        pipeline_results.append(res)

    mem_final_mb = process.memory_info().rss / (1024 * 1024)

    retrieval_times = [r.timing_ms.get("retrieval_ms", 0.0) for r in pipeline_results]
    assembly_times = [r.timing_ms.get("evidence_assembly_ms", 0.0) for r in pipeline_results]
    gate_times = [r.timing_ms.get("grounding_gate_ms", 0.0) for r in pipeline_results]
    generation_times = [r.timing_ms.get("generation_ms", 0.0) for r in pipeline_results]
    validation_times = [r.timing_ms.get("validation_ms", 0.0) for r in pipeline_results]
    total_times = [r.timing_ms.get("total_ms", 0.0) for r in pipeline_results]

    return {
        "model_cold_load_time_ms": cold_load_ms,
        "model_warm_check_time_ms": warm_check_ms,
        "model_memory_overhead_mb": model_mem_delta_mb,
        "final_process_rss_mb": round(mem_final_mb, 2),
        "end_to_end_pipeline_averages": {
            "retrieval_mean_ms": round(float(np.mean(retrieval_times)), 2),
            "evidence_assembly_mean_ms": round(float(np.mean(assembly_times)), 2),
            "grounding_gate_mean_ms": round(float(np.mean(gate_times)), 2),
            "generation_mean_ms": round(float(np.mean(generation_times)), 2),
            "validation_mean_ms": round(float(np.mean(validation_times)), 2),
            "total_answer_latency_mean_ms": round(float(np.mean(total_times)), 2)
        },
        "sample_queries_evaluated": len(test_queries),
        "verification_badges_assigned": [r.verification_badge for r in pipeline_results]
    }


def main():
    print("=" * 80)
    print("NyayaVarta — Milestone 19: NLI Calibration, Policy Comparison & Safety Evaluation")
    print("=" * 80)

    # Initialize components
    nli_verifier = LocalNLIVerifier()
    deterministic_verifier = ClaimVerifier()
    pipeline = RAGPipeline(
        llm_provider=MockLLMProvider(mode=MockLLMProvider.MODE_STRUCTURED_NORMAL)
    )

    # Load Dataset A: Diagnostic Set (M17: 30 claims, M18: 12 claims)
    diagnostic_records = []
    for fn in ["evaluation/rag/milestone17_unseen_claims.jsonl", "evaluation/rag/milestone18_generalization_claims.jsonl"]:
        path = PROJECT_ROOT / fn
        if path.exists():
            with path.open("r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        diagnostic_records.append(json.loads(line))
    print(f"Loaded Diagnostic Dataset: {len(diagnostic_records)} claims (M17: 30, M18: 12)")

    # Load Dataset B: Untouched Held-Out Set (M19: 30 claims)
    heldout_records = []
    m19_path = PROJECT_ROOT / "evaluation" / "rag" / "milestone19_unseen_claims.jsonl"
    with m19_path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                heldout_records.append(json.loads(line))
    print(f"Loaded Held-Out Evaluation Dataset: {len(heldout_records)} claims (M19)")

    all_audited_cases = []

    def _process_dataset(cases: List[Dict[str, Any]], dataset_tag: str):
        processed = []
        for c in cases:
            case_id = c["case_id"]
            claim_text = c["claim_sentence"]
            gold = c["gold_support_label"]
            passages = c["supporting_passages"]
            p_text = passages[0]["passage_text"]
            eid = passages[0].get("evidence_id", "E1")

            ep = EvidencePassage(
                evidence_id=eid,
                document_id=passages[0].get("document_id", "doc_1"),
                case_title=passages[0].get("case_title", "Unknown"),
                passage_text=p_text,
                start_char=passages[0].get("start_char", 0),
                end_char=passages[0].get("end_char", len(p_text)),
                structural_label=passages[0].get("structural_label", "headnote_holding")
            )

            # Deterministic prediction
            v_res = deterministic_verifier.verify_claim(
                claim_text=claim_text,
                cited_passages=[ep],
                query=c.get("question", "")
            )
            det_status = v_res.status.value

            # NLI inference
            nli_res = nli_verifier.predict(premise=p_text, hypothesis=claim_text)

            # Evaluate all 5 policies
            p1_pred = evaluate_policy("policy_1_deterministic_alone", det_status, nli_res.label, nli_res.confidence, nli_res.probabilities)
            p2_pred = evaluate_policy("policy_2_diagnostic_only", det_status, nli_res.label, nli_res.confidence, nli_res.probabilities)
            p3_pred = evaluate_policy("policy_3_contradiction_veto", det_status, nli_res.label, nli_res.confidence, nli_res.probabilities)
            p4_pred = evaluate_policy("policy_4_shadow_hybrid", det_status, nli_res.label, nli_res.confidence, nli_res.probabilities)
            p5_pred = evaluate_policy("policy_5_ambiguity_guard", det_status, nli_res.label, nli_res.confidence, nli_res.probabilities)

            status_changed = (det_status != p4_pred)
            prevented_fa = (gold != "supported" and det_status == "supported" and p4_pred != "supported")
            caused_fr = (gold == "supported" and det_status == "supported" and p4_pred != "supported")

            err_cat = assign_error_category(gold, det_status, nli_res.label, claim_text, p_text)

            rec = {
                "case_id": case_id,
                "dataset_tag": dataset_tag,
                "gold_support_label": gold,
                "claim_sentence": claim_text,
                "premise_excerpt": p_text[:140] + "...",
                "deterministic_status": det_status,
                "deterministic_method": v_res.method,
                "deterministic_reason": v_res.reason,
                "nli_label": nli_res.label,
                "nli_confidence": nli_res.confidence,
                "nli_probabilities": nli_res.probabilities,
                "raw_logits": nli_res.raw_logits,
                "nli_latency_ms": nli_res.latency_ms,
                "policy_1_deterministic_alone_pred": p1_pred,
                "policy_2_diagnostic_only_pred": p2_pred,
                "policy_3_contradiction_veto_pred": p3_pred,
                "policy_4_shadow_hybrid_pred": p4_pred,
                "policy_5_ambiguity_guard_pred": p5_pred,
                "status_changed_by_hybrid": status_changed,
                "prevented_false_acceptance": prevented_fa,
                "caused_false_rejection": caused_fr,
                "error_category": err_cat
            }
            processed.append(rec)
            all_audited_cases.append(rec)
        return processed

    print("\nProcessing Diagnostic Set...")
    processed_diag = _process_dataset(diagnostic_records, "diagnostic_m17_m18")
    print("Processing Untouched Held-Out Set (M19)...")
    processed_heldout = _process_dataset(heldout_records, "heldout_m19")

    # Save Disagreement Audit to JSONL
    disagreements = [c for c in all_audited_cases if c["status_changed_by_hybrid"]]
    audit_file = PROJECT_ROOT / "evaluation" / "rag" / "milestone19_disagreement_audit.jsonl"
    with audit_file.open("w", encoding="utf-8") as f:
        for d in disagreements:
            f.write(json.dumps(d) + "\n")
    print(f"Logged {len(disagreements)} total disagreements to {audit_file}")

    # Compute policy comparisons
    policies = [
        "policy_1_deterministic_alone",
        "policy_2_diagnostic_only",
        "policy_3_contradiction_veto",
        "policy_4_shadow_hybrid",
        "policy_5_ambiguity_guard"
    ]

    policy_eval_diag = {p: compute_policy_metrics(processed_diag, f"{p}_pred") for p in policies}
    policy_eval_heldout = {p: compute_policy_metrics(processed_heldout, f"{p}_pred") for p in policies}

    # Run End-to-End Performance Profiling
    print("\nMeasuring End-to-End Pipeline Performance...")
    e2e_profile = run_e2e_performance_benchmark(nli_verifier, pipeline)

    # Save complete evaluation output
    final_output = {
        "milestone": "Milestone 19 - NLI Calibration and End-to-End Safety Evaluation",
        "model_metadata": {
            "model_id": nli_verifier.model_id,
            "license": "Apache-2.0",
            "weights_format": "quantized_onnx_quint8_avx2",
            "model_size_mb": 172.5
        },
        "performance_profile": e2e_profile,
        "diagnostic_set_evaluation": {
            "total_claims": len(processed_diag),
            "policy_metrics": policy_eval_diag
        },
        "heldout_set_evaluation": {
            "total_claims": len(processed_heldout),
            "provenance": "developer_curated_frozen_pre_evaluation",
            "policy_metrics": policy_eval_heldout
        },
        "disagreement_audit_summary": {
            "total_disagreements_logged": len(disagreements),
            "prevented_false_acceptances_count": sum(1 for c in all_audited_cases if c["prevented_false_acceptance"]),
            "caused_false_rejections_count": sum(1 for c in all_audited_cases if c["caused_false_rejection"]),
            "error_category_distribution": {}
        }
    }

    for d in disagreements:
        cat = d["error_category"]
        final_output["disagreement_audit_summary"]["error_category_distribution"][cat] = (
            final_output["disagreement_audit_summary"]["error_category_distribution"].get(cat, 0) + 1
        )

    out_json = PROJECT_ROOT / "evaluation" / "rag" / "milestone19_policy_comparison.json"
    with out_json.open("w", encoding="utf-8") as f:
        json.dump(final_output, f, indent=2)
    print(f"Complete results saved to: {out_json}")

    # Print summary table for held-out evaluation
    print("\n" + "=" * 90)
    print("HELDOUT (M19) POLICY COMPARISON SUMMARY (30 UNSEEN CLAIMS)")
    print("=" * 90)
    print(f"{'Policy':<35} | {'Precision':<10} | {'Recall':<10} | {'Non-Sup FAR':<12} | {'Contra FAR':<12} | {'Safe Comp':<10}")
    print("-" * 90)
    for p in policies:
        m = policy_eval_heldout[p]
        p_name = p.replace("policy_", "P").replace("_", " ")
        print(f"{p_name:<35} | {m['supported_precision']:<10.2%} | {m['supported_recall']:<10.2%} | {m['non_supported_far']:<12.2%} | {m['contradiction_far']:<12.2%} | {m['safe_presentation_compliance_rate']:<10.2%}")
    print("=" * 90)


if __name__ == "__main__":
    main()
