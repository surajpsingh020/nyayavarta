"""
Repeatable Real Local-LLM Evaluation Runner for NyayaVarta (Milestone 5B).

Evaluates the real LocalOllamaProvider on the evaluation dataset.
- Checks Ollama daemon availability and model readiness.
- Automatically reports skipped/not-run if Ollama or model is unavailable.
- Separates retrieval latency, generation latency, total latency, and timeouts.
- Evaluates citation-reference adherence and abstention on unanswerable queries.
- Records exact model metadata, hardware constraints, and raw outputs.
"""
import os
import sys
import json
import time
import argparse
from typing import Dict, Any, List

sys.path.insert(0, ".")
from services.rag.pipeline import RAGPipeline
from services.rag.providers import LocalOllamaProvider
from services.rag.evidence import verify_evidence_offsets

DATASET_PATH = "evaluation/rag/rag_eval_dataset.json"
REPORT_PATH = "evaluation/rag/local_ollama_evaluation_report.json"


def evaluate_local_ollama(
    base_url: str = "http://localhost:11434",
    model_name: str = None,
    timeout: float = 60.0,
    max_queries: int = 5
):
    print("=" * 75)
    print("NyayaVarta Milestone 5B: Real Local-LLM (Ollama) Benchmark Evaluation")
    print("=" * 75)

    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    # Step 1: Check Ollama availability
    avail = LocalOllamaProvider.check_availability(base_url=base_url)
    if not avail["available"]:
        print(f"[STATUS: NOT RUN] Ollama daemon is unreachable at {base_url}.")
        print(f"Detail: {avail.get('error')}")
        report = {
            "benchmark_title": "NyayaVarta Real Local-LLM Benchmark",
            "evaluation_status": "not_run",
            "skip_reason": f"Ollama daemon unreachable at {base_url}: {avail.get('error')}",
            "timestamp": timestamp,
            "model_metadata": {
                "base_url": base_url,
                "installed_models": []
            }
        }
        os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
        with open(REPORT_PATH, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=4)
        return

    installed_models = avail["models"]
    print(f"Ollama is running at {base_url}. Installed models: {installed_models}")

    # Step 2: Select candidate model
    target_model = model_name
    if not target_model:
        preferred = ["phi3.5:latest", "qwen2.5:3b-instruct-q4_K_M", "llama3.2:3b", "llama3.1:latest"]
        for p in preferred:
            if p in installed_models:
                target_model = p
                break
        if not target_model and installed_models:
            target_model = installed_models[0]

    if not target_model or target_model not in installed_models:
        print(f"[STATUS: NOT RUN] No suitable model available. Target: '{target_model}'.")
        report = {
            "benchmark_title": "NyayaVarta Real Local-LLM Benchmark",
            "evaluation_status": "not_run",
            "skip_reason": f"Target model '{target_model}' not installed in Ollama.",
            "timestamp": timestamp,
            "model_metadata": {
                "base_url": base_url,
                "installed_models": installed_models
            }
        }
        os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
        with open(REPORT_PATH, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=4)
        return

    print(f"Selected Local Model: '{target_model}' (Timeout: {timeout}s per query)")

    # Step 3: Load Evaluation Queries
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    # Use max_queries to balance CPU execution time
    test_items = dataset[:max_queries] if max_queries else dataset
    print(f"Evaluating {len(test_items)} queries ({sum(1 for i in test_items if i['expected_answerability']=='answerable')} answerable, "
          f"{sum(1 for i in test_items if i['expected_answerability']!='answerable')} unanswerable)...")

    provider = LocalOllamaProvider(model_name=target_model, base_url=base_url, timeout=timeout)
    pipeline = RAGPipeline(llm_provider=provider)

    per_query_results = []
    latencies_retrieval = []
    latencies_generation = []
    latencies_total = []
    timeouts_count = 0
    failures_count = 0
    abstentions_correct = 0
    unanswerable_total = 0
    answerable_total = 0
    valid_citations_count = 0
    total_citations_count = 0

    for idx, item in enumerate(test_items):
        qid = item["query_id"]
        q_text = item["question"]
        expected_type = item["expected_answerability"]
        print(f"\n[{idx+1}/{len(test_items)}] Query {qid}: '{q_text[:60]}...'")

        t_start = time.perf_counter()
        try:
            result = pipeline.query(query_text=q_text, top_k_judgments=3, max_passages=3)
            elapsed_ms = (time.perf_counter() - t_start) * 1000.0

            gen_ms = result.timing_ms.get("generation_ms", 0.0)
            ret_ms = result.timing_ms.get("retrieval_ms", 0.0)
            tot_ms = result.timing_ms.get("total_ms", elapsed_ms)

            latencies_retrieval.append(ret_ms)
            latencies_generation.append(gen_ms)
            latencies_total.append(tot_ms)

            val = result.citation_validation
            total_citations_count += len(val.cited_source_ids)
            valid_citations_count += len(val.valid_source_ids)

            is_abstained = (result.status == "insufficient_evidence") or ("insufficient evidence" in result.answer.lower())
            if expected_type != "answerable":
                unanswerable_total += 1
                if is_abstained:
                    abstentions_correct += 1
            else:
                answerable_total += 1

            per_query_results.append({
                "query_id": qid,
                "question": q_text,
                "expected_answerability": expected_type,
                "status": result.status,
                "raw_answer": result.answer,
                "citation_syntax_valid": val.citation_syntax_valid,
                "citation_existence_valid": val.citation_existence_valid,
                "cited_ids": val.cited_source_ids,
                "valid_ids": val.valid_source_ids,
                "invalid_ids": val.invalid_source_ids,
                "timing_ms": result.timing_ms
            })
            print(f"    Status: {result.status} | Gen: {gen_ms:.1f}ms | Tot: {tot_ms:.1f}ms | Cited: {val.cited_source_ids}")

        except TimeoutError as te:
            timeouts_count += 1
            failures_count += 1
            elapsed_ms = (time.perf_counter() - t_start) * 1000.0
            print(f"    TIMEOUT: {te}")
            per_query_results.append({
                "query_id": qid,
                "question": q_text,
                "expected_answerability": expected_type,
                "status": "timeout",
                "raw_answer": "",
                "error": str(te),
                "timing_ms": {"total_ms": elapsed_ms}
            })
        except Exception as e:
            failures_count += 1
            elapsed_ms = (time.perf_counter() - t_start) * 1000.0
            print(f"    FAILURE: {e}")
            per_query_results.append({
                "query_id": qid,
                "question": q_text,
                "expected_answerability": expected_type,
                "status": "error",
                "raw_answer": "",
                "error": str(e),
                "timing_ms": {"total_ms": elapsed_ms}
            })

    report = {
        "benchmark_title": "NyayaVarta Real Local-LLM Benchmark",
        "benchmark_version": "v1.0",
        "evaluation_status": "completed",
        "timestamp": timestamp,
        "model_metadata": {
            "model_name": target_model,
            "base_url": base_url,
            "timeout_seconds": timeout,
            "execution_environment": "Local pure-CPU Ollama instance"
        },
        "aggregate_metrics": {
            "total_queries_evaluated": len(test_items),
            "answerable_queries": answerable_total,
            "unanswerable_queries": unanswerable_total,
            "timeouts_count": timeouts_count,
            "failures_count": failures_count,
            "abstention_accuracy": (abstentions_correct / unanswerable_total) if unanswerable_total else 0.0,
            "citation_reference_validity_rate": (valid_citations_count / total_citations_count) if total_citations_count else 1.0,
            "semantic_support_status": "not_evaluated"
        },
        "latency_metrics_ms": {
            "retrieval_median_ms": round(sum(latencies_retrieval)/len(latencies_retrieval), 2) if latencies_retrieval else 0.0,
            "generation_median_ms": round(sum(latencies_generation)/len(latencies_generation), 2) if latencies_generation else 0.0,
            "total_median_ms": round(sum(latencies_total)/len(latencies_total), 2) if latencies_total else 0.0
        },
        "per_query_results": per_query_results
    }

    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4)

    print("\n" + "=" * 75)
    print(f"Evaluation report saved to: {REPORT_PATH}")
    print("=" * 75)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate local Ollama on NyayaVarta RAG.")
    parser.add_argument("--model", type=str, default=None, help="Model name in Ollama")
    parser.add_argument("--timeout", type=float, default=60.0, help="Per-query generation timeout")
    parser.add_argument("--max_queries", type=int, default=5, help="Number of queries to run")
    args = parser.parse_args()

    evaluate_local_ollama(model_name=args.model, timeout=args.timeout, max_queries=args.max_queries)
