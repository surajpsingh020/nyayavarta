"""Evaluation runner for NyayaVarta Milestone 16 — Independent Legal Review.

Validates reviewer packs, ingests blinded reviewer annotations, enforces
strict schema and label checks, and computes:
- 5x5 Confusion Matrix (Predicted vs Reviewer / Predicted vs Ground Truth)
- Disaggregated False Acceptance Rates (FAR)
- Supported-class Precision, Recall, and F1
- Answer-level safe aggregation audit
- Inter-annotator agreement (Cohen's Kappa / Fleiss' Kappa) if multiple reviewers exist.
"""

import argparse
import json
import logging
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

VALID_LABELS = {
    "supported",
    "partially_supported",
    "unsupported",
    "contradicted",
    "not_evaluated",
}

VALID_CONFIDENCE = {"high", "medium", "low"}


def validate_reviewer_pack(
    pack_path: Path,
    mapping_path: Optional[Path] = None
) -> Tuple[bool, List[str]]:
    """Validate the integrity and blinding of the reviewer pack."""
    errors = []
    if not pack_path.exists():
        return False, [f"Pack file does not exist: {pack_path}"]

    lines = [line.strip() for line in pack_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not lines:
        return False, ["Pack file is empty."]

    seen_ids = set()
    for idx, line in enumerate(lines, 1):
        try:
            item = json.loads(line)
        except json.JSONDecodeError as e:
            errors.append(f"Line {idx}: Invalid JSON - {e}")
            continue

        case_id = item.get("case_id")
        if not case_id:
            errors.append(f"Line {idx}: Missing 'case_id'")
        elif case_id in seen_ids:
            errors.append(f"Line {idx}: Duplicate case_id '{case_id}'")
        else:
            seen_ids.add(case_id)

        # Check required fields
        required_fields = ["case_id", "generated_claim", "exact_source_passage", "surrounding_context"]
        for f in required_fields:
            if f not in item or not isinstance(item[f], str) or not item[f].strip():
                errors.append(f"Line {idx} ({case_id}): Missing or empty required field '{f}'")

        # Verify blinding: No internal gold labels or system predictions should be present
        forbidden_fields = ["gold_status", "gold_support_label", "predicted_status", "system_predicted_status", "original_case_id", "original_review_id", "system_verification_method", "verifier_rationale"]
        for f in forbidden_fields:
            if f in item and item[f] is not None:
                errors.append(f"Line {idx} ({case_id}): Blinding violation! Found '{f}'")

        # Verify reviewer fields are initialized to null or missing
        if item.get("reviewer_label") is not None:
            errors.append(f"Line {idx} ({case_id}): reviewer_label must be null in uncompleted pack")

    if mapping_path and mapping_path.exists():
        try:
            mapping_data = json.loads(mapping_path.read_text(encoding="utf-8"))
            mapping_cases = mapping_data.get("cases", mapping_data)
            if set(mapping_cases.keys()) != seen_ids:
                errors.append(f"ID mismatch between pack ({len(seen_ids)}) and mapping ({len(mapping_cases)})")
        except Exception as e:
            errors.append(f"Failed to read mapping file: {e}")

    return len(errors) == 0, errors


def load_and_validate_review_file(
    review_path: Path,
    expected_case_ids: set
) -> Tuple[Optional[List[Dict[str, Any]]], List[str]]:
    """Load and validate an annotated reviewer submission."""
    errors = []
    if not review_path.exists():
        return None, [f"Review file does not exist: {review_path}"]

    lines = [line.strip() for line in review_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not lines:
        return None, [f"Review file is empty: {review_path}"]

    reviews = []
    seen_ids = set()
    for idx, line in enumerate(lines, 1):
        try:
            item = json.loads(line)
        except json.JSONDecodeError as e:
            errors.append(f"Line {idx}: Invalid JSON - {e}")
            continue

        case_id = item.get("case_id")
        if not case_id:
            errors.append(f"Line {idx}: Missing 'case_id'")
            continue

        if case_id not in expected_case_ids:
            errors.append(f"Line {idx}: Unknown case_id '{case_id}' not in evaluation pack")
            continue

        if case_id in seen_ids:
            errors.append(f"Line {idx}: Duplicate entry for case_id '{case_id}'")
            continue
        seen_ids.add(case_id)

        label = item.get("reviewer_label")
        if not label:
            errors.append(f"Line {idx} ({case_id}): Missing 'reviewer_label'")
        elif label.lower() not in VALID_LABELS:
            errors.append(f"Line {idx} ({case_id}): Invalid label '{label}'. Must be one of {sorted(list(VALID_LABELS))}")
        else:
            item["reviewer_label"] = label.lower()

        rationale = item.get("reviewer_rationale")
        if not rationale or len(str(rationale).strip()) < 10:
            errors.append(f"Line {idx} ({case_id}): Missing or insufficient 'reviewer_rationale' (min 10 chars)")

        conf = item.get("confidence", "high")
        if conf and str(conf).lower() not in VALID_CONFIDENCE:
            errors.append(f"Line {idx} ({case_id}): Invalid confidence '{conf}'")

        reviews.append(item)

    if errors:
        return None, errors
    return reviews, []


def compute_confusion_matrix(
    y_true: List[str],
    y_pred: List[str],
    labels: List[str]
) -> Dict[str, Dict[str, int]]:
    """Compute 2D confusion matrix dict[true_label][pred_label]."""
    matrix = {t: {p: 0 for p in labels} for t in labels}
    for t, p in zip(y_true, y_pred):
        if t in matrix and p in matrix[t]:
            matrix[t][p] += 1
    return matrix


def compute_metrics(
    y_true: List[str],
    y_pred: List[str],
    labels: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Compute per-class precision, recall, F1, and disaggregated FARs."""
    if labels is None:
        labels = sorted(list(VALID_LABELS))

    cm = compute_confusion_matrix(y_true, y_pred, labels)
    per_class = {}

    for label in labels:
        tp = cm[label][label]
        fn = sum(cm[label][p] for p in labels if p != label)
        fp = sum(cm[t][label] for t in labels if t != label)
        tn = sum(cm[t][p] for t in labels for p in labels if t != label and p != label)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

        per_class[label] = {
            "true_count": tp + fn,
            "predicted_count": tp + fp,
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
        }

    # Disaggregated False Acceptance Rates (FAR)
    # FAR = Non-supported true class predicted as 'supported' / Total true class
    contra_total = per_class["contradicted"]["true_count"]
    contra_fa = cm["contradicted"]["supported"]
    contra_far = (contra_fa / contra_total) if contra_total > 0 else 0.0

    unsupp_total = per_class["unsupported"]["true_count"]
    unsupp_fa = cm["unsupported"]["supported"]
    unsupp_far = (unsupp_fa / unsupp_total) if unsupp_total > 0 else 0.0

    partial_total = per_class["partially_supported"]["true_count"]
    partial_fa = cm["partially_supported"]["supported"]
    partial_far = (partial_fa / partial_total) if partial_total > 0 else 0.0

    non_supported_total = contra_total + unsupp_total + partial_total
    non_supported_fa = contra_fa + unsupp_fa + partial_fa
    overall_non_supp_far = (non_supported_fa / non_supported_total) if non_supported_total > 0 else 0.0

    # Overall accuracy
    correct = sum(1 for t, p in zip(y_true, y_pred) if t == p)
    total = len(y_true)
    accuracy = (correct / total) if total > 0 else 0.0

    return {
        "total_evaluations": total,
        "overall_accuracy": round(accuracy, 4),
        "per_class_metrics": per_class,
        "disaggregated_far": {
            "contradiction_far": round(contra_far, 4),
            "contradiction_false_accepts": contra_fa,
            "contradiction_total": contra_total,
            "unsupported_far": round(unsupp_far, 4),
            "unsupported_false_accepts": unsupp_fa,
            "unsupported_total": unsupp_total,
            "partially_supported_far": round(partial_far, 4),
            "partially_supported_false_accepts": partial_fa,
            "partially_supported_total": partial_total,
            "overall_non_supported_far": round(overall_non_supp_far, 4),
            "total_non_supported_false_accepts": non_supported_fa,
            "total_non_supported": non_supported_total,
        },
        "confusion_matrix": cm,
    }


def compute_cohens_kappa(rater1: List[str], rater2: List[str], labels: List[str]) -> float:
    """Compute Cohen's Kappa between two raters."""
    if len(rater1) != len(rater2) or not rater1:
        return 0.0

    n = len(rater1)
    cm = compute_confusion_matrix(rater1, rater2, labels)

    po = sum(cm[l][l] for l in labels) / n

    pe = sum(
        (sum(cm[l][j] for j in labels) * sum(cm[i][l] for i in labels))
        for l in labels
    ) / (n * n)

    if math.isclose(pe, 1.0):
        return 1.0
    return (po - pe) / (1.0 - pe)


def evaluate_pack_against_mapping(
    mapping_path: Path,
    reviewer_file: Optional[Path] = None,
    second_reviewer_file: Optional[Path] = None,
) -> Dict[str, Any]:
    """Execute complete Milestone 16 evaluation."""
    mapping_data = json.loads(mapping_path.read_text(encoding="utf-8"))
    cases = mapping_data.get("cases", mapping_data)
    expected_case_ids = set(cases.keys())

    # 1. Baseline internal performance (System predicted vs Gold truth)
    gold_labels = [
        cases[cid].get("gold_support_label", cases[cid].get("gold_status"))
        for cid in sorted(expected_case_ids)
    ]
    pred_labels = [
        cases[cid].get("system_predicted_status", cases[cid].get("predicted_status"))
        for cid in sorted(expected_case_ids)
    ]

    internal_metrics = compute_metrics(gold_labels, pred_labels)

    # 2. Answer-level aggregation check
    answer_aggregation_checks = []
    safe_promotions_violated = 0
    for cid in sorted(expected_case_ids):
        case_info = cases[cid]
        c_pred = case_info.get("system_predicted_status", case_info.get("predicted_status"))
        c_gold = case_info.get("gold_support_label", case_info.get("gold_status"))

        # If a claim is not supported, it must never receive a 'verified_supported' answer status
        # Simulate an answer containing this single claim
        would_be_verified = (c_pred == "supported")
        should_be_verified = (c_gold == "supported")

        violation = (would_be_verified and not should_be_verified)
        if violation:
            safe_promotions_violated += 1

        answer_aggregation_checks.append({
            "case_id": cid,
            "gold_status": c_gold,
            "predicted_status": c_pred,
            "answer_status_compliant": not violation,
        })

    report: Dict[str, Any] = {
        "milestone": "Milestone 16 - Independent Legal Review & External Validation",
        "pack_case_count": len(expected_case_ids),
        "system_vs_gold_benchmark": {
            "metrics": internal_metrics,
            "answer_level_safety": {
                "total_cases_audited": len(expected_case_ids),
                "safe_promotions_violated": safe_promotions_violated,
                "safety_compliance_rate": round(1.0 - (safe_promotions_violated / len(expected_case_ids)), 4),
            },
        },
        "review_status": "PENDING_EXTERNAL_REVIEW",
        "external_review_analysis": None,
    }

    # 3. Process primary reviewer file if provided
    if reviewer_file and reviewer_file.exists():
        reviews, errors = load_and_validate_review_file(reviewer_file, expected_case_ids)
        if errors:
            report["external_review_analysis"] = {
                "status": "VALIDATION_FAILED",
                "validation_errors": errors,
            }
            return report

        reviews_by_id = {r["case_id"]: r for r in reviews}
        if len(reviews_by_id) == len(expected_case_ids):
            rev_labels = [reviews_by_id[cid]["reviewer_label"] for cid in sorted(expected_case_ids)]
            reviewer_vs_pred = compute_metrics(rev_labels, pred_labels)
            reviewer_vs_gold = compute_metrics(gold_labels, rev_labels)

            analysis: Dict[str, Any] = {
                "status": "COMPLETED",
                "reviewer_id": reviews[0].get("reviewer_id", "external_reviewer"),
                "total_annotated": len(reviews),
                "system_vs_reviewer": reviewer_vs_pred,
                "reviewer_vs_gold": reviewer_vs_gold,
            }

            # If second reviewer provided, compute inter-annotator agreement
            if second_reviewer_file and second_reviewer_file.exists():
                reviews2, errors2 = load_and_validate_review_file(second_reviewer_file, expected_case_ids)
                if not errors2 and len(reviews2) == len(expected_case_ids):
                    reviews2_by_id = {r["case_id"]: r for r in reviews2}
                    rev2_labels = [reviews2_by_id[cid]["reviewer_label"] for cid in sorted(expected_case_ids)]
                    kappa = compute_cohens_kappa(rev_labels, rev2_labels, sorted(list(VALID_LABELS)))
                    raw_agree = sum(1 for a, b in zip(rev_labels, rev2_labels) if a == b) / len(rev_labels)
                    analysis["inter_annotator_agreement"] = {
                        "reviewer1_id": reviews[0].get("reviewer_id", "REV_1"),
                        "reviewer2_id": reviews2[0].get("reviewer_id", "REV_2"),
                        "raw_agreement": round(raw_agree, 4),
                        "cohens_kappa": round(kappa, 4),
                    }

            report["review_status"] = "REVIEW_RECEIVED"
            report["external_review_analysis"] = analysis
        else:
            report["review_status"] = "PARTIALLY_ANNOTATED"
            report["external_review_analysis"] = {
                "status": "INCOMPLETE",
                "annotated_count": len(reviews_by_id),
                "expected_count": len(expected_case_ids),
            }

    return report


def main():
    parser = argparse.ArgumentParser(description="Milestone 16 Independent Legal Review Evaluation")
    parser.add_argument("--pack-file", type=Path, default=Path("evaluation/rag/milestone16_reviewer_pack.jsonl"), help="Path to reviewer pack JSONL")
    parser.add_argument("--mapping-file", type=Path, default=Path("evaluation/rag/milestone16_reviewer_mapping.json"), help="Path to secret mapping JSON")
    parser.add_argument("--review-file", type=Path, default=None, help="Path to completed reviewer JSONL")
    parser.add_argument("--second-reviewer-file", type=Path, default=None, help="Path to second reviewer JSONL for agreement calculation")
    parser.add_argument("--output-file", type=Path, default=None, help="Path to output results JSON")
    parser.add_argument("--validate-pack", action="store_true", help="Run strict schema and blinding validation on the reviewer pack")

    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if args.validate_pack:
        valid, errors = validate_reviewer_pack(args.pack_file, args.mapping_file)
        if not valid:
            logger.error("Reviewer pack validation FAILED:")
            for e in errors:
                logger.error(f"  - {e}")
            sys.exit(1)
        logger.info("Reviewer pack validation PASSED successfully. Blinding and schema verified.")

    result = evaluate_pack_against_mapping(
        mapping_path=args.mapping_file,
        reviewer_file=args.review_file,
        second_reviewer_file=args.second_reviewer_file,
    )

    if args.output_file:
        args.output_file.parent.mkdir(parents=True, exist_ok=True)
        args.output_file.write_text(json.dumps(result, indent=2), encoding="utf-8")
        logger.info(f"Evaluation report written to {args.output_file}")
    else:
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
