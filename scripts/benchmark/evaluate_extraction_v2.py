"""
Evaluation Script for Legal Citation & Entity Resolution (Milestone 4A.1).
Audits and evaluates extraction and resolution against both baseline v1 and corrected v2 benchmarks.

Key features:
- Complete 3x3 confusion matrix (resolved, ambiguous, unresolved)
- Strict separation between status correctness and target document ID correctness
- Per-class Precision, Recall, and F1
- Resolved-link precision and recall
- Target-document-ID accuracy (strict ID verification)
- Cross-document vs self-citation resolution breakdown
- Discrepancy diagnosis report
"""
import os
import json
import re
from typing import Dict, Any, List, Tuple

from services.extraction.citation_extractor import CitationExtractor
from services.extraction.entity_resolver import EntityResolver

BENCHMARK_V1 = "evaluation/citations/annotated_citations_sample_v1.json"
BENCHMARK_V2 = "evaluation/citations/annotated_citations_sample_v2.json"
OUT_JSON = "evaluation/citations/extraction_evaluation_v2.json"


def normalize_text(t: str) -> str:
    """Normalize whitespace and punctuation for fuzzy matching evaluation."""
    t = re.sub(r'[^\w\s]', '', t.lower())
    return re.sub(r'\s+', ' ', t).strip()


def run_evaluation(benchmark_path: str, is_v2: bool = False) -> Dict[str, Any]:
    with open(benchmark_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    samples = data["samples"] if is_v2 else data

    extractor = CitationExtractor()
    resolver = EntityResolver()

    total_gold_citations = 0
    total_extracted_citations = 0
    true_positives = 0
    false_positives = 0
    false_negatives = 0

    type_metrics = {}

    # 3x3 Confusion matrix: confusion[gold_status][pred_status]
    classes = ["resolved", "ambiguous", "unresolved"]
    confusion = {g: {p: 0 for p in classes} for g in classes}

    # Resolution target accuracy tracking
    pred_resolved_total = 0
    pred_resolved_correct_target = 0
    both_resolved_count = 0
    both_resolved_correct_target = 0

    self_citations_resolved_pred = 0
    cross_doc_resolved_pred = 0

    detailed_records = []

    for sample in samples:
        doc_id = sample["source_doc_id"]
        text_segment = sample["text_segment"]
        gold_citations = sample["gold_citations"]

        extracted = extractor.extract_all(text_segment, doc_id)

        gold_matched = [False] * len(gold_citations)
        extracted_matched = [False] * len(extracted)

        # Greedy match extracted to gold
        for ext_idx, ext_cite in enumerate(extracted):
            ext_raw_norm = normalize_text(ext_cite["raw_text"])

            best_match_idx = None
            for g_idx, g_cite in enumerate(gold_citations):
                if gold_matched[g_idx]:
                    continue
                g_raw_norm = normalize_text(g_cite["raw_text"])

                if ext_raw_norm == g_raw_norm or ext_raw_norm in g_raw_norm or g_raw_norm in ext_raw_norm:
                    best_match_idx = g_idx
                    break

            if best_match_idx is not None:
                gold_matched[best_match_idx] = True
                extracted_matched[ext_idx] = True
                true_positives += 1

                g_cite = gold_citations[best_match_idx]
                c_type = g_cite["citation_type"]
                if c_type not in type_metrics:
                    type_metrics[c_type] = {"tp": 0, "fp": 0, "fn": 0}
                type_metrics[c_type]["tp"] += 1

                # Resolution evaluation
                res = resolver.resolve_citation(ext_cite)
                pred_status = res["resolution_status"]
                gold_status = g_cite["gold_resolution"]

                confusion[gold_status][pred_status] += 1

                pred_target = res.get("resolved_document_id")
                gold_target = g_cite.get("target_doc_id")

                target_matches = False
                if pred_status == "resolved":
                    pred_resolved_total += 1
                    if res.get("is_self_citation"):
                        self_citations_resolved_pred += 1
                    else:
                        cross_doc_resolved_pred += 1

                    if pred_target == gold_target and gold_target is not None:
                        pred_resolved_correct_target += 1
                        target_matches = True

                if gold_status == "resolved" and pred_status == "resolved":
                    both_resolved_count += 1
                    if pred_target == gold_target:
                        both_resolved_correct_target += 1

                detailed_records.append({
                    "sample_id": sample["sample_id"],
                    "source_doc_id": doc_id,
                    "raw_text": ext_cite["raw_text"],
                    "citation_type": c_type,
                    "gold_status": gold_status,
                    "pred_status": pred_status,
                    "status_correct": (gold_status == pred_status),
                    "gold_target_doc_id": gold_target,
                    "pred_resolved_doc_id": pred_target,
                    "target_id_correct": (pred_target == gold_target),
                    "match_method": res.get("match_method"),
                    "confidence_score": res.get("confidence_score"),
                    "is_self_citation": res.get("is_self_citation")
                })
            else:
                false_positives += 1
                c_type = ext_cite.get("citation_type", "unknown")
                if c_type not in type_metrics:
                    type_metrics[c_type] = {"tp": 0, "fp": 0, "fn": 0}
                type_metrics[c_type]["fp"] += 1

        for g_idx, g_cite in enumerate(gold_citations):
            if not gold_matched[g_idx]:
                false_negatives += 1
                c_type = g_cite["citation_type"]
                if c_type not in type_metrics:
                    type_metrics[c_type] = {"tp": 0, "fp": 0, "fn": 0}
                type_metrics[c_type]["fn"] += 1

        total_gold_citations += len(gold_citations)
        total_extracted_citations += len(extracted)

    # Calculate metrics
    precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
    recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

    # Per-class resolution metrics
    per_class = {}
    total_evaluated_mentions = sum(sum(confusion[g].values()) for g in classes)
    total_correct_status = sum(confusion[c][c] for c in classes)

    for c in classes:
        tp_c = confusion[c][c]
        fp_c = sum(confusion[other][c] for other in classes if other != c)
        fn_c = sum(confusion[c][other] for other in classes if other != c)
        p_c = tp_c / (tp_c + fp_c) if (tp_c + fp_c) > 0 else 0
        r_c = tp_c / (tp_c + fn_c) if (tp_c + fn_c) > 0 else 0
        f1_c = (2 * p_c * r_c) / (p_c + r_c) if (p_c + r_c) > 0 else 0
        per_class[c] = {
            "gold_count": tp_c + fn_c,
            "pred_count": tp_c + fp_c,
            "true_positives": tp_c,
            "false_positives": fp_c,
            "false_negatives": fn_c,
            "precision": round(p_c, 4),
            "recall": round(r_c, 4),
            "f1": round(f1_c, 4)
        }

    status_accuracy = total_correct_status / total_evaluated_mentions if total_evaluated_mentions > 0 else 0
    target_id_acc_on_pred = pred_resolved_correct_target / pred_resolved_total if pred_resolved_total > 0 else 0
    target_id_acc_on_both_resolved = both_resolved_correct_target / both_resolved_count if both_resolved_count > 0 else 0

    return {
        "benchmark_file": os.path.basename(benchmark_path),
        "benchmark_type": "corrected_v2" if is_v2 else "baseline_v1",
        "citation_extraction": {
            "total_gold": total_gold_citations,
            "total_extracted": total_extracted_citations,
            "true_positives": true_positives,
            "false_positives": false_positives,
            "false_negatives": false_negatives,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4)
        },
        "entity_resolution": {
            "total_evaluated_mentions": total_evaluated_mentions,
            "status_accuracy": round(status_accuracy, 4),
            "confusion_matrix": confusion,
            "per_class_metrics": per_class,
            "resolved_link_precision": per_class["resolved"]["precision"],
            "resolved_link_recall": per_class["resolved"]["recall"],
            "target_document_id_metrics": {
                "pred_resolved_total": pred_resolved_total,
                "pred_resolved_correct_target": pred_resolved_correct_target,
                "target_id_accuracy_on_all_pred_resolved": round(target_id_acc_on_pred, 4),
                "both_gold_and_pred_resolved": both_resolved_count,
                "both_resolved_correct_target": both_resolved_correct_target,
                "target_id_accuracy_when_status_correct": round(target_id_acc_on_both_resolved, 4)
            },
            "linking_breakdown": {
                "predicted_self_citations": self_citations_resolved_pred,
                "predicted_cross_document_citations": cross_doc_resolved_pred
            }
        },
        "detailed_records": detailed_records
    }


