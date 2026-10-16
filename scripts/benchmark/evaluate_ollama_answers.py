"""
Real Local Ollama Answer Generation & Claim Review Benchmark (Milestone 5F).

Runs representative legal queries through the end-to-end NyayaVarta RAG Pipeline
using the local Ollama provider (phi3.5:latest).

Verifies:
1. End-to-end grounding guardrails: Pipeline abstains immediately on ungrounded/out-of-corpus queries without wasteful generation.
2. Real-model answer generation for grounded queries: Response generation speed, token throughput, citation syntax & offset validity.
3. Claim-level attribution: Uses services/rag/claim_reviewer.py to extract structured claim review records.

Outputs:
- evaluation/rag/ollama_claim_review_artifact.jsonl
- evaluation/rag/ollama_answer_eval_report_5f.json
"""
import os
import sys
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any

sys.path.insert(0, ".")
from services.rag.pipeline import RAGPipeline
from services.rag.providers import LocalOllamaProvider
from services.rag.claim_reviewer import extract_claim_review_records, ClaimReviewRecord
from services.rag.models import RAGResult

OUTPUT_ARTIFACT_PATH = Path("evaluation/rag/ollama_claim_review_artifact.jsonl")
OUTPUT_REPORT_PATH = Path("evaluation/rag/ollama_answer_eval_report_5f.json")

# Representative suite of queries spanning grounded, negation, exception, submission, and out-of-corpus categories
SAMPLE_QUERIES = [
    {
        "query_id": "OLLAMA_001_GROUNDED_ART142",
        "category": "direct_positive_support",
        "query": "Can the Supreme Court exercise powers under Article 142 of the Constitution to grant admission to an IIT candidate from a marginalized community who was prevented from paying fees due to a portal login glitch?",
        "expected_answerable": True,
        "description": "Atul Kumar v. Chairman JOSAA (2024_10_150_153) Article 142 equity relief."
    },
    {
        "query_id": "OLLAMA_002_GROUNDED_IBC_SEC62",
        "category": "direct_positive_support",
        "query": "Can any person aggrieved by an order of the NCLAT maintain an appeal before the Supreme Court under Section 62 of the Insolvency and Bankruptcy Code?",
        "expected_answerable": True,
        "description": "Glas Trust v. Byju Raveendran (2024_10_1802_1854) Section 62 IBC statutory standing."
    },
    {
        "query_id": "OLLAMA_003_NEGATION_MUSLIM_COPARCENARY",
        "category": "negation",
        "query": "Does the Hindu legal concept of joint family coparcenary property apply to Mohammedans governed by Muslim law?",
        "expected_answerable": False,
        "description": "Nisar Ahmad v. Sami Ullah (2024_10_1855_1875) explicit negation of Hindu joint family to Muslims."
    },
    {
        "query_id": "OLLAMA_004_EXCEPTION_NDPS_SUMMARY_TRIAL",
        "category": "exception",
        "query": "Does Section 36A(5) of the NDPS Act empower a Special Judge to conduct summary trial for offences punishable with imprisonment exceeding three years?",
        "expected_answerable": False,
        "description": "Bharti Arora v. State of Haryana (2024_12_1044_1071) summary trial limited to <=3 years."
    },
    {
        "query_id": "OLLAMA_005_REJECTED_SUBMISSION_ASG",
        "category": "rejected_submissions",
        "query": "Does Section 71 of the PMLA override the CrPC to dispense with sanction under Section 197 CrPC as held by the Supreme Court?",
        "expected_answerable": False,
        "description": "Bibhu Prasad Acharya (2024_11_510_522) ASG submission rejected by Court."
    },
    {
        "query_id": "OLLAMA_006_OUT_OF_CORPUS_DPDP",
        "category": "out_of_corpus_unanswerable",
        "query": "What are the eligibility criteria and tenure prescribed under Section 18 of the Digital Personal Data Protection Act, 2023 for members of the Data Protection Board of India?",
        "expected_answerable": False,
        "description": "DPDP Act 2023 out of 2024 Supreme Court judgments corpus."
    }
]


