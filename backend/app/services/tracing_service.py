"""LLMOps Tracing & Observability Service for Nyayavarta Legal AI.

Supports:
1. Structured Trace Telemetry (Latency, Token Estimation, Retrieval Breakdown, Guardrails Status)
2. Local Persistent Telemetry Log (/app/logs/llmops_traces.jsonl)
3. Online Aggregate Quality & Error Metrics
"""

import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

logger = logging.getLogger("llmops_tracing")

LOGS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "logs")
TRACE_LOG_PATH = os.path.join(LOGS_DIR, "llmops_traces.jsonl")


class TraceSpan:
    """Represents a discrete execution span within an LLMOps trace."""
    def __init__(self, name: str):
        self.name = name
        self.start_time = 0.0
        self.end_time = 0.0
        self.duration_ms = 0.0
        self.metadata: Dict[str, Any] = {}

    def start(self):
        self.start_time = time.time()
        return self

    def stop(self, metadata: Optional[Dict[str, Any]] = None):
        self.end_time = time.time()
        self.duration_ms = round((self.end_time - self.start_time) * 1000, 2)
        if metadata:
            self.metadata.update(metadata)
        return self


class LLMTrace:
    """Complete lifecycle trace for an individual citizen legal consultation."""
    def __init__(
        self,
        trace_id: Optional[str] = None,
        user_id: Optional[str] = None,
        thread_id: Optional[str] = None,
        query: str = ""
    ):
        self.trace_id = trace_id or str(uuid.uuid4())
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.user_id = user_id
        self.thread_id = thread_id
        self.query = query
        self.sanitized_query = query
        self.guardrail_status = "PASSED"
        self.guardrail_redactions: List[str] = []
        self.spans: Dict[str, TraceSpan] = {}
        self.retrieved_sections: List[str] = []
        self.citations: List[Dict[str, Any]] = []
        self.response_text: str = ""
        self.model_name: str = "gemini-3.5-flash-lite"
        self.token_usage: Dict[str, int] = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        self.eval_scores: Dict[str, float] = {}
        self.error: Optional[str] = None

    def start_span(self, name: str) -> TraceSpan:
        span = TraceSpan(name).start()
        self.spans[name] = span
        return span

    def stop_span(self, name: str, metadata: Optional[Dict[str, Any]] = None):
        if name in self.spans:
            self.spans[name].stop(metadata)

    def to_dict(self) -> Dict[str, Any]:
        span_durations = {name: span.duration_ms for name, span in self.spans.items()}
        total_latency = sum(span_durations.values())
        return {
            "trace_id": self.trace_id,
            "timestamp": self.timestamp,
            "user_id": self.user_id,
            "thread_id": self.thread_id,
            "query": self.query,
            "sanitized_query": self.sanitized_query,
            "guardrail_status": self.guardrail_status,
            "guardrail_redactions": self.guardrail_redactions,
            "latency_ms": {
                "total": round(total_latency, 2),
                "breakdown": span_durations,
            },
            "retrieved_sections": self.retrieved_sections,
            "citations_count": len(self.citations),
            "model_name": self.model_name,
            "token_usage": self.token_usage,
            "eval_scores": self.eval_scores,
            "error": self.error,
        }


class TracingService:
    """Singleton LLMOps telemetry logger and exporter."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TracingService, cls).__new__(cls)
            cls._instance._init_service()
        return cls._instance

    def _init_service(self):
        os.makedirs(LOGS_DIR, exist_ok=True)

    def record_trace(self, trace: LLMTrace):
        """Persists the trace locally in structured JSONL format."""
        trace_data = trace.to_dict()

        # Local JSONL Persistence
        try:
            with open(TRACE_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(trace_data, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"Failed to write local trace log: {e}")

    def get_recent_traces(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Reads recent traces from the JSONL log."""
        if not os.path.exists(TRACE_LOG_PATH):
            return []
        traces = []
        try:
            with open(TRACE_LOG_PATH, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        try:
                            traces.append(json.loads(line.strip()))
                        except Exception:
                            continue
        except Exception as e:
            logger.error(f"Error reading trace log: {e}")
        return traces[-limit:]

    def get_telemetry_metrics(self) -> Dict[str, Any]:
        """Calculates aggregate metrics over recorded traces."""
        traces = self.get_recent_traces(limit=200)
        if not traces:
            return {
                "total_queries": 0,
                "avg_latency_ms": 0.0,
                "guardrail_redaction_rate": "0.0%",
                "error_rate": "0.0%",
            }

        total = len(traces)
        total_lat = sum(t.get("latency_ms", {}).get("total", 0.0) for t in traces)
        redacted = sum(1 for t in traces if t.get("guardrail_status") == "PII_REDACTED")
        errors = sum(1 for t in traces if t.get("error") is not None)

        return {
            "total_queries": total,
            "avg_latency_ms": round(total_lat / total, 2),
            "guardrail_redactions": redacted,
            "guardrail_redaction_rate": f"{round((redacted / total) * 100, 1)}%",
            "error_rate": f"{round((errors / total) * 100, 1)}%",
        }


def get_tracing_service() -> TracingService:
    return TracingService()
