"""
Reproducible Controlled Local Inference Benchmark for NyayaVarta RAG (Milestone 5C).

Profiles local CPU Ollama inference performance across:
1. Workload 1: Short prompt + 1 evidence passage.
2. Workload 2: Representative prompt + 3 evidence passages.
3. Workload 3: Production long prompt + 3 full-length evidence passages.

Measures:
- Cold-start vs warm runs
- Model load time
- Prompt evaluation count, duration, and prompt tokens/second
- Generation token count, duration, and tokens/second
- Request latency vs timeout
- Safe configuration changes (num_predict limit, prompt compaction, num_ctx)
Outputs structured report to evaluation/rag/local_inference_benchmark_report.json.
"""
import os
import sys
import time
import json
import platform
import argparse
from typing import Dict, Any, List, Optional

sys.path.insert(0, ".")
from services.rag.providers import LocalOllamaProvider
from services.rag.models import EvidencePassage
from services.rag.prompt import SYSTEM_PROMPT, build_rag_prompt

REPORT_PATH = "evaluation/rag/local_inference_benchmark_report.json"


def get_hardware_info() -> Dict[str, Any]:
    """Capture host system hardware profile."""
    info = {
        "platform": platform.platform(),
        "processor": platform.processor(),
        "python_version": platform.python_version()
    }
    try:
        import psutil
        info["cpu_logical_cores"] = psutil.cpu_count(logical=True)
        info["cpu_physical_cores"] = psutil.cpu_count(logical=False)
        info["total_ram_gb"] = round(psutil.virtual_memory().total / (1024 ** 3), 2)
        info["available_ram_gb"] = round(psutil.virtual_memory().available / (1024 ** 3), 2)
    except ImportError:
        info["cpu_logical_cores"] = os.cpu_count()
    return info


