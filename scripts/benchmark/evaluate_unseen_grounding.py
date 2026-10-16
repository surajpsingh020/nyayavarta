"""
Independent Grounding Evaluation & Baseline Comparison Runner (Milestone 5F).

Evaluates generalization on evaluation/rag/unseen_grounding_eval_dataset.json comparing:
1. PropositionGroundingGate (Frozen Milestone 5E implementation)
2. Simple Token-Coverage Baseline (Retriever/Lexical Overlap heuristic >= 40%)

Measures:
- True Positives, False Positives, True Negatives, False Negatives
- Accuracy, Precision, Recall, Specificity
- Per-category confusion matrix across all 12 legal categories
- Gate latency percentiles (median, p95, max)
- Explicit segregation of ambiguous / 'needs_human_review' test items

Outputs:
- evaluation/rag/unseen_grounding_audit_report.json
"""
import os
import sys
import json
import time
import re
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Set, Tuple

sys.path.insert(0, ".")
from services.rag.grounding_gate import PropositionGroundingGate, GroundingStatus
from services.rag.models import EvidencePassage

UNSEEN_DATASET_PATH = Path("evaluation/rag/unseen_grounding_eval_dataset.json")
REPORT_OUTPUT_PATH = Path("evaluation/rag/unseen_grounding_audit_report.json")

RE_WORDS_4 = re.compile(r'\b[a-z0-9]{4,}\b')
STOPWORDS = {
    "what", "where", "when", "which", "who", "does", "did", "would", "could", "should",
    "shall", "about", "these", "those", "their", "there", "having", "being", "under",
    "between", "against", "cannot", "court", "courts", "supreme", "judgment", "held",
    "with", "from", "into", "such", "also", "only", "other", "some", "same", "view",
    "this", "that", "and", "for", "the", "are", "is", "a", "an", "to", "of", "in", "by"
}


def run_token_coverage_baseline(query: str, passages: List[EvidencePassage], threshold: float = 0.40) -> Tuple[bool, float, str]:
    """
    Standard lexical token-coverage baseline without syntactic, polarity, or structural gating.
    If salient query token overlap in evidence is >= threshold, returns (True, coverage, 'sufficient_evidence'),
    else returns (False, coverage, 'insufficient_evidence').
    """
    if not passages:
        return False, 0.0, "no_relevant_evidence"

    q_terms = set(w.lower() for w in RE_WORDS_4.findall(query.lower()) if w.lower() not in STOPWORDS)
    if not q_terms:
        return False, 0.0, "insufficient_evidence"

    all_evidence = " ".join(p.passage_text.lower() for p in passages)
    matched = [w for w in q_terms if w in all_evidence]
    coverage = len(matched) / len(q_terms)

    if coverage >= threshold:
        return True, round(coverage, 3), "sufficient_evidence"
    return False, round(coverage, 3), "insufficient_evidence"


