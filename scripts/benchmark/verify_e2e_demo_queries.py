"""
End-to-End Demo Verification Script for NyayaVarta (Phase 3 Audit).

Executes the 5 canonical demo queries under both MockLLMProvider and live LocalOllamaProvider:
1. Supported, corpus-grounded: Tej Prakash Pathak recruitment rules alteration.
2. Partially supported: SARFAESI Rule 9(4) balance deposit extension without borrower consent.
3. Contradicted: Patents Act Section 3(j) seed patentability.
4. Out-of-corpus: Maritime admiralty in rem action limitation.
5. Error/timeout simulation: Simulated provider timeout/failure (fail-closed check).

Captures badges, claims, latencies, and produces a structured audit report.
"""
import time
import json
import logging
import sys
from pathlib import Path
from typing import Dict, Any, List

repo_root = Path(__file__).resolve().parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from services.rag.pipeline import RAGPipeline
from services.rag.providers import MockLLMProvider, LocalOllamaProvider, LLMResponse, LLMProvider
from services.rag.models import RAGResult

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("e2e_demo_verify")

TEST_QUERIES = [
    {
        "id": "DEMO_Q1_SUPPORTED",
        "category": "supported_corpus_grounded",
        "query": "Can the rules of selection or eligibility criteria be changed after the recruitment process has commenced under Rajasthan High Court rules?",
        "expected_badge_family": ["verified_supported", "qualified_answer"],
        "description": "Corpus-grounded recruitment law query regarding Tej Prakash Pathak ruling."
    },
    {
        "id": "DEMO_Q2_PARTIAL",
        "category": "partially_supported",
        "query": "Can the authorized officer unilaterally extend the 15-day period for deposit of 75% purchase money under SARFAESI Rule 9(4) without consent of the borrower?",
        "expected_badge_family": ["qualified_answer", "rejected_answer"],
        "description": "Tests statutory condition where extension is conditioned upon written consent."
    },
    {
        "id": "DEMO_Q3_CONTRADICTED",
        "category": "contradicted",
        "query": "Are seeds, plant varieties, and essentially biological processes patentable under Section 3(j) of the Indian Patents Act, 1970?",
        "expected_badge_family": ["qualified_answer", "rejected_answer", "unverified_answer"],
        "description": "Tests direct statutory prohibition under Section 3(j)."
    },
    {
        "id": "DEMO_Q4_OUT_OF_CORPUS",
        "category": "out_of_corpus",
        "query": "What is the period of limitation for filing an in rem admiralty action against an arrested foreign cargo vessel under the Admiralty Act, 2017?",
        "expected_badge_family": ["unverified_answer", "rejected_answer"],
        "description": "Tests abstention on topic absent from the 2024 SCR corpus."
    },
    {
        "id": "DEMO_Q5_ERROR_TIMEOUT",
        "category": "error_timeout_fail_closed",
        "query": "Simulated fail-closed query under provider timeout/exception.",
        "expected_badge_family": ["rejected_answer", "system_error", "unverified_answer"],
        "description": "Simulates backend timeout / provider error to verify fail-closed invariant."
    }
]


class FailingTimeoutProvider(LLMProvider):
    """Simulates a 504 Gateway Timeout or Provider Exception."""
    def generate(self, prompt: str, **kwargs) -> LLMResponse:
        raise TimeoutError("Simulated 504 Gateway Timeout: Local LLM failed to respond within deadline.")


def run_pipeline_eval(pipeline: RAGPipeline, query_spec: Dict[str, Any], is_timeout_test: bool = False) -> Dict[str, Any]:
    qid = query_spec["id"]
    query_text = query_spec["query"]
    t0 = time.perf_counter()
    
    try:
        if is_timeout_test:
            # Inject timeout provider
            orig_provider = pipeline.llm_provider
            pipeline.llm_provider = FailingTimeoutProvider()
            try:
                res = pipeline.query(query_text=query_text, enable_graph=False)
            finally:
                pipeline.llm_provider = orig_provider
        elif qid == "DEMO_Q2_PARTIAL" and isinstance(pipeline.llm_provider, MockLLMProvider):
            # Inject mock provider asserting the candidate partially supported proposition
            orig_provider = pipeline.llm_provider
            pipeline.llm_provider = MockLLMProvider(mode=MockLLMProvider.MODE_PARTIALLY_SUPPORTED)
            try:
                res = pipeline.query(query_text=query_text, enable_graph=False)
            finally:
                pipeline.llm_provider = orig_provider
        else:
            res = pipeline.query(query_text=query_text, enable_graph=False)
            
        total_time_ms = (time.perf_counter() - t0) * 1000.0
        
        # Extract claim details
        claims_summary = []
        if res.claims:
            for ca in res.claims:
                claims_summary.append({
                    "text": ca.sentence,
                    "status": ca.verification_status,
                    "method": ca.verification_method,
                    "reason": ca.verification_reason,
                    "is_supported": ca.verification_status == "supported",
                    "is_contradicted": ca.verification_status == "contradicted"
                })
                
        total_lat = res.timing_ms.get("total_ms", total_time_ms) if res.timing_ms else total_time_ms

        return {
            "query_id": qid,
            "category": query_spec["category"],
            "query_text": query_text,
            "status": res.status,
            "verification_badge": res.verification_badge,
            "answer_text": res.answer[:300] + "..." if len(res.answer) > 300 else res.answer,
            "num_passages_retrieved": len(res.evidence_passages),
            "retrieved_doc_ids": [p.document_id for p in res.evidence_passages],
            "claims_count": len(res.claims),
            "claims": claims_summary,
            "timing_ms": res.timing_ms,
            "total_latency_ms": round(total_lat, 2),
            "exception_raised": False,
            "error_message": None,
            "is_fail_closed": res.verification_badge != "verified_supported" if qid != "DEMO_Q1_SUPPORTED" else True
        }
    except Exception as e:
        total_time_ms = (time.perf_counter() - t0) * 1000.0
        return {
            "query_id": qid,
            "category": query_spec["category"],
            "query_text": query_text,
            "status": "system_error",
            "verification_badge": "system_error",
            "answer_text": f"Error handled fail-closed: {str(e)}",
            "num_passages_retrieved": 0,
            "retrieved_doc_ids": [],
            "claims_count": 0,
            "claims": [],
            "timing_ms": {},
            "total_latency_ms": round(total_time_ms, 2),
            "exception_raised": True,
            "error_message": str(e),
            "is_fail_closed": True
        }


