"""
Evaluation Script for Milestone 11 Task 6:
Evaluates EntityResolverV2 on `evaluation/citations/milestone11_citation_gold.json` (110 records).

Calculates:
- Resolution Precision (cross-document)
- Resolution Recall (cross-document)
- Resolution F1
- Target-ID Accuracy
- False Cross-Document Match Rate
- Self-Citation Rejection Accuracy
- Ambiguity Detection Precision / Recall
- Categorical Breakdown
"""
import os
import sys
sys.path.insert(0, os.path.abspath("."))
import json
from collections import defaultdict, Counter

from services.extraction.entity_resolver_v2 import EntityResolverV2
from services.extraction.citation_normalizer import CitationNormalizer

GOLD_PATH = "evaluation/citations/milestone11_citation_gold.json"
RESULTS_PATH = "evaluation/citations/milestone11_citation_eval_results.json"


def evaluate_resolution():
    print("=== Milestone 11: Citation Resolution Evaluation (110 Mentions) ===")
    with open(GOLD_PATH, "r", encoding="utf-8") as f:
        gold_data = json.load(f)

    resolver = EntityResolverV2()
    normalizer = CitationNormalizer()

    total = len(gold_data)
    tp_cross = 0
    fp_cross = 0
    fn_cross = 0

    gold_cross_count = 0
    pred_cross_count = 0

    target_id_correct = 0
    target_id_evaluated = 0

    gold_self_count = 0
    correct_self_flags = 0

    gold_ambig_count = 0
    tp_ambig = 0
    fp_ambig = 0

    gold_unresolved_count = 0
    tp_unresolved = 0

    category_results = defaultdict(lambda: {"total": 0, "correct_status": 0, "correct_target": 0, "false_cross": 0})
    method_counts = Counter()

    evaluated_records = []

    for item in gold_data:
        gold_status = item["gold_resolution_status"]
        gold_target = item["gold_target_document_id"]
        gold_self = item["gold_is_self_citation"]
        cat = item["test_category"]

        # Run normalization if applicable
        raw = item["raw_text"]
        norm_rec = normalizer.normalize(raw)
        norm_cite = norm_rec.normalized_citation if norm_rec.parsing_status == "valid" else raw

        mention_dict = {
            "source_doc_id": item["source_doc_id"],
            "citation_type": item["citation_type"],
            "raw_text": raw,
            "normalized_citation": norm_cite,
            "mention_context": item.get("mention_context", ""),
            "components": item.get("components", {})
        }

        pred = resolver.resolve_citation(mention_dict)

        pred_status = pred["resolution_status"]
        pred_target = pred["resolved_document_id"]
        pred_self = pred.get("is_self_citation", False)
        method = pred.get("match_method", "unknown")
        method_counts[method] += 1

        is_gold_cross = (gold_status == "resolved" and not gold_self)
        is_pred_cross = (pred_status == "resolved" and not pred_self)

        category_results[cat]["total"] += 1

        # Check self-citation handling
        if gold_self:
            gold_self_count += 1
            if pred_self and pred_status == "resolved" and pred_target == gold_target:
                correct_self_flags += 1

        # Check ambiguous handling
        if gold_status == "ambiguous":
            gold_ambig_count += 1
            if pred_status == "ambiguous":
                tp_ambig += 1
        elif pred_status == "ambiguous":
            fp_ambig += 1

        # Check unresolved handling
        if gold_status == "unresolved":
            gold_unresolved_count += 1
            if pred_status == "unresolved":
                tp_unresolved += 1

        # Check cross-doc resolution
        if is_gold_cross:
            gold_cross_count += 1
            if is_pred_cross and pred_target == gold_target:
                tp_cross += 1
            else:
                fn_cross += 1

        if is_pred_cross:
            pred_cross_count += 1
            if not is_gold_cross or pred_target != gold_target:
                fp_cross += 1
                category_results[cat]["false_cross"] += 1

        # Target ID accuracy across all resolved
        if gold_status == "resolved" and pred_status == "resolved":
            target_id_evaluated += 1
            if pred_target == gold_target:
                target_id_correct += 1
                category_results[cat]["correct_target"] += 1

        if pred_status == gold_status:
            category_results[cat]["correct_status"] += 1

        evaluated_records.append({
            "mention_id": item["mention_id"],
            "raw_text": raw,
            "category": cat,
            "gold_status": gold_status,
            "gold_target": gold_target,
            "gold_self": gold_self,
            "pred_status": pred_status,
            "pred_target": pred_target,
            "pred_self": pred_self,
            "match_method": method,
            "is_correct_status": (pred_status == gold_status),
            "is_correct_target": (pred_target == gold_target) if gold_target else (pred_target is None)
        })

    # Metrics calculation
    precision = (tp_cross / pred_cross_count) if pred_cross_count > 0 else 0.0
    recall = (tp_cross / gold_cross_count) if gold_cross_count > 0 else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

    target_accuracy = (target_id_correct / target_id_evaluated) if target_id_evaluated > 0 else 0.0
    false_cross_rate = (fp_cross / (total - gold_cross_count)) if (total - gold_cross_count) > 0 else 0.0
    self_rejection_acc = (correct_self_flags / gold_self_count) if gold_self_count > 0 else 0.0
    ambig_precision = (tp_ambig / (tp_ambig + fp_ambig)) if (tp_ambig + fp_ambig) > 0 else 0.0
    ambig_recall = (tp_ambig / gold_ambig_count) if gold_ambig_count > 0 else 0.0

    overall_status_accuracy = sum(1 for r in evaluated_records if r["is_correct_status"]) / total

    print("\n--- Aggregate Performance Metrics ---")
    print(f"Total Evaluated Mentions: {total}")
    print(f"Overall Status Accuracy: {overall_status_accuracy*100:.2f}% ({sum(1 for r in evaluated_records if r['is_correct_status'])}/{total})")
    print(f"Cross-Document Precision: {precision*100:.2f}% ({tp_cross}/{pred_cross_count})")
    print(f"Cross-Document Recall: {recall*100:.2f}% ({tp_cross}/{gold_cross_count})")
    print(f"Cross-Document F1: {f1:.4f}")
    print(f"Target-ID Accuracy: {target_accuracy*100:.2f}% ({target_id_correct}/{target_id_evaluated})")
    print(f"False Cross-Document Match Rate: {false_cross_rate*100:.2f}% ({fp_cross}/{total - gold_cross_count})")
    print(f"Self-Citation Rejection Accuracy: {self_rejection_acc*100:.2f}% ({correct_self_flags}/{gold_self_count})")
    print(f"Ambiguity Detection (P / R): {ambig_precision*100:.2f}% / {ambig_recall*100:.2f}%")

    print("\n--- Results by Category ---")
    for cat, d in sorted(category_results.items()):
        tot = d["total"]
        st = d["correct_status"]
        fc = d["false_cross"]
        print(f"  {cat:32}: Status Acc = {st/tot*100:5.1f}% ({st}/{tot}), False Cross = {fc}")

    report = {
        "evaluation_name": "Milestone 11 Gold Citation Resolution Audit",
        "dataset_path": GOLD_PATH,
        "total_mentions_evaluated": total,
        "metrics": {
            "overall_status_accuracy": round(overall_status_accuracy, 4),
            "cross_document_precision": round(precision, 4),
            "cross_document_recall": round(recall, 4),
            "cross_document_f1": round(f1, 4),
            "target_id_accuracy": round(target_accuracy, 4),
            "false_cross_document_rate": round(false_cross_rate, 4),
            "self_citation_rejection_accuracy": round(self_rejection_acc, 4),
            "ambiguity_precision": round(ambig_precision, 4),
            "ambiguity_recall": round(ambig_recall, 4)
        },
        "breakdown_by_category": dict(category_results),
        "method_distribution": dict(method_counts)
    }

    with open(RESULTS_PATH, "w", encoding="utf-8") as f_out:
        json.dump(report, f_out, indent=2)
    print(f"\nSaved evaluation results to {RESULTS_PATH}")
    return report

if __name__ == "__main__":
    evaluate_resolution()