def run_ollama_evaluation(
    model_name: str = "phi3.5:latest",
    queries: List[Dict[str, Any]] = SAMPLE_QUERIES
) -> Dict[str, Any]:
    print("=" * 80)
    print(f"NyayaVarta Milestone 5F: Real Local Ollama Model Evaluation ({model_name})")
    print("=" * 80)

    # Check Ollama status
    avail = LocalOllamaProvider.check_availability(model_name=model_name)
    if not avail["available"]:
        raise RuntimeError(f"Ollama daemon not reachable at http://localhost:11434. Error: {avail['error']}")
    if not avail["target_model_installed"]:
        raise RuntimeError(f"Model {model_name} is not installed in local Ollama. Installed: {avail['models']}")

    print(f"Local Ollama online: {avail['models']}")
    print(f"Target model verified: {model_name}\n")

    provider = LocalOllamaProvider(
        model_name=model_name,
        timeout=240.0,
        default_options={"num_predict": 128, "num_ctx": 1024, "num_thread": 8}
    )
    pipeline = RAGPipeline(llm_provider=provider)

    evaluated_cases: List[Dict[str, Any]] = []
    all_claim_records: List[ClaimReviewRecord] = []

    total_queries = len(queries)
    abstentions_count = 0
    answers_count = 0

    for idx, q_info in enumerate(queries, 1):
        q_id = q_info["query_id"]
        q_text = q_info["query"]
        category = q_info["category"]
        expected_ans = q_info["expected_answerable"]

        print(f"[{idx}/{total_queries}] Evaluating {q_id} ({category})...", flush=True)
        t0 = time.perf_counter()

        result: RAGResult = pipeline.query(
            query_text=q_text,
            top_k_judgments=2,
            max_passages=2,
            enable_graph=False,
            max_chars_per_passage=350
        )
        total_time_s = round(time.perf_counter() - t0, 3)

        is_abstained = (result.status in ["insufficient_evidence", "empty_retrieval", "error"] or
                        result.grounding_status != "sufficient_evidence")

        if is_abstained:
            abstentions_count += 1
            print(f"  -> Abstention enforced: status='{result.status}', grounding='{result.grounding_status}'", flush=True)
            print(f"  -> Total pipeline latency: {total_time_s}s (no wasteful LLM generation)", flush=True)
        else:
            answers_count += 1
            gen_ms = result.timing_ms.get("generation_ms", 0.0)
            print(f"  -> Answer generated successfully: status='{result.status}'", flush=True)
            print(f"  -> Generation time: {gen_ms / 1000.0:.2f}s | Citations valid: {result.citation_validation.is_valid}", flush=True)
            print(f"  -> Answer preview: {result.answer[:120]}...", flush=True)

        # Extract claim review records
        claim_recs = extract_claim_review_records(result, query_id=q_id)
        all_claim_records.extend(claim_recs)

        # Audit decision record
        case_audit = {
            "query_id": q_id,
            "category": category,
            "query": q_text,
            "expected_answerable": expected_ans,
            "actual_answered": not is_abstained,
            "pipeline_status": result.status,
            "grounding_status": result.grounding_status,
            "timing_ms": result.timing_ms,
            "total_latency_seconds": total_time_s,
            "num_evidence_passages": len(result.evidence_passages),
            "citations_summary": {
                "is_valid": result.citation_validation.is_valid,
                "cited_ids": result.citation_validation.cited_source_ids,
                "valid_ids": result.citation_validation.valid_source_ids,
                "invalid_ids": result.citation_validation.invalid_source_ids
            },
            "answer_preview": result.answer[:250],
            "claims_count": len(result.claims)
        }
        evaluated_cases.append(case_audit)
        print()

    # Save claim review artifact
    OUTPUT_ARTIFACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_ARTIFACT_PATH, "w", encoding="utf-8") as f:
        for cr in all_claim_records:
            f.write(cr.model_dump_json() + "\n")
    print(f"Exported {len(all_claim_records)} claim review records to {OUTPUT_ARTIFACT_PATH}")

    # Build evaluation report
    report = {
        "evaluation_metadata": {
            "benchmark_name": "Milestone 5F Real Local Ollama Answer Validation",
            "benchmark_timestamp": datetime.now(timezone.utc).isoformat(),
            "provider_name": "LocalOllamaProvider",
            "model_name": model_name,
            "ollama_base_url": "http://localhost:11434",
            "total_queries_tested": total_queries,
            "abstentions": abstentions_count,
            "answers_generated": answers_count
        },
        "query_evaluations": evaluated_cases,
        "claim_review_summary": {
            "total_claims_extracted": len(all_claim_records),
            "claims_artifact_path": str(OUTPUT_ARTIFACT_PATH)
        }
    }

    OUTPUT_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"Saved evaluation report to {OUTPUT_REPORT_PATH}")

    return report


if __name__ == "__main__":
    run_ollama_evaluation()
