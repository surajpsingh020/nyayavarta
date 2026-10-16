"""
Milestone 14: Unseen Claim Verification Evaluation Runner.

Evaluates the generalization of NyayaVarta's deterministic ClaimVerifier across:
- 44 held-out unseen claim verification test cases.
- Spanning 11 legal categories:
  1. direct_holding_support
  2. directly_contradicted_holding
  3. unrelated_evidence
  4. multipart_partial_support
  5. missing_statutory_exception
  6. party_submissions_as_holding
  7. quoted_landmark_precedent_confusion
  8. overgeneralized_equitable_relief
  9. negation_modal_verb_variation
  10. lexical_divergence_support
  11. genuinely_ambiguous_uncertainty

Outputs:
- evaluation/rag/milestone14_verification_results.json
"""
import os
import sys
import json
import time
from pathlib import Path
from collections import defaultdict

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from services.rag.models import EvidencePassage
from services.rag.claim_verifier import ClaimVerifier, ClaimVerificationStatus

UNSEEN_DATASET_PATH = PROJECT_ROOT / "evaluation" / "rag" / "milestone14_unseen_claims.jsonl"
OUTPUT_RESULTS_PATH = PROJECT_ROOT / "evaluation" / "rag" / "milestone14_verification_results.json"


def run_evaluation():
    if not UNSEEN_DATASET_PATH.exists():
        raise FileNotFoundError(f"Dataset not found at {UNSEEN_DATASET_PATH}")

    with open(UNSEEN_DATASET_PATH, "r", encoding="utf-8") as f:
        cases = [json.loads(line) for line in f if line.strip()]

    verifier = ClaimVerifier()
    labels = ["supported", "partially_supported", "unsupported", "contradicted", "not_evaluated"]

    confusion_matrix = {gold: {pred: 0 for pred in labels} for gold in labels}
    category_breakdown = defaultdict(lambda: {"total": 0, "correct": 0, "predictions": defaultdict(int)})

    detailed_evaluations = []
    t_start = time.perf_counter()

    for c in cases:
        gold = c["support_label"]
        cat = c["category"]
        passages = [
            EvidencePassage(
                evidence_id=p["evidence_id"],
                document_id=p["document_id"],
                case_title=p.get("case_title", "Unknown Case"),
                structural_label=p.get("structural_label"),
                passage_text=p["passage_text"],
                start_char=p["start_char"],
                end_char=p["end_char"]
            )
            for p in c["supporting_passages"]
        ]

        t0 = time.perf_counter()
        res = verifier.verify_claim(c["claim_sentence"], passages)
        latency_ms = round((time.perf_counter() - t0) * 1000.0, 3)

        pred = res.status.value
        confusion_matrix[gold][pred] += 1

        category_breakdown[cat]["total"] += 1
        category_breakdown[cat]["predictions"][pred] += 1
        if gold == pred:
            category_breakdown[cat]["correct"] += 1

        detailed_evaluations.append({
            "review_id": c["review_id"],
            "query_id": c["query_id"],
            "category": cat,
            "claim_sentence": c["claim_sentence"],
            "gold_support_label": gold,
            "predicted_status": pred,
            "is_correct": (gold == pred),
            "verification_method": res.method,
            "verification_reason": res.reason,
            "unresolved_uncertainty": res.unresolved_uncertainty,
            "latency_ms": latency_ms
        })

    elapsed_total_ms = round((time.perf_counter() - t_start) * 1000.0, 2)
    total_cases = len(cases)
    total_correct = sum(1 for d in detailed_evaluations if d["is_correct"])
    overall_accuracy = round(total_correct / total_cases, 4)

    # Per-class metrics: Precision, Recall, F1
    per_class_metrics = {}
    f1_list = []
    for lbl in labels:
        tp = confusion_matrix[lbl][lbl]
        fp = sum(confusion_matrix[other][lbl] for other in labels if other != lbl)
        fn = sum(confusion_matrix[lbl][other] for other in labels if other != lbl)

        precision = round(tp / (tp + fp), 4) if (tp + fp) > 0 else 0.0
        recall = round(tp / (tp + fn), 4) if (tp + fn) > 0 else 0.0
        f1 = round(2 * precision * recall / (precision + recall), 4) if (precision + recall) > 0 else 0.0

        per_class_metrics[lbl] = {
            "gold_count": sum(confusion_matrix[lbl].values()),
            "predicted_count": sum(confusion_matrix[other][lbl] for other in labels),
            "true_positives": tp,
            "false_positives": fp,
            "false_negatives": fn,
            "precision": precision,
            "recall": recall,
            "f1_score": f1
        }
        f1_list.append(f1)

    macro_f1 = round(sum(f1_list) / len(f1_list), 4)

    # False Acceptance Rate (FAR) for contradicted & unsupported claims
    # (Contradicted or unsupported claim predicted as 'supported')
    contradicted_or_unsupported = [d for d in detailed_evaluations if d["gold_support_label"] in ["contradicted", "unsupported"]]
    false_accepts = [d for d in contradicted_or_unsupported if d["predicted_status"] == "supported"]
    far_rate = round(len(false_accepts) / len(contradicted_or_unsupported), 4) if contradicted_or_unsupported else 0.0

    # False Rejection Rate (FRR) for supported claims
    # (Supported claim predicted as 'contradicted')
    supported_claims = [d for d in detailed_evaluations if d["gold_support_label"] == "supported"]
    false_rejects = [d for d in supported_claims if d["predicted_status"] == "contradicted"]
    frr_rate = round(len(false_rejects) / len(supported_claims), 4) if supported_claims else 0.0

    # Preservation of Uncertainty
    not_evaluated_total = sum(1 for d in detailed_evaluations if d["predicted_status"] == "not_evaluated")
    not_evaluated_rate = round(not_evaluated_total / total_cases, 4)

    # Summary object
    results = {
        "benchmark_metadata": {
            "milestone": "Milestone 14 — Unseen Claim Verification Evaluation",
            "evaluation_date": "2026-10-14",
            "evaluator": "NyayaVarta ClaimVerifier (Generalization Audit)",
            "curation_status": "developer_curated",
            "total_cases_evaluated": total_cases,
            "total_categories_evaluated": len(category_breakdown),
            "evaluation_latency_ms": elapsed_total_ms
        },
        "overall_summary": {
            "accuracy": overall_accuracy,
            "macro_f1": macro_f1,
            "total_correct": total_correct,
            "total_cases": total_cases,
            "false_acceptance_rate_contradicted_unsupported": far_rate,
            "false_accepts_count": len(false_accepts),
            "false_rejection_rate_supported": frr_rate,
            "false_rejects_count": len(false_rejects),
            "not_evaluated_count": not_evaluated_total,
            "not_evaluated_rate": not_evaluated_rate
        },
        "per_class_metrics": per_class_metrics,
        "confusion_matrix": confusion_matrix,
        "category_breakdown": {
            cat: {
                "total": data["total"],
                "correct": data["correct"],
                "accuracy": round(data["correct"] / data["total"], 4),
                "predictions": dict(data["predictions"])
            }
            for cat, data in category_breakdown.items()
        },
        "safety_invariants": {
            "zero_false_acceptances_of_contradicted": len([d for d in detailed_evaluations if d["gold_support_label"] == "contradicted" and d["predicted_status"] == "supported"]) == 0,
            "zero_false_acceptances_of_unsupported": len([d for d in detailed_evaluations if d["gold_support_label"] == "unsupported" and d["predicted_status"] == "supported"]) == 0,
            "zero_false_rejections_of_supported": len(false_rejects) == 0,
            "preserves_uncertainty_on_ambiguous": all(
                d["predicted_status"] == "not_evaluated"
                for d in detailed_evaluations
                if d["category"] == "genuinely_ambiguous_uncertainty"
            )
        },
        "detailed_evaluations": detailed_evaluations
    }

    OUTPUT_RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"Results written to {OUTPUT_RESULTS_PATH}")
    print(f"\n--- MILESTONE 14 EVALUATION METRICS ---")
    print(f"Total Cases: {total_cases}")
    print(f"Accuracy: {overall_accuracy:.2%}")
    print(f"Macro F1: {macro_f1:.4f}")
    print(f"False Acceptance Rate (FAR): {far_rate:.2%} (Count: {len(false_accepts)})")
    print(f"False Rejection Rate (FRR): {frr_rate:.2%} (Count: {len(false_rejects)})")
    print(f"Not Evaluated (Uncertainty Preservation): {not_evaluated_rate:.2%} ({not_evaluated_total} cases)")

    print(f"\n--- PER-CLASS METRICS ---")
    for lbl, m in per_class_metrics.items():
        print(f"  {lbl:20s}: P={m['precision']:.2f}, R={m['recall']:.2f}, F1={m['f1_score']:.2f} (Gold={m['gold_count']})")

    print(f"\n--- CATEGORY ACCURACY ---")
    for cat, d in sorted(results["category_breakdown"].items()):
        print(f"  {cat:38s}: {d['accuracy']:.2%} ({d['correct']}/{d['total']})")


if __name__ == "__main__":
    run_evaluation()