def build_synthetic_passages(count: int, chars_per_passage: int) -> List[EvidencePassage]:
    """Construct representative evidence passages from actual Supreme Court judgments."""
    base_samples = [
        (
            "E1", "2024_10_393_410", "V. Senthil Balaji v. Directorate of Enforcement",
            "Under Section 45 of the Prevention of Money Laundering Act, the court before granting bail must be satisfied that there are reasonable grounds for believing that the accused is not guilty of the alleged offence and that he is not likely to commit any offence while on bail. However, prolonged incarceration coupled with absence of any possibility of trial concluding within a reasonable timeframe constitutes a violation of the fundamental right to speedy trial under Article 21 of the Constitution."
        ),
        (
            "E2", "2024_10_1359_1370", "Renjith K.G. & Others v. Sheeba",
            "Order XXI Rule 99 of the Code of Civil Procedure provides a statutory remedy to any person other than the judgment debtor who is dispossessed of immovable property by the decree holder or purchaser. The executing court under Rule 101 is mandated to determine all questions including right, title, and interest arising between the parties without relegating the stranger or pendente lite purchaser to an independent civil suit."
        ),
        (
            "E3", "2024_10_1462_1474", "Vidyasagar Prasad v. UCO Bank & Anr.",
            "An unequivocal acknowledgement of liability recorded in the duly audited balance sheet of a corporate debtor constitutes an acknowledgement of debt under Section 18 of the Limitation Act, 1963. Such acknowledgement enures to the benefit of financial creditors and extends the limitation period of three years for instituting Corporate Insolvency Resolution Process under Section 7 of the Insolvency and Bankruptcy Code."
        )
    ]

    passages = []
    for i in range(count):
        eid, doc_id, title, text = base_samples[i % len(base_samples)]
        p_text = (text + " ") * (chars_per_passage // len(text) + 1)
        p_text = p_text[:chars_per_passage].strip()
        passages.append(EvidencePassage(
            evidence_id=f"E{i+1}",
            document_id=doc_id,
            case_title=title,
            passage_text=p_text,
            start_char=100 * i,
            end_char=100 * i + len(p_text),
            judgment_rank=i + 1,
            judgment_score=0.9 - 0.1 * i,
            passage_score=0.85
        ))
    return passages


def run_single_inference_test(
    provider: LocalOllamaProvider,
    prompt: str,
    max_tokens: int,
    temperature: float = 0.0,
    options: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Execute a single inference request and measure all dimensions."""
    t0 = time.perf_counter()
    result = {
        "status": "pending",
        "total_wall_ms": 0.0,
        "load_duration_ms": 0.0,
        "prompt_tokens": 0,
        "prompt_eval_ms": 0.0,
        "prompt_tokens_per_sec": 0.0,
        "generation_tokens": 0,
        "generation_eval_ms": 0.0,
        "tokens_per_sec": 0.0,
        "content_length": 0,
        "answer_preview": "",
        "error": None
    }

    try:
        resp = provider.generate(
            prompt=prompt,
            system_prompt=SYSTEM_PROMPT,
            max_tokens=max_tokens,
            temperature=temperature,
            options=options
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        result["status"] = "success"
        result["total_wall_ms"] = round(elapsed_ms, 2)
        usage = resp.usage or {}
        result["load_duration_ms"] = usage.get("load_duration_ms", 0.0)
        result["prompt_tokens"] = usage.get("prompt_eval_count", 0)
        result["prompt_eval_ms"] = usage.get("prompt_eval_ms", 0.0)
        result["prompt_tokens_per_sec"] = usage.get("prompt_tokens_per_second", 0.0)
        result["generation_tokens"] = usage.get("eval_count", 0)
        result["generation_eval_ms"] = usage.get("eval_duration_ms", 0.0)
        result["tokens_per_sec"] = usage.get("tokens_per_second", 0.0)
        result["content_length"] = len(resp.content)
        result["answer_preview"] = resp.content[:160].replace("\n", " ") + "..."
    except TimeoutError as te:
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        result["status"] = "timeout"
        result["total_wall_ms"] = round(elapsed_ms, 2)
        result["error"] = str(te)
    except Exception as e:
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        result["status"] = "error"
        result["total_wall_ms"] = round(elapsed_ms, 2)
        result["error"] = str(e)

    return result


def benchmark_local_inference(
    base_url: str = "http://localhost:11434",
    model_name: str = "phi3.5:latest",
    timeout: float = 90.0,
    runs_per_workload: int = 2
) -> Dict[str, Any]:
    print("=" * 80)
    print("NyayaVarta Milestone 5C: Controlled Local Inference Benchmark")
    print("=" * 80)

    # 1. Hardware & System Profiling
    hw_info = get_hardware_info()
    print(f"Host: {hw_info.get('platform')}")
    print(f"Processor: {hw_info.get('processor')}")
    print(f"Logical Cores: {hw_info.get('cpu_logical_cores')} | RAM: {hw_info.get('total_ram_gb')} GB")

    # 2. Ollama Status
    avail = LocalOllamaProvider.check_availability(base_url=base_url)
    if not avail["available"]:
        print(f"[STATUS: NOT RUN] Ollama unreachable at {base_url}: {avail.get('error')}")
        report = {
            "status": "not_run",
            "reason": f"Ollama daemon unreachable: {avail.get('error')}",
            "hardware_info": hw_info
        }
        with open(REPORT_PATH, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        return report

    print(f"Ollama running at {base_url}. Installed models: {avail['models']}")
    target_model = model_name if model_name in avail["models"] else avail["models"][0]
    print(f"Target Model: {target_model} (Timeout: {timeout}s)")

    provider = LocalOllamaProvider(model_name=target_model, base_url=base_url, timeout=timeout)

    # 3. Workload Definitions
    workloads = [
        {
            "name": "Workload 1 (Short)",
            "description": "1 short question + 1 short evidence passage (~250 chars)",
            "query": "What are the twin conditions for bail under Section 45 PMLA?",
            "passages": build_synthetic_passages(count=1, chars_per_passage=250),
            "max_tokens": 128
        },
        {
            "name": "Workload 2 (Representative)",
            "description": "1 standard question + 3 representative evidence passages (~350 chars each)",
            "query": "Can an accused seek bail when there is prolonged delay in trial under special acts?",
            "passages": build_synthetic_passages(count=3, chars_per_passage=350),
            "max_tokens": 160
        },
        {
            "name": "Workload 3 (Production Long)",
            "description": "1 complex question + 3 full evidence passages (~900 chars each)",
            "query": "How do courts balance statutory restrictions against Article 21 in economic offences?",
            "passages": build_synthetic_passages(count=3, chars_per_passage=900),
            "max_tokens": 200
        }
    ]

    workload_results = []

    print("\n--- Running Standard Workload Experiments ---")
    for w in workloads:
        print(f"\n>> {w['name']}: {w['description']}")
        prompt = build_rag_prompt(query=w["query"], evidence_passages=w["passages"])
        prompt_words = len(prompt.split())
        print(f"   Prompt size: ~{len(prompt)} chars, ~{prompt_words} words")

        runs = []
        for r_idx in range(runs_per_workload):
            run_type = "Cold Start" if (w["name"].startswith("Workload 1") and r_idx == 0) else f"Run {r_idx+1} (Warm)"
            print(f"   [{run_type}] executing...", end=" ", flush=True)
            res = run_single_inference_test(
                provider=provider,
                prompt=prompt,
                max_tokens=w["max_tokens"],
                temperature=0.0
            )
            res["run_type"] = run_type
            res["run_index"] = r_idx + 1
            runs.append(res)
            if res["status"] == "success":
                print(f"OK in {res['total_wall_ms']}ms | Gen: {res['generation_tokens']} tok @ {res['tokens_per_sec']} t/s | Prompt: {res['prompt_tokens']} tok @ {res['prompt_tokens_per_sec']} t/s")
            elif res["status"] == "timeout":
                print(f"TIMEOUT after {res['total_wall_ms']}ms")
            else:
                print(f"ERROR: {res['error']}")

        workload_results.append({
            "workload": w["name"],
            "description": w["description"],
            "prompt_length_chars": len(prompt),
            "max_tokens_budget": w["max_tokens"],
            "runs": runs
        })

    # 4. Safe Configuration Experiments (on Workload 2)
    print("\n--- Running Safe Configuration Ablation Experiments ---")
    base_w = workloads[1]
    base_prompt = build_rag_prompt(query=base_w["query"], evidence_passages=base_w["passages"])

    config_variants = [
        {
            "variant_name": "Variant A: Output Budget 64 tokens",
            "prompt": base_prompt,
            "max_tokens": 64,
            "options": {"num_predict": 64, "num_ctx": 2048}
        },
        {
            "variant_name": "Variant B: Output Budget 128 tokens + num_ctx 1024",
            "prompt": base_prompt,
            "max_tokens": 128,
            "options": {"num_predict": 128, "num_ctx": 1024}
        },
        {
            "variant_name": "Variant C: Compact Evidence (max 200 chars/passage, 128 tokens)",
            "prompt": build_rag_prompt(query=base_w["query"], evidence_passages=base_w["passages"], max_chars_per_passage=200),
            "max_tokens": 128,
            "options": {"num_predict": 128, "num_ctx": 2048}
        }
    ]

    variant_results = []
    for var in config_variants:
        print(f"\n>> {var['variant_name']}")
        print(f"   Prompt size: ~{len(var['prompt'])} chars")
        res = run_single_inference_test(
            provider=provider,
            prompt=var["prompt"],
            max_tokens=var["max_tokens"],
            temperature=0.0,
            options=var["options"]
        )
        if res["status"] == "success":
            print(f"   OK in {res['total_wall_ms']}ms | Gen: {res['generation_tokens']} tok @ {res['tokens_per_sec']} t/s | Prompt eval: {res['prompt_eval_ms']}ms")
        else:
            print(f"   {res['status'].upper()}: {res.get('error')}")

        variant_results.append({
            "variant_name": var["variant_name"],
            "prompt_length_chars": len(var["prompt"]),
            "max_tokens": var["max_tokens"],
            "options": var["options"],
            "result": res
        })

    # 5. Compile Final Report
    report = {
        "benchmark_title": "NyayaVarta Milestone 5C Controlled Local Inference Benchmark",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "model_metadata": {
            "model_name": target_model,
            "base_url": base_url,
            "configured_timeout_seconds": timeout,
            "installed_models": avail["models"]
        },
        "hardware_profile": hw_info,
        "standard_workload_benchmarks": workload_results,
        "safe_configuration_ablations": variant_results
    }

    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"\nBenchmark completed. Report written to {REPORT_PATH}")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run controlled local inference benchmark.")
    parser.add_argument("--model", type=str, default="phi3.5:latest")
    parser.add_argument("--timeout", type=float, default=90.0)
    parser.add_argument("--runs", type=int, default=2)
    args = parser.parse_args()

    benchmark_local_inference(model_name=args.model, timeout=args.timeout, runs_per_workload=args.runs)
