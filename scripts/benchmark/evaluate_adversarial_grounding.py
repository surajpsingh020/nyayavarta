"""
Adversarial Stress-Testing and Audit Runner for Proposition Grounding Gate (Milestone 5E).

Evaluates the PropositionGroundingGate against evaluation/rag/adversarial_grounding_dataset.json.
Measures:
- True Positives (Correctly Accepted Supported Cases)
- False Negatives (False Abstentions on Supported Cases)
- True Negatives (Correctly Rejected Unsupported Cases)
- False Positives (False Accepts on Unsupported/Contradictory/Adversarial Cases)
- Per-category confusion and failure breakdown
- Grounding Gate latency statistics (median, p95, max)

Outputs:
- evaluation/rag/adversarial_grounding_audit_report.json
"""
import os
import sys
import json
import time
import argparse
import statistics
from typing import Dict, Any, List

sys.path.insert(0, ".")
from services.rag.grounding_gate import PropositionGroundingGate, GroundingStatus
from services.rag.models import EvidencePassage

ADVERSARIAL_DATASET_PATH = "evaluation/rag/adversarial_grounding_dataset.json"
REPORT_OUTPUT_PATH = "evaluation/rag/adversarial_grounding_audit_report.json"


def evaluate_adversarial_grounding(
    dataset_path: str = ADVERSARIAL_DATASET_PATH,
    output_path: str = REPORT_OUTPUT_PATH
) -> Dict[str, Any]:
    print("=" * 80)
    print("NyayaVarta Milestone 5E: Adversarial Grounding Gate Audit")
    print("=" * 80)

    with open(dataset_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    gate = PropositionGroundingGate()

    total_cases = len(dataset)
    true_positives = 0
    false_negatives = 0
    true_negatives = 0
    false_positives = 0

    category_stats: Dict[str, Dict[str, Any]] = {}
    latencies: List[float] = []
    audit_records: List[Dict[str, Any]] = []

    for item in dataset:
        test_id = item["test_id"]
        category = item["category"]
        fixture_type = item["fixture_type"]
        query = item["query"]
        expected_status = item["expected_status"]
        expected_is_grounded = item["expected_is_grounded"]
        rationale = item.get("rationale", "")

        if category not in category_stats:
            category_stats[category] = {
                "total": 0,
                "expected_grounded": 0,
                "expected_ungrounded": 0,
                "actual_grounded": 0,
                "actual_ungrounded": 0,
                "correct": 0,
                "false_positive": 0,
                "false_negative": 0
            }
        category_stats[category]["total"] += 1
        if expected_is_grounded:
            category_stats[category]["expected_grounded"] += 1
        else:
            category_stats[category]["expected_ungrounded"] += 1

        passages = [
            EvidencePassage(
                evidence_id=p["evidence_id"],
                document_id=p["document_id"],
                case_title=p["case_title"],
                citation=p.get("citation"),
                passage_text=p["passage_text"],
                start_char=p["start_char"],
                end_char=p["end_char"],
                judgment_rank=idx + 1,
                judgment_score=round(1.0 - (idx * 0.1), 2),
                passage_score=round(1.0 - (idx * 0.1), 2)
            )
            for idx, p in enumerate(item["passages"])
        ]

        t0 = time.perf_counter()
        decision = gate.assess_grounding(query=query, evidence_passages=passages)
        lat = (time.perf_counter() - t0) * 1000.0
        latencies.append(decision.gate_latency_ms if decision.gate_latency_ms > 0 else lat)

        actual_is_grounded = decision.is_grounded
        actual_status = decision.status.value

        if actual_is_grounded:
            category_stats[category]["actual_grounded"] += 1
        else:
            category_stats[category]["actual_ungrounded"] += 1

        is_correct = (actual_is_grounded == expected_is_grounded)
        is_false_positive = (actual_is_grounded is True and expected_is_grounded is False)
        is_false_negative = (actual_is_grounded is False and expected_is_grounded is True)

        if expected_is_grounded:
            if actual_is_grounded:
                true_positives += 1
            else:
                false_negatives += 1
        else:
            if not actual_is_grounded:
                true_negatives += 1
            else:
                false_positives += 1

        if is_correct:
            category_stats[category]["correct"] += 1
        elif is_false_positive:
            category_stats[category]["false_positive"] += 1
        elif is_false_negative:
            category_stats[category]["false_negative"] += 1

        audit_record = {
            "test_id": test_id,
            "category": category,
            "fixture_type": fixture_type,
            "query": query,
            "expected_is_grounded": expected_is_grounded,
            "expected_status": expected_status,
            "actual_is_grounded": actual_is_grounded,
            "actual_status": actual_status,
            "decision_match": is_correct,
            "is_false_positive": is_false_positive,
            "is_false_negative": is_false_negative,
            "generation_permitted": actual_is_grounded,
            "decision_rationale": decision.rationale,
            "expected_rationale": rationale,
            "provisions_required": decision.provisions_required,
            "provisions_found": decision.provisions_found,
            "missing_provisions": decision.missing_provisions,
            "content_classifications": decision.content_classifications,
            "has_holding_or_authoritative_support": decision.has_holding_or_authoritative_support,
            "diagnostics": decision.diagnostics,
            "gate_latency_ms": decision.gate_latency_ms
        }
        audit_records.append(audit_record)

    # Compute aggregate metrics
    total_supported = true_positives + false_negatives
    total_unsupported = true_negatives + false_positives

    true_positive_rate = (true_positives / total_supported) if total_supported > 0 else 0.0
    false_abstention_rate = (false_negatives / total_supported) if total_supported > 0 else 0.0
    true_negative_rate = (true_negatives / total_unsupported) if total_unsupported > 0 else 0.0
    false_accept_rate = (false_positives / total_unsupported) if total_unsupported > 0 else 0.0
    overall_accuracy = ((true_positives + true_negatives) / total_cases) if total_cases > 0 else 0.0

    median_lat = statistics.median(latencies) if latencies else 0.0
    p95_lat = statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 20 else max(latencies or [0.0])
    max_lat = max(latencies) if latencies else 0.0

    report = {
        "benchmark_title": "NyayaVarta Milestone 5E Adversarial Grounding Gate Audit",
        "benchmark_version": "v1.0_adversarial_matrix",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "summary_counts": {
            "total_test_cases": total_cases,
            "total_supported_cases": total_supported,
            "total_unsupported_cases": total_unsupported,
            "true_positives": true_positives,
            "false_negatives": false_negatives,
            "true_negatives": true_negatives,
            "false_positives": false_positives
        },
        "performance_metrics": {
            "overall_accuracy": round(overall_accuracy, 4),
            "true_positive_rate": round(true_positive_rate, 4),
            "false_abstention_rate": round(false_abstention_rate, 4),
            "true_negative_rate": round(true_negative_rate, 4),
            "false_accept_rate": round(false_accept_rate, 4)
        },
        "latency_metrics_ms": {
            "median_latency_ms": round(median_lat, 3),
            "p95_latency_ms": round(p95_lat, 3),
            "max_latency_ms": round(max_lat, 3),
            "target_under_10ms_met": max_lat < 10.0
        },
        "category_breakdown": category_stats,
        "audit_records": audit_records
    }

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print("\n=== ADVERSARIAL AUDIT SUMMARY ===")
    print(f"Total Test Cases: {total_cases} ({total_supported} supported, {total_unsupported} unsupported)")
    print(f"True Positives (Correctly Accepted Supported):    {true_positives}/{total_supported} ({true_positive_rate*100:.1f}%)")
    print(f"False Negatives (False Abstentions on Supported):  {false_negatives}/{total_supported} ({false_abstention_rate*100:.1f}%)")
    print(f"True Negatives (Correctly Rejected Unsupported):  {true_negatives}/{total_unsupported} ({true_negative_rate*100:.1f}%)")
    print(f"False Positives (False Accepts on Unsupported):   {false_positives}/{total_unsupported} ({false_accept_rate*100:.1f}%)")
    print(f"Overall Accuracy:                                 {overall_accuracy*100:.1f}%")
    print(f"Median Gate Latency:                              {median_lat:.3f} ms (p95: {p95_lat:.3f} ms, max: {max_lat:.3f} ms)")
    print(f"Report written to: {output_path}")

    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate adversarial grounding.")
    parser.add_argument("--dataset", type=str, default=ADVERSARIAL_DATASET_PATH)
    parser.add_argument("--output", type=str, default=REPORT_OUTPUT_PATH)
    args = parser.parse_args()

    evaluate_adversarial_grounding(dataset_path=args.dataset, output_path=args.output)
