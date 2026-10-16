"""
Milestone 10: Retrieval Quality Audit and Evidence Passage Evaluation Runner.
Audits retrieval, passage selection, offset integrity, party submission contamination,
and context budgets across 3 configurations for all 42 queries in milestone10_eval_dataset.json.
"""
import os
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import json
import time
from typing import Dict, Any, List
from collections import defaultdict

from services.rag.pipeline import RAGPipeline
from services.rag.evidence import compute_jaccard_similarity
from services.rag.models import RAGResult

EVAL_DATASET_PATH = "evaluation/rag/milestone10_eval_dataset.json"
REPORT_OUTPUT_PATH = "evaluation/rag/milestone10_retrieval_comparison.json"
CORPUS_DIR = "data/processed/aws_sc"


def evaluate_config(
    pipeline: RAGPipeline,
    queries: List[Dict[str, Any]],
    config_name: str,
    max_passages: int,
    max_chars_per_passage: int,
    enable_compression: bool,
    enable_issue_holding_pairing: bool
) -> Dict[str, Any]:
    print(f"\n=======================================================")
    print(f"Evaluating {config_name}")
    print(f"=======================================================")

    total_queries = len(queries)
    answerable_queries = [q for q in queries if q.get("sufficient_evidence_in_corpus", False)]
    num_answerable = len(answerable_queries)
    unanswerable_queries = [q for q in queries if not q.get("sufficient_evidence_in_corpus", False)]
    num_unanswerable = len(unanswerable_queries)

    hits_at_1 = 0
    hits_at_3 = 0
    hits_at_5 = 0
    reciprocal_ranks = []
    recalls_at_3 = []
    recalls_at_5 = []

    retrieval_latencies_ms = []
    evidence_assembly_latencies_ms = []
    gate_latencies_ms = []
    total_pregen_latencies_ms = []

    candidate_text_chars_list = []
    active_passages_raw_chars_list = []
    formatted_evidence_chars_list = []
    prompt_chars_list = []
    total_prompt_chars_list = []

    total_active_passages = 0
    party_submission_passages = 0
    offset_verified_passages = 0
    overlapping_passages_count = 0
    holding_passages_selected = 0

    required_passages_retrieved_count = 0
    fast_exit_abstentions = 0
    answered_count = 0

    per_query_results = []

    for idx, q in enumerate(queries, 1):
        qid = q["query_id"]
        q_text = q["question"]
        expected_docs = q.get("expected_document_ids", [])
        is_answerable = q.get("sufficient_evidence_in_corpus", False)

        t0 = time.perf_counter()
        res: RAGResult = pipeline.query(
            query_text=q_text,
            top_k_judgments=5,
            max_passages=max_passages,
            max_chars_per_passage=max_chars_per_passage,
            enable_compression=enable_compression,
            structured_output=True,
            enable_issue_holding_pairing=enable_issue_holding_pairing
        )
        total_time_ms = round((time.perf_counter() - t0) * 1000.0, 2)

        meta = res.retrieval_metadata
        timing = res.timing_ms
        retrieval_latencies_ms.append(timing.get("retrieval_ms", 0.0))
        evidence_assembly_latencies_ms.append(timing.get("evidence_assembly_ms", 0.0))
        gate_latencies_ms.append(timing.get("grounding_gate_ms", 0.0))
        total_pregen_latencies_ms.append(
            timing.get("retrieval_ms", 0.0) +
            timing.get("evidence_assembly_ms", 0.0) +
            timing.get("grounding_gate_ms", 0.0)
        )

        c_budget = meta.get("context_budget", {})
        candidate_text_chars_list.append(c_budget.get("candidate_text_chars", 0))
        active_passages_raw_chars_list.append(c_budget.get("active_passages_raw_chars", 0))
        formatted_evidence_chars_list.append(c_budget.get("formatted_evidence_chars", 0))
        prompt_chars_list.append(c_budget.get("prompt_chars", 0))
        total_prompt_chars_list.append(c_budget.get("total_prompt_chars", 0))

        top_candidates = meta.get("top_candidates", [])

        # Document-level metrics for answerable queries
        if is_answerable and expected_docs:
            # HitRate@1
            if top_candidates and top_candidates[0] in expected_docs:
                hits_at_1 += 1
            # HitRate@3
            if any(doc in expected_docs for doc in top_candidates[:3]):
                hits_at_3 += 1
            # HitRate@5
            if any(doc in expected_docs for doc in top_candidates[:5]):
                hits_at_5 += 1

            # MRR
            rr = 0.0
            for rank_idx, doc_id in enumerate(top_candidates, 1):
                if doc_id in expected_docs:
                    rr = 1.0 / rank_idx
                    break
            reciprocal_ranks.append(rr)

            # Recall@K
            retrieved_3 = set(top_candidates[:3])
            retrieved_5 = set(top_candidates[:5])
            exp_set = set(expected_docs)
            recalls_at_3.append(len(retrieved_3.intersection(exp_set)) / len(exp_set))
            recalls_at_5.append(len(retrieved_5.intersection(exp_set)) / len(exp_set))

        # Check active passages properties
        active = res.evidence_passages
        num_act = len(active)
        total_active_passages += num_act

        # Offset integrity & structural labels
        has_holding = False
        has_submission = False
        has_overlap = False

        for p_idx, p in enumerate(active):
            fpath = os.path.join(CORPUS_DIR, f"{p.document_id}.json")
            if os.path.exists(fpath):
                with open(fpath, "r", encoding="utf-8") as f:
                    full_text = json.load(f).get("full_text", "")
                if full_text[p.start_char:p.end_char] == p.passage_text:
                    offset_verified_passages += 1

            if p.structural_label == "party_submissions":
                party_submission_passages += 1
                has_submission = True
            if p.structural_label in ("headnote_holding", "judicial_holding"):
                has_holding = True
                holding_passages_selected += 1

            # Check overlap against previous passages in this answer
            for prev_p in active[:p_idx]:
                if prev_p.document_id == p.document_id:
                    if not (p.end_char <= prev_p.start_char or p.start_char >= prev_p.end_char):
                        has_overlap = True
                        overlapping_passages_count += 1
                if compute_jaccard_similarity(p.passage_text, prev_p.passage_text) >= 0.80:
                    has_overlap = True
                    overlapping_passages_count += 1

        if is_answerable and (has_holding or any(p.document_id in expected_docs for p in active)):
            required_passages_retrieved_count += 1

        is_fast_exit = (res.timing_ms.get("generation_ms", 0) == 0.0)
        if is_fast_exit:
            fast_exit_abstentions += 1
        else:
            answered_count += 1

        per_query_results.append({
            "query_id": qid,
            "category": q.get("category"),
            "is_answerable": is_answerable,
            "expected_docs": expected_docs,
            "top_candidates": top_candidates[:5],
            "status": res.status,
            "grounding_status": res.grounding_status,
            "is_fast_exit": is_fast_exit,
            "active_evidence_count": len(active),
            "active_evidence": [
                {
                    "evidence_id": p.evidence_id,
                    "document_id": p.document_id,
                    "structural_label": p.structural_label,
                    "char_length": len(p.passage_text),
                    "start_char": p.start_char,
                    "end_char": p.end_char
                }
                for p in active
            ],
            "context_budget": c_budget,
            "total_pregen_ms": round(total_time_ms, 2)
        })

    def _mean(vals):
        return round(sum(vals) / len(vals), 3) if vals else 0.0

    def _median(vals):
        if not vals:
            return 0.0
        s = sorted(vals)
        n = len(s)
        mid = n // 2
        return round((s[mid] if n % 2 != 0 else (s[mid - 1] + s[mid]) / 2.0), 3)

    return {
        "config_name": config_name,
        "max_passages": max_passages,
        "max_chars_per_passage": max_chars_per_passage,
        "enable_compression": enable_compression,
        "enable_issue_holding_pairing": enable_issue_holding_pairing,
        "queries_total": total_queries,
        "queries_answerable": num_answerable,
        "queries_unanswerable": num_unanswerable,
        "retrieval_document_metrics": {
            "hit_rate_at_1": round(hits_at_1 / num_answerable, 4) if num_answerable else 0.0,
            "hit_rate_at_3": round(hits_at_3 / num_answerable, 4) if num_answerable else 0.0,
            "hit_rate_at_5": round(hits_at_5 / num_answerable, 4) if num_answerable else 0.0,
            "mean_reciprocal_rank": _mean(reciprocal_ranks),
            "recall_at_3": _mean(recalls_at_3),
            "recall_at_5": _mean(recalls_at_5)
        },
        "passage_selection_metrics": {
            "total_active_passages_selected": total_active_passages,
            "required_passages_retrieved_rate": round(required_passages_retrieved_count / num_answerable, 4) if num_answerable else 0.0,
            "party_submission_contamination_rate": round(party_submission_passages / total_active_passages, 4) if total_active_passages else 0.0,
            "party_submission_passages_count": party_submission_passages,
            "overlapping_passage_rate": round(overlapping_passages_count / total_active_passages, 4) if total_active_passages else 0.0,
            "overlapping_passages_count": overlapping_passages_count,
            "exact_offset_integrity_rate": round(offset_verified_passages / total_active_passages, 4) if total_active_passages else 1.0,
            "holding_passages_count": holding_passages_selected
        },
        "context_budget_metrics": {
            "avg_candidate_text_chars": _mean(candidate_text_chars_list),
            "median_candidate_text_chars": _median(candidate_text_chars_list),
            "avg_active_passages_raw_chars": _mean(active_passages_raw_chars_list),
            "median_active_passages_raw_chars": _median(active_passages_raw_chars_list),
            "avg_formatted_evidence_chars": _mean(formatted_evidence_chars_list),
            "median_formatted_evidence_chars": _median(formatted_evidence_chars_list),
            "avg_prompt_chars": _mean(prompt_chars_list),
            "avg_total_prompt_chars": _mean(total_prompt_chars_list)
        },
        "latency_metrics_ms": {
            "mean_retrieval_ms": _mean(retrieval_latencies_ms),
            "median_retrieval_ms": _median(retrieval_latencies_ms),
            "mean_evidence_assembly_ms": _mean(evidence_assembly_latencies_ms),
            "median_evidence_assembly_ms": _median(evidence_assembly_latencies_ms),
            "mean_gate_ms": _mean(gate_latencies_ms),
            "median_gate_ms": _median(gate_latencies_ms),
            "mean_total_pregen_ms": _mean(total_pregen_latencies_ms),
            "median_total_pregen_ms": _median(total_pregen_latencies_ms)
        },
        "pipeline_decisions": {
            "fast_exit_abstentions": fast_exit_abstentions,
            "proceeded_to_generation": answered_count
        },
        "per_query_results": per_query_results
    }