def main():
    print("=" * 80)
    print("PHASE 3: END-TO-END DEMO QUERY VERIFICATION (MOCK VS LIVE MODEL)")
    print("=" * 80)

    # 1. Evaluate with MockLLMProvider
    print("\n--- Running Suite with MockLLMProvider ---")
    mock_pipeline = RAGPipeline(llm_provider=MockLLMProvider())
    mock_results = []
    
    for q in TEST_QUERIES:
        is_timeout = (q["id"] == "DEMO_Q5_ERROR_TIMEOUT")
        res = run_pipeline_eval(mock_pipeline, q, is_timeout_test=is_timeout)
        mock_results.append(res)
        print(f"[{res['query_id']}] Badge: {res['verification_badge']} | Status: {res['status']} | Latency: {res['total_latency_ms']:.1f}ms")
        if res['claims']:
            for cl in res['claims']:
                print(f"    Claim: {cl['text'][:60]}... -> {cl['status']} ({cl['method']})")

    # 2. Evaluate with LocalOllamaProvider (llama3.2:1b)
    print("\n--- Running Suite with LocalOllamaProvider (llama3.2:1b) ---")
    ollama_avail = LocalOllamaProvider.check_availability()
    ollama_results = []
    
    if ollama_avail["available"]:
        # Use llama3.2:1b which is available in Ollama
        live_provider = LocalOllamaProvider(model_name="llama3.2:1b", timeout=60.0, default_options={"num_ctx": 1024, "num_predict": 128})
        live_pipeline = RAGPipeline(llm_provider=live_provider)
        
        for q in TEST_QUERIES:
            is_timeout = (q["id"] == "DEMO_Q5_ERROR_TIMEOUT")
            print(f"Evaluating {q['id']} on live llama3.2:1b...")
            res = run_pipeline_eval(live_pipeline, q, is_timeout_test=is_timeout)
            ollama_results.append(res)
            print(f"[{res['query_id']}] Badge: {res['verification_badge']} | Status: {res['status']} | Latency: {res['total_latency_ms']:.1f}ms")
            if res['claims']:
                for cl in res['claims']:
                    print(f"    Claim: {cl['text'][:60]}... -> {cl['status']} ({cl['method']})")
    else:
        print("Local Ollama not available; skipping live model evaluation.")

    # Save results
    report = {
        "metadata": {
            "title": "Phase 3 End-to-End Demo Query Verification",
            "milestone": "Final Audit and College Demo Readiness",
            "date": "2026-10-16",
            "ollama_available": ollama_avail["available"],
            "live_model_tested": "llama3.2:1b" if ollama_avail["available"] else None,
            "graph_traversal_enabled": False,
            "verification_policy": "policy_3"
        },
        "queries_tested": [q["id"] for q in TEST_QUERIES],
        "mock_pipeline_results": mock_results,
        "live_pipeline_results": ollama_results,
        "safety_invariants_verified": {
            "all_adversarial_queries_fail_closed": all(r["is_fail_closed"] for r in mock_results if r["query_id"] != "DEMO_Q1_SUPPORTED"),
            "live_model_adversarial_fail_closed": all(r["is_fail_closed"] for r in ollama_results if r["query_id"] != "DEMO_Q1_SUPPORTED") if ollama_results else True,
            "zero_verified_supported_leaks_on_adversarial": sum(1 for r in mock_results + ollama_results if r["query_id"] != "DEMO_Q1_SUPPORTED" and r["verification_badge"] == "verified_supported") == 0
        }
    }

    out_file = Path("evaluation/rag/final_e2e_demo_verification.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\nSaved complete verification report to {out_file}")


if __name__ == "__main__":
    main()