def main():
    print("=" * 70)
    print("NyayaVarta Milestone 4A.1: Entity Resolution & Citation Audit")
    print("=" * 70)

    # 1. Run on Baseline v1
    v1_results = run_evaluation(BENCHMARK_V1, is_v2=False)
    print("\n[1] BASELINE BENCHMARK (v1 - Original Unaudited):")
    print(f"Extraction Precision: {v1_results['citation_extraction']['precision']:.4f}, Recall: {v1_results['citation_extraction']['recall']:.4f}, F1: {v1_results['citation_extraction']['f1']:.4f}")
    print(f"Resolution Status Accuracy: {v1_results['entity_resolution']['status_accuracy']:.4f}")
    print(f"Resolved Class: P={v1_results['entity_resolution']['per_class_metrics']['resolved']['precision']:.4f}, R={v1_results['entity_resolution']['per_class_metrics']['resolved']['recall']:.4f}")
    print(f"Target ID Accuracy (on status-correct resolved): {v1_results['entity_resolution']['target_document_id_metrics']['target_id_accuracy_when_status_correct']:.4f}")
    print("Confusion Matrix:")
    for g, row in v1_results['entity_resolution']['confusion_matrix'].items():
        print(f"  Gold {g:11s} -> {row}")

    # 2. Run on Corrected v2
    v2_results = run_evaluation(BENCHMARK_V2, is_v2=True)
    print("\n[2] CORRECTED BENCHMARK (v2 - Cross-Verified):")
    print(f"Extraction Precision: {v2_results['citation_extraction']['precision']:.4f}, Recall: {v2_results['citation_extraction']['recall']:.4f}, F1: {v2_results['citation_extraction']['f1']:.4f}")
    print(f"Resolution Status Accuracy: {v2_results['entity_resolution']['status_accuracy']:.4f}")
    print(f"Resolved Class: P={v2_results['entity_resolution']['per_class_metrics']['resolved']['precision']:.4f}, R={v2_results['entity_resolution']['per_class_metrics']['resolved']['recall']:.4f}")
    print(f"Target ID Accuracy (on status-correct resolved): {v2_results['entity_resolution']['target_document_id_metrics']['target_id_accuracy_when_status_correct']:.4f}")
    print("Confusion Matrix:")
    for g, row in v2_results['entity_resolution']['confusion_matrix'].items():
        print(f"  Gold {g:11s} -> {row}")

    # Save dual evaluation
    combined_report = {
        "evaluation_version": "2.0.0",
        "milestone": "4A.1",
        "baseline_v1": v1_results,
        "corrected_v2": v2_results
    }

    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(combined_report, f, indent=4)

    print(f"\nSaved dual-benchmark machine-readable evaluation report to {OUT_JSON}")


if __name__ == "__main__":
    main()