def run_milestone10_retrieval_audit():
    with open(EVAL_DATASET_PATH, "r", encoding="utf-8") as f:
        queries = json.load(f)

    print(f"Loaded {len(queries)} evaluation queries from {EVAL_DATASET_PATH}.")

    pipeline = RAGPipeline()

    configs = [
        {
            "config_key": "config_1_m7_single_passage",
            "config_name": "Config 1: Milestone 7 Baseline (Single-Passage, k=1, max 750 chars)",
            "max_passages": 1,
            "max_chars_per_passage": 750,
            "enable_compression": False,
            "enable_issue_holding_pairing": False
        },
        {
            "config_key": "config_2_m8_two_passage",
            "config_name": "Config 2: Milestone 8 Baseline (Two-Passage, k=2, max 750 chars, no pairing)",
            "max_passages": 2,
            "max_chars_per_passage": 750,
            "enable_compression": False,
            "enable_issue_holding_pairing": False
        },
        {
            "config_key": "config_3_m9_structure_aware_paired",
            "config_name": "Config 3: Milestone 9 Structure-Aware (Two-Passage, k=2, max 550 chars, pairing+budget)",
            "max_passages": 2,
            "max_chars_per_passage": 550,
            "enable_compression": True,
            "enable_issue_holding_pairing": True
        }
    ]

    report = {
        "metadata": {
            "milestone": "Milestone 10",
            "dataset": "42-Query Expanded Evaluation Suite",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "corpus_size": 782,
            "total_queries": len(queries),
            "provenance": "developer_curated"
        },
        "configurations": {}
    }

    for cfg in configs:
        res = evaluate_config(
            pipeline=pipeline,
            queries=queries,
            config_name=cfg["config_name"],
            max_passages=cfg["max_passages"],
            max_chars_per_passage=cfg["max_chars_per_passage"],
            enable_compression=cfg["enable_compression"],
            enable_issue_holding_pairing=cfg["enable_issue_holding_pairing"]
        )
        report["configurations"][cfg["config_key"]] = res

    os.makedirs(os.path.dirname(REPORT_OUTPUT_PATH), exist_ok=True)
    with open(REPORT_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"\n=======================================================")
    print(f"Audit completed successfully!")
    print(f"Report saved to: {REPORT_OUTPUT_PATH}")
    print(f"=======================================================")


if __name__ == "__main__":
    run_milestone10_retrieval_audit()