def evaluate_unseen_grounding(
    dataset_path: Path = UNSEEN_DATASET_PATH,
    output_path: Path = REPORT_OUTPUT_PATH
) -> Dict[str, Any]:
    print("=" * 80)
    print("NyayaVarta Milestone 5F: Independent Grounding Evaluation & Baseline Comparison")
    print("=" * 80)

    with open(dataset_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    gate = PropositionGroundingGate()

    total_cases = len(dataset)
    definitive_cases = 0
    human_review_cases = 0

    gate_tp, gate_fp, gate_tn, gate_fn = 0, 0, 0, 0
    base_tp, base_fp, base_tn, base_fn = 0, 0, 0, 0

    category_stats: Dict[str, Dict[str, Any]] = {}
    gate_latencies: List[float] = []
    case_results: List[Dict[str, Any]] = []

    for item in dataset:
        test_id = item["test_id"]
        category = item["category"]
        query = item["query"]
        expected_status = item["expected_status"]
        expected_is_grounded = item["expected_is_grounded"]
        rationale = item.get("rationale", "")

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
            for idx, p in enumerate(item.get("passages", []))
        ]

        # 1. Evaluate PropositionGroundingGate
        t0 = time.perf_counter()
        gate_dec = gate.assess_grounding(query=query, evidence_passages=passages)
        lat = round((time.perf_counter() - t0) * 1000.0, 3)
        gate_latencies.append(gate_dec.gate_latency_ms if gate_dec.gate_latency_ms > 0 else lat)

        # 2. Evaluate Lexical Baseline
        base_grounded, base_coverage, base_status = run_token_coverage_baseline(query, passages)

        is_human_review = (expected_status == "needs_human_review")

        if is_human_review:
            human_review_cases += 1
        else:
            definitive_cases += 1

            # Gate metrics
            if expected_is_grounded is True:
                if gate_dec.is_grounded is True:
                    gate_tp += 1
                else:
                    gate_fn += 1
            else:
                if gate_dec.is_grounded is False:
                    gate_tn += 1
                else:
                    gate_fp += 1

            # Baseline metrics
            if expected_is_grounded is True:
                if base_grounded is True:
                    base_tp += 1
                else:
                    base_fn += 1
            else:
                if base_grounded is False:
                    base_tn += 1
                else:
                    base_fp += 1

        if category not in category_stats:
            category_stats[category] = {
                "total": 0,
                "expected_grounded": 0,
                "expected_ungrounded": 0,
                "needs_human_review": 0,
                "gate_correct": 0,
                "gate_false_positive": 0,
                "gate_false_negative": 0,
                "baseline_correct": 0,
                "baseline_false_positive": 0,
                "baseline_false_negative": 0
            }

        cs = category_stats[category]
        cs["total"] += 1
        if is_human_review:
            cs["needs_human_review"] += 1
        elif expected_is_grounded is True:
            cs["expected_grounded"] += 1
            if gate_dec.is_grounded:
                cs["gate_correct"] += 1
            else:
                cs["gate_false_negative"] += 1
            if base_grounded:
                cs["baseline_correct"] += 1
            else:
                cs["baseline_false_negative"] += 1
        else:
            cs["expected_ungrounded"] += 1
            if not gate_dec.is_grounded:
                cs["gate_correct"] += 1
            else:
                cs["gate_false_positive"] += 1
            if not base_grounded:
                cs["baseline_correct"] += 1
            else:
                cs["baseline_false_positive"] += 1

        case_results.append({
            "test_id": test_id,
            "category": category,
            "query": query,
            "expected_status": expected_status,
            "expected_is_grounded": expected_is_grounded,
            "gate_decision": {
                "status": gate_dec.status.value,
                "is_grounded": gate_dec.is_grounded,
                "confidence": gate_dec.confidence_score,
                "rationale": gate_dec.rationale,
                "latency_ms": gate_dec.gate_latency_ms
            },
            "baseline_decision": {
                "status": base_status,
                "is_grounded": base_grounded,
                "coverage": base_coverage
            },
            "curator_rationale": rationale
        })

    # Summary Metrics for Definitive Set
    gate_acc = round((gate_tp + gate_tn) / definitive_cases, 4) if definitive_cases else 0.0
    gate_prec = round(gate_tp / (gate_tp + gate_fp), 4) if (gate_tp + gate_fp) else 0.0
    gate_rec = round(gate_tp / (gate_tp + gate_fn), 4) if (gate_tp + gate_fn) else 0.0
    gate_spec = round(gate_tn / (gate_tn + gate_fp), 4) if (gate_tn + gate_fp) else 0.0
    gate_fpr = round(gate_fp / (gate_tn + gate_fp), 4) if (gate_tn + gate_fp) else 0.0

    base_acc = round((base_tp + base_tn) / definitive_cases, 4) if definitive_cases else 0.0
    base_prec = round(base_tp / (base_tp + base_fp), 4) if (base_tp + base_fp) else 0.0
    base_rec = round(base_tp / (base_tp + base_fn), 4) if (base_tp + base_fn) else 0.0
    base_spec = round(base_tn / (base_tn + base_fp), 4) if (base_tn + base_fp) else 0.0
    base_fpr = round(base_fp / (base_tn + base_fp), 4) if (base_tn + base_fp) else 0.0

    lat_sorted = sorted(gate_latencies)
    median_lat = round(statistics.median(gate_latencies), 3) if gate_latencies else 0.0
    p95_lat = round(lat_sorted[int(len(lat_sorted) * 0.95)], 3) if gate_latencies else 0.0
    max_lat = round(max(gate_latencies), 3) if gate_latencies else 0.0

    report = {
        "benchmark_metadata": {
            "eval_name": "Milestone 5F Independent Unseen Grounding Benchmark",
            "benchmark_date": datetime.now(timezone.utc).isoformat(),
            "dataset_version": "unseen_grounding_eval_dataset_v1",
            "total_queries": total_cases,
            "definitive_queries": definitive_cases,
            "human_review_queries": human_review_cases,
            "corpus_size": "782 judgments (2024 SC)",
            "gate_version": "PropositionGroundingGate_5E_Frozen"
        },
        "performance_comparison": {
            "proposition_grounding_gate": {
                "accuracy": gate_acc,
                "precision": gate_prec,
                "recall": gate_rec,
                "specificity": gate_spec,
                "false_positive_rate": gate_fpr,
                "true_positives": gate_tp,
                "false_positives": gate_fp,
                "true_negatives": gate_tn,
                "false_negatives": gate_fn,
                "latency_stats": {
                    "median_ms": median_lat,
                    "p95_ms": p95_lat,
                    "max_ms": max_lat
                }
            },
            "token_coverage_baseline": {
                "accuracy": base_acc,
                "precision": base_prec,
                "recall": base_rec,
                "specificity": base_spec,
                "false_positive_rate": base_fpr,
                "true_positives": base_tp,
                "false_positives": base_fp,
                "true_negatives": base_tn,
                "false_negatives": base_fn
            }
        },
        "category_breakdown": category_stats,
        "human_review_cases": [
            r for r in case_results if r["expected_status"] == "needs_human_review"
        ],
        "detailed_case_evaluations": case_results
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 80)
    print("EVALUATION RESULTS SUMMARY")
    print("=" * 80)
    print(f"Total Queries: {total_cases} (Definitive: {definitive_cases}, Needs Human Review: {human_review_cases})")
    print("\nMETRIC                      PROPOSITION GATE    TOKEN BASELINE")
    print("-" * 65)
    print(f"Accuracy:                   {gate_acc*100:15.2f}%   {base_acc*100:15.2f}%")
    print(f"Precision:                  {gate_prec*100:15.2f}%   {base_prec*100:15.2f}%")
    print(f"Recall:                     {gate_rec*100:15.2f}%   {base_rec*100:15.2f}%")
    print(f"Specificity:                {gate_spec*100:15.2f}%   {base_spec*100:15.2f}%")
    print(f"False Positive Rate:        {gate_fpr*100:15.2f}%   {base_fpr*100:15.2f}%")
    print(f"Confusion (TP/TN/FP/FN):    {gate_tp}/{gate_tn}/{gate_fp}/{gate_fn}         {base_tp}/{base_tn}/{base_fp}/{base_fn}")
    print(f"Gate Latency (median/p95):  {median_lat:.2f} ms / {p95_lat:.2f} ms")
    print("=" * 80)
    print(f"Audit report saved to: {output_path}")

    return report


if __name__ == "__main__":
    evaluate_unseen_grounding()
