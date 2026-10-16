"""
Milestone 18 NLI Feasibility Benchmark & Controlled Comparison Runner.

Evaluates 3 configurations:
1. Config 1: Deterministic ClaimVerifier alone (Baseline).
2. Config 2: Local NLI Model alone (cross-encoder/nli-deberta-v3-small on CPU).
3. Config 3: Deterministic Verifier + NLI Shadow Hybrid Decision Layer.

Across two datasets:
- Dataset A: Milestone 17 Unseen Claims (30 claims - Diagnostic set).
- Dataset B: Milestone 18 Generalization Claims (12 claims - Held-out unseen set).

Outputs:
- evaluation/rag/milestone18_nli_results.json
- evaluation/rag/milestone18_disagreement_audit.jsonl
"""
import os
import sys
import json
import time
import psutil
from typing import Dict, Any, List, Tuple
import numpy as np

# Ensure project root is in path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from services.rag.models import EvidencePassage, ClaimAttribution, CitationValidationResult
from services.rag.claim_verifier import ClaimVerifier, ClaimVerificationStatus
from services.rag.nli_verifier import LocalNLIVerifier, DEFAULT_NLI_MODEL_ID


def compute_metrics(records: List[Dict[str, Any]], pred_key: str) -> Dict[str, Any]:
    """Compute precision, recall, F1, and disaggregated FARs for a given prediction key."""
    total = len(records)
    classes = ["supported", "partially_supported", "unsupported", "contradicted", "not_evaluated"]
    gold_counts = {c: 0 for c in classes}
    pred_counts = {c: 0 for c in classes}
    matrix = {g: {p: 0 for p in classes} for g in classes}

    for r in records:
        gold = r["gold_support_label"]
        pred = r[pred_key]
        gold_counts[gold] = gold_counts.get(gold, 0) + 1
        pred_counts[pred] = pred_counts.get(pred, 0) + 1
        if gold in matrix and pred in matrix[gold]:
            matrix[gold][pred] += 1

    # Supported class metrics
    tp_sup = matrix["supported"]["supported"]
    pred_sup = sum(matrix[g]["supported"] for g in classes)
    true_sup = gold_counts["supported"]

    sup_prec = round(tp_sup / pred_sup, 4) if pred_sup > 0 else 0.0
    sup_rec = round(tp_sup / true_sup, 4) if true_sup > 0 else 0.0
    sup_f1 = round(2 * sup_prec * sup_rec / (sup_prec + sup_rec), 4) if (sup_prec + sup_rec) > 0 else 0.0

    # Disaggregated False Acceptance into 'supported'
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

    # Uncertainty (% predicted as not_evaluated)
    uncertain_count = pred_counts.get("not_evaluated", 0)
    uncertainty_rate = round(uncertain_count / total, 4) if total > 0 else 0.0

    # Safe presentation compliance: answer is safe if non-supported claim did NOT get predicted as supported
    # In single-claim per answer context, safe answers = total - non_sup_fa
    safe_answers = total - non_sup_fa
    safe_rate = round(safe_answers / total, 4) if total > 0 else 0.0

    return {
        "total_evaluations": total,
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
        "total_false_acceptances_into_supported": non_sup_fa,
        "uncertainty_rate": uncertainty_rate,
        "uncertain_count": uncertain_count,
        "safe_presentation_compliance_rate": safe_rate,
        "safe_answers_count": safe_answers,
        "confusion_matrix": matrix
    }


