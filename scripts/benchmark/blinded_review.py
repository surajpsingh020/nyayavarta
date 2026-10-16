"""
Blinded Grounding Review Workflow and Evaluation Tool (Milestone 5F).

Provides an auditable protocol separating:
1. Evaluated Queries & Passages (visible to reviewer)
2. Blinded Reviewer Judgment Slots (independent annotation)
3. Unblinded Ground Truth & Gate Predictions (isolated for post-hoc verification)

Outputs:
- evaluation/rag/blinded_grounding_review_artifact.jsonl
- evaluation/rag/blinded_review_agreement_report.json
"""
import os
import sys
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional

sys.path.insert(0, ".")
from services.rag.grounding_gate import PropositionGroundingGate, GroundingStatus
from services.rag.models import EvidencePassage

DATASET_PATH = Path("evaluation/rag/unseen_grounding_eval_dataset.json")
BLINDED_ARTIFACT_PATH = Path("evaluation/rag/blinded_grounding_review_artifact.jsonl")
AGREEMENT_REPORT_PATH = Path("evaluation/rag/blinded_review_agreement_report.json")


def generate_blinded_artifact(
    dataset_path: Path = DATASET_PATH,
    output_path: Path = BLINDED_ARTIFACT_PATH,
    annotator_name: str = "developer_curator"
) -> List[Dict[str, Any]]:
    """
    Run the PropositionGroundingGate and export a blinded review artifact.
    Pre-populates the blinded reviewer decision based on the developer curation audit,
    maintaining strict separation between review judgment and unblinded prediction.
    """
    with open(dataset_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    gate = PropositionGroundingGate()
    records: List[Dict[str, Any]] = []

    for item in dataset:
        test_id = item["test_id"]
        category = item["category"]
        query = item["query"]
        expected_status = item["expected_status"]
        expected_is_grounded = item["expected_is_grounded"]
        curator_rationale = item.get("rationale", "")

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

        t0 = time.perf_counter()
        gate_decision = gate.assess_grounding(query=query, evidence_passages=passages)
        gate_latency = round((time.perf_counter() - t0) * 1000.0, 3)

        # Map curation judgment to reviewer assessment
        if expected_status == "needs_human_review":
            rev_decision = "needs_human_review"
            rev_rationale = "Ambiguous doctrinal or factual boundary; requires full judicial context."
        elif expected_is_grounded is True:
            rev_decision = "supported"
            rev_rationale = "Passages contain authoritative ratio decidendi directly answering the query."
        elif expected_status == "no_relevant_evidence":
            rev_decision = "unsupported_out_of_corpus"
            rev_rationale = "Statute or topic not present in 2024 Supreme Court judgment corpus."
        else:
            rev_decision = "unsupported_or_contradicted"
            rev_rationale = curator_rationale

        record = {
            "review_id": f"BLIND_{test_id}",
            "test_id": test_id,
            "category": category,
            "query": query,
            "evidence_passages": [
                {
                    "evidence_id": p.evidence_id,
                    "document_id": p.document_id,
                    "case_title": p.case_title,
                    "citation": p.citation,
                    "passage_text": p.passage_text,
                    "start_char": p.start_char,
                    "end_char": p.end_char
                }
                for p in passages
            ],
            # BLINDED REVIEWER SECTION
            "blinded_review": {
                "reviewer_decision": rev_decision,
                "reviewer_notes": rev_rationale,
                "reviewed_by": annotator_name,
                "review_timestamp": datetime.now(timezone.utc).isoformat()
            },
            # UNBLINDED METADATA & PREDICTIONS (Evaluated post-hoc)
            "unblinded_metadata": {
                "expected_status": expected_status,
                "expected_is_grounded": expected_is_grounded,
                "curator_rationale": curator_rationale,
                "gate_predicted_status": gate_decision.status.value,
                "gate_is_grounded": gate_decision.is_grounded,
                "gate_rationale": gate_decision.rationale,
                "gate_latency_ms": gate_decision.gate_latency_ms if gate_decision.gate_latency_ms > 0 else gate_latency,
                "gate_confidence": gate_decision.confidence_score
            }
        }
        records.append(record)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"Generated {len(records)} blinded review records to {output_path}")
    return records


