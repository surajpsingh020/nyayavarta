"""
Evaluation Script for Milestone 11 Task 7:
Evaluates StatuteResolverV2 on `evaluation/statutes/milestone11_statute_gold.json` (60 records).

Calculates:
- Correct governing-Act assignments
- Incorrect assignments (fabrications or wrong statute)
- Correctly unresolved references
- False inheritance rate
- Categorical and method-based breakdown
"""
import os
import sys
sys.path.insert(0, os.path.abspath("."))
import json
from collections import defaultdict, Counter

from services.extraction.statute_extractor import StatuteExtractor
from services.extraction.statute_resolver_v2 import StatuteResolverV2

GOLD_PATH = "evaluation/statutes/milestone11_statute_gold.json"
RESULTS_PATH = "evaluation/statutes/milestone11_statute_eval_results.json"


def evaluate_statute_attribution():
    print("=== Milestone 11: Statutory Attribution Evaluation (60 Sections) ===")
    with open(GOLD_PATH, "r", encoding="utf-8") as f:
        gold_data = json.load(f)

    extractor = StatuteExtractor()
    resolver = StatuteResolverV2()

    total = len(gold_data)
    correct_act_assignments = 0
    incorrect_act_assignments = 0
    correctly_unresolved = 0
    false_inheritances = 0

    category_results = defaultdict(lambda: {"total": 0, "correct_act": 0, "correct_status": 0, "false_inheritance": 0})
    method_counts = Counter()

    evaluated_records = []

    for item in gold_data:
        text = item["sample_document_text"]
        gold_act = item["gold_governing_statute"]
        gold_atype = item["gold_attribution_type"]
        cat = item["test_category"]

        # Run section extraction and statute resolution on the sample text
        raw_secs = resolver.extract_sections_v2(text, "eval_doc")
        resolved_secs = resolver.resolve_document_statutes(text, "eval_doc", extracted_sections=raw_secs)

        category_results[cat]["total"] += 1

        # Match the target section in resolved_secs
        matched_sec = None
        for s in resolved_secs:
            if s["components"]["section_numbers"] == item["section_number"]:
                matched_sec = s
                break
        if not matched_sec and resolved_secs:
            matched_sec = resolved_secs[0]

        pred_act = matched_sec["components"].get("governing_statute") if matched_sec else None
        pred_atype = matched_sec.get("attribution_type", "unresolved") if matched_sec else "unresolved"
        method_counts[pred_atype] += 1

        is_act_correct = (pred_act == gold_act)
        is_status_correct = (pred_atype == gold_atype)

        if gold_act is not None:
            if is_act_correct:
                correct_act_assignments += 1
                category_results[cat]["correct_act"] += 1
            else:
                incorrect_act_assignments += 1
        else:
            # Gold has no Act (ambiguous or unresolved)
            if pred_act is None:
                correctly_unresolved += 1
                category_results[cat]["correct_act"] += 1
            else:
                # Falsely assigned an Act!
                incorrect_act_assignments += 1
                if pred_atype == "inherited":
                    false_inheritances += 1
                    category_results[cat]["false_inheritance"] += 1

        if is_status_correct:
            category_results[cat]["correct_status"] += 1

        evaluated_records.append({
            "mention_id": item["mention_id"],
            "raw_text": item["raw_text"],
            "category": cat,
            "gold_act": gold_act,
            "pred_act": pred_act,
            "gold_type": gold_atype,
            "pred_type": pred_atype,
            "is_act_correct": is_act_correct,
            "is_status_correct": is_status_correct
        })

    # Metrics calculation
    total_with_act = sum(1 for r in gold_data if r["gold_governing_statute"] is not None)
    total_without_act = sum(1 for r in gold_data if r["gold_governing_statute"] is None)

    act_assignment_accuracy = correct_act_assignments / total_with_act if total_with_act > 0 else 0.0
    unresolved_accuracy = correctly_unresolved / total_without_act if total_without_act > 0 else 0.0
    false_inheritance_rate = false_inheritances / total_without_act if total_without_act > 0 else 0.0
    overall_accuracy = sum(1 for r in evaluated_records if r["is_act_correct"]) / total

    print("\n--- Aggregate Statutory Attribution Metrics ---")
    print(f"Total Evaluated Mentions: {total}")
    print(f"Overall Act Assignment Accuracy: {overall_accuracy*100:.2f}% ({sum(1 for r in evaluated_records if r['is_act_correct'])}/{total})")
    print(f"Grounding Accuracy (where Act exists): {act_assignment_accuracy*100:.2f}% ({correct_act_assignments}/{total_with_act})")
    print(f"Correctly Unresolved / Ambiguous Accuracy: {unresolved_accuracy*100:.2f}% ({correctly_unresolved}/{total_without_act})")
    print(f"False Inheritance Rate: {false_inheritance_rate*100:.2f}% ({false_inheritances}/{total_without_act})")
    print(f"Incorrect / Fabricated Assignments: {incorrect_act_assignments}")

    print("\n--- Results by Category ---")
    for cat, d in sorted(category_results.items()):
        tot = d["total"]
        ca = d["correct_act"]
        cs = d["correct_status"]
        fi = d["false_inheritance"]
        print(f"  {cat:32}: Act Acc = {ca/tot*100:5.1f}% ({ca}/{tot}), Status Acc = {cs/tot*100:5.1f}%, False Inherit = {fi}")

    report = {
        "evaluation_name": "Milestone 11 Gold Statutory Attribution Audit",
        "dataset_path": GOLD_PATH,
        "total_mentions_evaluated": total,
        "metrics": {
            "overall_act_assignment_accuracy": round(overall_accuracy, 4),
            "governing_act_accuracy": round(act_assignment_accuracy, 4),
            "correctly_unresolved_accuracy": round(unresolved_accuracy, 4),
            "false_inheritance_rate": round(false_inheritance_rate, 4),
            "incorrect_assignments_count": incorrect_act_assignments,
            "false_inheritances_count": false_inheritances
        },
        "breakdown_by_category": dict(category_results),
        "method_distribution": dict(method_counts)
    }

    with open(RESULTS_PATH, "w", encoding="utf-8") as f_out:
        json.dump(report, f_out, indent=2)
    print(f"\nSaved statutory evaluation results to {RESULTS_PATH}")
    return report

if __name__ == "__main__":
    evaluate_statute_attribution()