def evaluate_dataset(
    dataset_path: str,
    dataset_name: str,
    deterministic_verifier: ClaimVerifier,
    nli_verifier: LocalNLIVerifier
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Run evaluation across all 3 configs on a dataset."""
    records = []
    with open(dataset_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))

    evaluated_records = []
    latencies = []

    for r in records:
        case_id = r["case_id"]
        claim_text = r["claim_sentence"]
        gold = r["gold_support_label"]
        passages = r["supporting_passages"]
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

        claim_attr = ClaimAttribution(
            sentence=claim_text,
            cited_evidence_ids=[eid]
        )

        # Config 1: Deterministic alone
        v_res = deterministic_verifier.verify_claim(
            claim_text=claim_text,
            cited_passages=[ep],
            query=r.get("question", "")
        )
        c1_pred = v_res.status.value

        # Config 2: NLI alone
        nli_res = nli_verifier.predict(premise=p_text, hypothesis=claim_text)
        latencies.append(nli_res.latency_ms)

        if nli_res.label == "entailment":
            c2_pred = "supported"
        elif nli_res.label == "contradiction":
            c2_pred = "contradicted"
        else:
            c2_pred = "not_evaluated"

        # Config 3: Shadow Hybrid (Safe Decision Layer)
        shadow_verdict = nli_verifier.evaluate_shadow(
            claim=claim_text,
            passage=p_text,
            deterministic_status=c1_pred,
            deterministic_method=v_res.method
        )
        c3_pred = shadow_verdict.shadow_recommended_status

        evaluated_records.append({
            "case_id": case_id,
            "dataset": dataset_name,
            "claim_text": claim_text,
            "gold_support_label": gold,
            "premise_excerpt": p_text[:140] + "...",
            "config1_deterministic_pred": c1_pred,
            "config1_method": v_res.method,
            "config2_nli_pred": c2_pred,
            "config2_nli_label": nli_res.label,
            "config2_nli_confidence": nli_res.confidence,
            "config2_nli_probs": nli_res.probabilities,
            "config3_shadow_pred": c3_pred,
            "has_disagreement": shadow_verdict.has_disagreement,
            "disagreement_type": shadow_verdict.disagreement_type,
            "shadow_rationale": shadow_verdict.audit_rationale,
            "nli_latency_ms": nli_res.latency_ms
        })

    # Compute metrics for each config
    metrics_c1 = compute_metrics(evaluated_records, "config1_deterministic_pred")
    metrics_c2 = compute_metrics(evaluated_records, "config2_nli_pred")
    metrics_c3 = compute_metrics(evaluated_records, "config3_shadow_pred")

    latency_stats = {
        "mean_latency_ms": round(float(np.mean(latencies)), 2) if latencies else 0.0,
        "min_latency_ms": round(float(np.min(latencies)), 2) if latencies else 0.0,
        "max_latency_ms": round(float(np.max(latencies)), 2) if latencies else 0.0,
        "p95_latency_ms": round(float(np.percentile(latencies, 95)), 2) if latencies else 0.0
    }

    dataset_summary = {
        "dataset_name": dataset_name,
        "dataset_file": dataset_path,
        "total_claims": len(evaluated_records),
        "gold_distribution": {
            "supported": sum(1 for r in evaluated_records if r["gold_support_label"] == "supported"),
            "partially_supported": sum(1 for r in evaluated_records if r["gold_support_label"] == "partially_supported"),
            "unsupported": sum(1 for r in evaluated_records if r["gold_support_label"] == "unsupported"),
            "contradicted": sum(1 for r in evaluated_records if r["gold_support_label"] == "contradicted")
        },
        "config1_deterministic_alone": metrics_c1,
        "config2_nli_alone": metrics_c2,
        "config3_shadow_hybrid": metrics_c3,
        "latency_stats": latency_stats
    }

    return dataset_summary, evaluated_records


def main():
    print("=" * 80)
    print("NyayaVarta — Milestone 18: NLI Feasibility Benchmark & Controlled Comparison")
    print("=" * 80)

    # Measure system memory and load time
    process = psutil.Process(os.getpid())
    mem_before_mb = process.memory_info().rss / (1024 * 1024)

    t0_load = time.perf_counter()
    nli_verifier = LocalNLIVerifier()
    t_load_ms = (time.perf_counter() - t0_load) * 1000.0
    mem_after_mb = process.memory_info().rss / (1024 * 1024)
    mem_delta_mb = mem_after_mb - mem_before_mb

    print(f"Model: {nli_verifier.model_id}")
    print(f"Load Time: {t_load_ms:.1f}ms")
    print(f"Memory Overhead: {mem_delta_mb:.1f} MB (Total Process: {mem_after_mb:.1f} MB)")
    print(f"Model Available: {nli_verifier.is_available}")

    deterministic_verifier = ClaimVerifier()

    # Evaluate Dataset A: M17 Unseen Claims (30 cases - Diagnostic Baseline)
    m17_path = os.path.join(project_root, "evaluation", "rag", "milestone17_unseen_claims.jsonl")
    print(f"\nEvaluating Dataset A (Milestone 17 Diagnostic Set, 30 claims)...")
    summary_m17, records_m17 = evaluate_dataset(
        dataset_path=m17_path,
        dataset_name="milestone17_unseen_diagnostic",
        deterministic_verifier=deterministic_verifier,
        nli_verifier=nli_verifier
    )

    # Evaluate Dataset B: M18 Generalization Claims (12 cases - Held-out Set)
    m18_path = os.path.join(project_root, "evaluation", "rag", "milestone18_generalization_claims.jsonl")
    print(f"Evaluating Dataset B (Milestone 18 Generalization Set, 12 claims)...")
    summary_m18, records_m18 = evaluate_dataset(
        dataset_path=m18_path,
        dataset_name="milestone18_generalization_heldout",
        deterministic_verifier=deterministic_verifier,
        nli_verifier=nli_verifier
    )

    all_records = records_m17 + records_m18
    disagreements = [r for r in all_records if r["has_disagreement"]]

    # Save disagreements audit
    audit_path = os.path.join(project_root, "evaluation", "rag", "milestone18_disagreement_audit.jsonl")
    with open(audit_path, "w", encoding="utf-8") as f:
        for d in disagreements:
            f.write(json.dumps(d) + "\n")
    print(f"\nDisagreements logged to: {audit_path} (Total: {len(disagreements)})")

    # Save full machine-readable results
    final_output = {
        "milestone": "Milestone 18 - Local NLI Verification Feasibility & Benchmark",
        "model_metadata": {
            "model_id": nli_verifier.model_id,
            "onnx_file": nli_verifier.onnx_filename,
            "license": "Apache-2.0",
            "model_size_mb": 172.5,
            "architecture": "DebertaV2ForSequenceClassification",
            "execution_provider": "CPUExecutionProvider",
            "load_time_ms": round(t_load_ms, 2),
            "memory_delta_mb": round(mem_delta_mb, 2),
            "process_rss_mb": round(mem_after_mb, 2)
        },
        "datasets": {
            "milestone17_diagnostic": summary_m17,
            "milestone18_generalization": summary_m18
        },
        "disagreement_audit_summary": {
            "total_disagreements": len(disagreements),
            "breakdown_by_type": {}
        }
    }

    # Disagreement breakdown
    for d in disagreements:
        dt = d["disagreement_type"]
        final_output["disagreement_audit_summary"]["breakdown_by_type"][dt] = (
            final_output["disagreement_audit_summary"]["breakdown_by_type"].get(dt, 0) + 1
        )

    results_path = os.path.join(project_root, "evaluation", "rag", "milestone18_nli_results.json")
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(final_output, f, indent=2)
    print(f"Full benchmark results saved to: {results_path}")

    # Print summary table
    print("\n" + "=" * 80)
    print("CONTROLLED BENCHMARK COMPARISON SUMMARY")
    print("=" * 80)
    print(f"{'Metric':<35} | {'Config 1 (Deterministic)':<25} | {'Config 2 (NLI Alone)':<22} | {'Config 3 (Shadow Hybrid)':<25}")
    print("-" * 115)

    def _row(metric_name, k):
        v1 = summary_m17["config1_deterministic_alone"][k]
        v2 = summary_m17["config2_nli_alone"][k]
        v3 = summary_m17["config3_shadow_hybrid"][k]
        print(f"{metric_name:<35} | {str(v1):<25} | {str(v2):<22} | {str(v3):<25}")

    _row("Supported Precision", "supported_precision")
    _row("Supported Recall", "supported_recall")
    _row("Non-Supported False Acceptance (FAR)", "non_supported_far")
    _row("Contradiction FAR", "contradiction_far")
    _row("Unsupported FAR", "unsupported_far")
    _row("Partial Support FAR", "partially_supported_far")
    _row("Safe Presentation Compliance", "safe_presentation_compliance_rate")
    _row("Uncertainty Rate (not_evaluated)", "uncertainty_rate")
    print("=" * 115)


if __name__ == "__main__":
    main()