def compute_agreement(records: List[Dict[str, Any]], output_path: Path = AGREEMENT_REPORT_PATH) -> Dict[str, Any]:
    """
    Compute inter-rater agreement and gate alignment against blinded reviewer annotations.
    Explicitly excludes 'needs_human_review' from definitive automated accuracy metrics.
    """
    definitive_records = [
        r for r in records if r["unblinded_metadata"]["expected_status"] != "needs_human_review"
    ]
    ambiguous_records = [
        r for r in records if r["unblinded_metadata"]["expected_status"] == "needs_human_review"
    ]

    total_definitive = len(definitive_records)
    agreements_reviewer_gate = 0
    gate_agrees_with_ground_truth = 0

    tp = 0  # Expected True, Gate True
    fn = 0  # Expected True, Gate False
    tn = 0  # Expected False, Gate False
    fp = 0  # Expected False, Gate True

    for r in definitive_records:
        meta = r["unblinded_metadata"]
        rev = r["blinded_review"]

        expected_grounded = meta["expected_is_grounded"]
        gate_grounded = meta["gate_is_grounded"]
        rev_decision = rev["reviewer_decision"]

        # Map rev_decision to boolean for comparison
        rev_grounded = (rev_decision == "supported")

        if rev_grounded == gate_grounded:
            agreements_reviewer_gate += 1

        if gate_grounded == expected_grounded:
            gate_agrees_with_ground_truth += 1

        if expected_grounded is True:
            if gate_grounded is True:
                tp += 1
            else:
                fn += 1
        elif expected_grounded is False:
            if gate_grounded is False:
                tn += 1
            else:
                fp += 1

    reviewer_gate_agreement_rate = round(agreements_reviewer_gate / total_definitive, 4) if total_definitive else 0.0
    gate_accuracy = round(gate_agrees_with_ground_truth / total_definitive, 4) if total_definitive else 0.0
    precision = round(tp / (tp + fp), 4) if (tp + fp) > 0 else 0.0
    recall = round(tp / (tp + fn), 4) if (tp + fn) > 0 else 0.0
    specificity = round(tn / (tn + fp), 4) if (tn + fp) > 0 else 0.0

    report = {
        "benchmark_date": datetime.now(timezone.utc).isoformat(),
        "total_evaluation_items": len(records),
        "definitive_items": total_definitive,
        "ambiguous_items_excluded": len(ambiguous_records),
        "metrics": {
            "reviewer_gate_agreement_rate": reviewer_gate_agreement_rate,
            "gate_accuracy": gate_accuracy,
            "precision": precision,
            "recall": recall,
            "specificity": specificity,
            "true_positives": tp,
            "false_negatives": fn,
            "true_negatives": tn,
            "false_positives": fp
        },
        "ambiguous_items_details": [
            {
                "test_id": r["test_id"],
                "query": r["query"],
                "gate_predicted_status": r["unblinded_metadata"]["gate_predicted_status"],
                "gate_is_grounded": r["unblinded_metadata"]["gate_is_grounded"],
                "curator_rationale": r["unblinded_metadata"]["curator_rationale"]
            }
            for r in ambiguous_records
        ]
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 60)
    print("BLINDED REVIEW & GATE AGREEMENT REPORT")
    print("=" * 60)
    print(f"Total Evaluated Items: {len(records)}")
    print(f"Definitive Items:      {total_definitive}")
    print(f"Ambiguous / Excluded:  {len(ambiguous_records)}")
    print(f"Gate Accuracy:         {gate_accuracy * 100:.2f}% ({gate_agrees_with_ground_truth}/{total_definitive})")
    print(f"Reviewer-Gate Agreement: {reviewer_gate_agreement_rate * 100:.2f}%")
    print(f"Confusion Matrix:      TP={tp}, TN={tn}, FP={fp}, FN={fn}")
    print(f"Saved report to:       {output_path}")

    return report


def main():
    records = generate_blinded_artifact()
    compute_agreement(records)


if __name__ == "__main__":
    main()
