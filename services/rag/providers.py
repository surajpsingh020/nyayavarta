"""
LLM Provider Abstraction and Implementations for NyayaVarta RAG (Milestone 5A).

Provides:
1. Abstract LLMProvider interface.
2. MockLLMProvider for deterministic, zero-download, fast CPU testing and baseline evaluation.
3. LocalOllamaProvider for local CPU model execution (e.g., Llama 3.2 1B, Qwen 2.5 1.5B).
"""
import time
import json
import re
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field


class LLMResponse(BaseModel):
    """Normalized response from an LLM provider."""
    content: str = Field(..., description="Generated text response")
    model_name: str = Field(..., description="Identifier of the generating model")
    latency_ms: float = Field(..., ge=0.0, description="Latency in milliseconds")
    usage: Dict[str, Any] = Field(default_factory=dict, description="Token usage metadata")
    raw_response: Optional[Any] = Field(None, description="Raw provider response")


class LLMProvider(ABC):
    """Abstract interface for local language models."""

    @abstractmethod
    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 512,
        temperature: float = 0.0,
        structured_schema: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate text or structured JSON from a prompt."""
        pass


class MockLLMProvider(LLMProvider):
    """
    Deterministic mock provider for unit testing, reproducible benchmarks, and CPU execution.
    Synthesizes grounded answers directly from evidence passages without external model downloads.
    """
    MODE_NORMAL = "normal"
    MODE_FORCE_ABSTAIN = "force_abstain"
    MODE_HALLUCINATED_CITATION = "hallucinated_citation"
    MODE_MALFORMED = "malformed"
    MODE_UNSUPPORTED_CLAIM = "unsupported_claim"
    MODE_PARTIALLY_SUPPORTED = "partially_supported"

    # Milestone 7 Structured Output Modes
    MODE_STRUCTURED_NORMAL = "structured_normal"
    MODE_STRUCTURED_ABSTAIN = "structured_abstain"
    MODE_STRUCTURED_MALFORMED_JSON = "structured_malformed_json"
    MODE_STRUCTURED_MISSING_FIELDS = "structured_missing_fields"
    MODE_STRUCTURED_UNEXPECTED_EID = "structured_unexpected_eid"
    MODE_STRUCTURED_STALE_EID = "structured_stale_eid"
    MODE_STRUCTURED_UNCITED_CLAIM = "structured_uncited_claim"
    MODE_STRUCTURED_PARTIALLY_SUPPORTED = "structured_partially_supported"

    def __init__(self, mode: str = MODE_NORMAL, model_name: str = "mock-grounded-cpu-v1"):
        self.mode = mode
        self.model_name = model_name

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 512,
        temperature: float = 0.0,
        structured_schema: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> LLMResponse:
        t0 = time.perf_counter()

        is_structured = structured_schema is not None or self.mode.startswith("structured_")

        # Handle specific structured test modes
        if self.mode == self.MODE_STRUCTURED_ABSTAIN or (is_structured and self.mode == self.MODE_FORCE_ABSTAIN):
            content = json.dumps({
                "status": "abstain",
                "claims": [],
                "abstention_reason": "The retrieved judicial passages do not provide sufficient evidence to answer this question."
            })
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            return LLMResponse(content=content, model_name=self.model_name, latency_ms=elapsed_ms)

        if self.mode == self.MODE_STRUCTURED_MALFORMED_JSON or (is_structured and self.mode == self.MODE_MALFORMED):
            content = '{"status": "answer", "claims": [{"text": "Incomplete json'
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            return LLMResponse(content=content, model_name=self.model_name, latency_ms=elapsed_ms)

        if self.mode == self.MODE_STRUCTURED_MISSING_FIELDS:
            content = json.dumps({
                "claims": [{"text": "Missing status and evidence_ids"}]
            })
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            return LLMResponse(content=content, model_name=self.model_name, latency_ms=elapsed_ms)

        if self.mode == self.MODE_STRUCTURED_UNEXPECTED_EID or (is_structured and self.mode == self.MODE_HALLUCINATED_CITATION):
            content = json.dumps({
                "status": "answer",
                "claims": [
                    {
                        "text": "Specific performance requires readiness under Section 16 of Specific Relief Act.",
                        "evidence_ids": ["E1"]
                    },
                    {
                        "text": "Appeals may be dismissed under hypothetical doctrines.",
                        "evidence_ids": ["E99"]
                    }
                ]
            })
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            return LLMResponse(content=content, model_name=self.model_name, latency_ms=elapsed_ms)

        if self.mode == self.MODE_STRUCTURED_STALE_EID:
            content = json.dumps({
                "status": "answer",
                "claims": [
                    {
                        "text": "Power of this Court u/Art.142 to do substantial justice applies.",
                        "evidence_ids": ["E2"]
                    }
                ]
            })
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            return LLMResponse(content=content, model_name=self.model_name, latency_ms=elapsed_ms)

        if self.mode == self.MODE_STRUCTURED_UNCITED_CLAIM or (is_structured and self.mode == self.MODE_UNSUPPORTED_CLAIM):
            content = json.dumps({
                "status": "answer",
                "claims": [
                    {
                        "text": "Under the Specific Relief Act, time is not presumptively of the essence.",
                        "evidence_ids": ["E1"]
                    },
                    {
                        "text": "Furthermore, parties always receive compensation regardless of delay.",
                        "evidence_ids": []
                    }
                ]
            })
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            return LLMResponse(content=content, model_name=self.model_name, latency_ms=elapsed_ms)

        if self.mode == self.MODE_STRUCTURED_PARTIALLY_SUPPORTED or (is_structured and self.mode == self.MODE_PARTIALLY_SUPPORTED):
            content = json.dumps({
                "status": "answer",
                "claims": [
                    {
                        "text": "The authorized officer can unilaterally extend the 15-day period for deposit of 75% purchase money under SARFAESI Rule 9(4) without consent of the borrower.",
                        "evidence_ids": ["E1"]
                    }
                ]
            })
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            return LLMResponse(content=content, model_name=self.model_name, latency_ms=elapsed_ms)

        # Handle specific free-form test modes
        if self.mode == self.MODE_FORCE_ABSTAIN:
            content = "INSUFFICIENT EVIDENCE: The retrieved judicial passages do not provide sufficient evidence to answer this question."
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            return LLMResponse(content=content, model_name=self.model_name, latency_ms=elapsed_ms)

        if self.mode == self.MODE_MALFORMED:
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            return LLMResponse(content="", model_name=self.model_name, latency_ms=elapsed_ms)

        if self.mode == self.MODE_HALLUCINATED_CITATION:
            content = "According to the Supreme Court, specific performance requires readiness [E1], but appeals may be dismissed under hypothetical doctrines [E99]."
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            return LLMResponse(content=content, model_name=self.model_name, latency_ms=elapsed_ms)

        if self.mode == self.MODE_UNSUPPORTED_CLAIM:
            content = "Under the Specific Relief Act, time is not presumptively of the essence [E1]. Furthermore, parties always receive compensation regardless of delay."
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            return LLMResponse(content=content, model_name=self.model_name, latency_ms=elapsed_ms)

        if self.mode == self.MODE_PARTIALLY_SUPPORTED:
            content = "The authorized officer can unilaterally extend the 15-day period for deposit of 75% purchase money under SARFAESI Rule 9(4) without consent of the borrower. [E1]"
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            return LLMResponse(content=content, model_name=self.model_name, latency_ms=elapsed_ms)

        # MODE_NORMAL: Extract evidence passages from prompt
        evidence_pattern = re.compile(r'\[(E\d+)\] Case: ([^\n]+)\nPassage Text:\s*"([^"]+)"', re.DOTALL)
        matches = evidence_pattern.findall(prompt)

        # Check if question exists
        q_match = re.search(r'=== USER QUESTION ===\s*([^\n]+)', prompt)
        question = q_match.group(1).strip() if q_match else ""

        def _make_abstain_response():
            if is_structured:
                cnt = json.dumps({
                    "status": "abstain",
                    "claims": [],
                    "abstention_reason": "The retrieved judicial passages do not provide sufficient evidence to answer this question."
                })
            else:
                cnt = "INSUFFICIENT EVIDENCE: The retrieved judicial passages do not provide sufficient evidence to answer this question."
            el_ms = (time.perf_counter() - t0) * 1000.0
            return LLMResponse(content=cnt, model_name=self.model_name, latency_ms=el_ms)

        if not matches or "No evidence passages available." in prompt:
            return _make_abstain_response()

        # Inspect salient token overlap between question and passages
        legal_generic_terms = {
            "court", "courts", "judgment", "judgments", "appeal", "appeals",
            "appellant", "appellants", "respondent", "respondents", "under", "section",
            "sections", "high", "supreme", "bench", "order", "orders", "held", "stated",
            "case", "cases", "learned", "counsel", "counsels", "matter", "matters",
            "passed", "versus", "state", "union", "india", "decision", "decisions",
            "ground", "grounds", "trial", "civil", "criminal", "petition", "petitions",
            "writ", "writs", "article", "articles", "rule", "rules", "act", "acts",
            "provision", "provisions", "whether", "which", "there", "their", "about",
            "these", "those", "would", "could", "should", "shall", "having", "being",
            "where", "while", "after", "before", "between", "against", "cannot", "party", "parties",
            "digital", "reports", "indian", "para", "paras", "record", "records",
            "what", "were", "when", "does", "have", "been", "with", "from", "into",
            "such", "also", "only", "other", "some", "same", "view",
            "statutory", "procedure", "jurisdiction", "standard", "standards", "requirements",
            "right", "rights", "duty", "duties", "power", "powers", "regarding",
            "judge", "judges", "bench", "benches", "constitution", "constitutional",
            "doctrine", "doctrines", "amendment", "amendments"
        }
        q_tokens_all = set(re.findall(r'\b[a-z0-9]{4,}\b', question.lower()))
        q_salient = {tok for tok in q_tokens_all if tok not in legal_generic_terms}
        if not q_salient:
            q_salient = q_tokens_all

        # Require focal provisions or calendar years to be covered in evidence
        q_provisions = set(re.findall(r'\b(?:section|article|rule|order)\s+(\d+[a-z]?)\b', question.lower()))
        q_years = set(re.findall(r'\b(19\d\d|20[0-2]\d)\b', question))
        focal_tokens = q_provisions.union(q_years)

        best_passage = None
        best_eid = None
        best_overlap_tokens = set()
        best_has_focal = False

        def _token_matches(tok: str, p_toks: set, p_lower: str) -> bool:
            if tok in p_toks or tok in p_lower:
                return True
            if len(tok) > 3 and tok.endswith('s') and tok[:-1] in p_toks:
                return True
            if len(tok) > 4 and tok.endswith('ed') and tok[:-2] in p_toks:
                return True
            if len(tok) > 4 and tok.endswith('ing') and tok[:-3] in p_toks:
                return True
            variants = {
                "grant": ["granted", "grants", "granting"],
                "admission": ["admit", "admitted", "admitting", "admission"],
                "exercise": ["exercised", "exercises", "exercising"],
                "signatory": ["signatories", "signs", "signed"],
                "cheque": ["cheques"],
                "holding": ["hold", "held", "holds"],
                "precedent": ["precedents"]
            }
            if tok in variants:
                if any(v in p_toks or v in p_lower for v in variants[tok]):
                    return True
            for root, vars_list in variants.items():
                if tok in vars_list:
                    if root in p_toks or root in p_lower or any(v in p_toks or v in p_lower for v in vars_list):
                        return True
            return False

        for eid, case_header, p_text in matches:
            p_tokens = set(re.findall(r'\b[a-z0-9]{3,}\b', p_text.lower()))
            overlap = {tok for tok in q_salient if _token_matches(tok, p_tokens, p_text.lower())}
            has_focal = bool(focal_tokens and any(tok in p_text.lower() for tok in focal_tokens))

            # Prioritize passages covering focal statutory provisions or years
            is_better = False
            if best_passage is None:
                is_better = True
            elif focal_tokens and has_focal and not best_has_focal:
                is_better = True
            elif focal_tokens and not has_focal and best_has_focal:
                is_better = False
            elif len(overlap) > len(best_overlap_tokens):
                is_better = True

            if is_better:
                best_overlap_tokens = overlap
                best_passage = p_text
                best_eid = eid
                best_has_focal = has_focal

        overlap_ratio = len(best_overlap_tokens) / len(q_salient) if q_salient else 0.0

        # If salient overlap is weak (< 3 matching salient concepts and < 40% query concepts), abstain
        if (len(best_overlap_tokens) < 3 and overlap_ratio < 0.40) or not best_passage:
            return _make_abstain_response()

        if focal_tokens:
            p_text_lower = best_passage.lower()
            if not any(tok in p_text_lower for tok in focal_tokens):
                return _make_abstain_response()

        # Relational check: If question connects a subject to a target predicate (establish/bar/permit),
        # verify predicate terms are present in the best passage
        rel_match = re.split(r'\b(?:establish\s+that|establish|automatically\s+bar|permit|applies\s+to)\b', question, flags=re.IGNORECASE)
        if len(rel_match) == 2:
            pred_tokens = set(re.findall(r'\b[a-z0-9]{4,}\b', rel_match[1].lower())) - legal_generic_terms
            if pred_tokens:
                p_text_lower = best_passage.lower()
                pred_covered = [t for t in pred_tokens if t in p_text_lower]
                if not pred_covered:
                    return _make_abstain_response()


        # Grounded extraction synthesis:
        # Require candidate sentences to contain multiple salient overlap tokens for genuine grounding
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', best_passage) if len(s.strip()) > 30]
        extracted_points = []
        for s in sentences:
            s_lower = s.lower()
            if any(m in s_lower for m in ["case law cited", "cases cited", "authorities cited", "cases referred", "list of acts"]):
                continue
            s_tokens = set(re.findall(r'\b[a-z0-9]{3,}\b', s_lower))
            matched_salient = {tok for tok in best_overlap_tokens if _token_matches(tok, s_tokens, s_lower)}
            if len(matched_salient) >= 2 or (len(matched_salient) >= 1 and len(best_overlap_tokens) <= 2):
                clean_s = re.sub(r'\s+', ' ', s).strip()
                extracted_points.append(clean_s)
                if len(extracted_points) >= 2:
                    break

        if not extracted_points:
            if is_structured:
                content = json.dumps({
                    "status": "abstain",
                    "claims": [],
                    "abstention_reason": "The retrieved judicial passages do not provide sufficient evidence to answer this question."
                })
            else:
                content = "INSUFFICIENT EVIDENCE: The retrieved judicial passages do not provide sufficient evidence to answer this question."
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            return LLMResponse(content=content, model_name=self.model_name, latency_ms=elapsed_ms)

        if is_structured:
            claims_data = [{"text": pt, "evidence_ids": [best_eid]} for pt in extracted_points]
            content = json.dumps({"status": "answer", "claims": claims_data})
        else:
            answer_lines = []
            for pt in extracted_points:
                answer_lines.append(f"{pt} [{best_eid}]")
            content = " ".join(answer_lines)

        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        return LLMResponse(
            content=content,
            model_name=self.model_name,
            latency_ms=elapsed_ms,
            usage={"prompt_tokens": len(prompt.split()), "completion_tokens": len(content.split())}
        )


class LocalOllamaProvider(LLMProvider):
    """
    Connects to local Ollama HTTP API (e.g. http://localhost:11434).
    Recommended for lightweight local models (e.g. llama3.2:1b, qwen2.5:3b, phi3.5:latest).
    """

    def __init__(
        self,
        model_name: str = "llama3.2:1b",
        base_url: str = "http://localhost:11434",
        timeout: float = 180.0,
        default_options: Optional[Dict[str, Any]] = None
    ):
        self.model_name = model_name
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.default_options = default_options or {"num_ctx": 2048, "num_predict": 320}

    @classmethod
    def check_availability(cls, base_url: str = "http://localhost:11434", model_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Check if Ollama service is reachable and query installed models.
        """
        import urllib.request
        import urllib.error
        try:
            req = urllib.request.Request(
                f"{base_url.rstrip('/')}/api/tags",
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                models = [m.get("name", "") for m in data.get("models", [])]
                target_installed = (model_name in models) if model_name else (len(models) > 0)
                return {
                    "available": True,
                    "models": models,
                    "target_model_installed": target_installed,
                    "error": None
                }
        except Exception as e:
            return {
                "available": False,
                "models": [],
                "target_model_installed": False,
                "error": str(e)
            }

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 512,
        temperature: float = 0.0,
        options: Optional[Dict[str, Any]] = None,
        structured_schema: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> LLMResponse:
        import urllib.request
        import urllib.error
        import socket

        t0 = time.perf_counter()
        merged_options = dict(self.default_options)
        merged_options["temperature"] = temperature
        merged_options["num_predict"] = max_tokens
        if options:
            merged_options.update(options)

        payload: Dict[str, Any] = {
            "model": self.model_name,
            "prompt": prompt,
            "system": system_prompt or "",
            "stream": False,
            "options": merged_options
        }

        # Apply structured output schema constraint if provided
        active_format = structured_schema or (options.get("format") if options else None)
        if active_format:
            payload["format"] = active_format

        req = urllib.request.Request(
            f"{self.base_url}/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                content = data.get("response", "").strip()
                elapsed_ms = (time.perf_counter() - t0) * 1000.0

                eval_count = data.get("eval_count", 0)
                eval_duration_ns = data.get("eval_duration", 0)
                prompt_eval_count = data.get("prompt_eval_count", 0)
                prompt_eval_duration_ns = data.get("prompt_eval_duration", 0)
                load_duration_ns = data.get("load_duration", 0)
                total_duration_ns = data.get("total_duration", 0)

                eval_sec = eval_duration_ns / 1e9 if eval_duration_ns > 0 else 0.0
                prompt_eval_sec = prompt_eval_duration_ns / 1e9 if prompt_eval_duration_ns > 0 else 0.0

                tokens_per_sec = round(eval_count / eval_sec, 2) if eval_sec > 0 else 0.0
                prompt_tokens_per_sec = round(prompt_eval_count / prompt_eval_sec, 2) if prompt_eval_sec > 0 else 0.0

                usage_meta = {
                    "prompt_eval_count": prompt_eval_count,
                    "prompt_eval_ms": round(prompt_eval_duration_ns / 1e6, 2),
                    "eval_count": eval_count,
                    "eval_duration_ms": round(eval_duration_ns / 1e6, 2),
                    "load_duration_ms": round(load_duration_ns / 1e6, 2),
                    "total_duration_ms": round(total_duration_ns / 1e6, 2),
                    "tokens_per_second": tokens_per_sec,
                    "prompt_tokens_per_second": prompt_tokens_per_sec
                }

                return LLMResponse(
                    content=content,
                    model_name=self.model_name,
                    latency_ms=elapsed_ms,
                    usage=usage_meta,
                    raw_response=data
                )
        except (TimeoutError, socket.timeout):
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            raise TimeoutError(
                f"Local Ollama generation timed out after {self.timeout}s on model '{self.model_name}' (elapsed: {elapsed_ms:.1f}ms)."
            )
        except urllib.error.URLError as e:
            raise RuntimeError(
                f"Local Ollama service unreachable at {self.base_url} for model '{self.model_name}': {e}. "
                "Ensure Ollama daemon is running or specify provider_type='mock'."
            )


def get_llm_provider(provider_type: str = "mock", **kwargs) -> LLMProvider:
    """Factory creating configured LLM provider."""
    p_type = provider_type.lower()
    if p_type in ["mock", "mock_partial"]:
        default_mode = MockLLMProvider.MODE_PARTIALLY_SUPPORTED if p_type == "mock_partial" else MockLLMProvider.MODE_NORMAL
        mode = kwargs.get("mode", default_mode)
        return MockLLMProvider(mode=mode)
    elif p_type in ["ollama", "local"]:
        model = kwargs.get("model_name", "llama3.2:1b")
        url = kwargs.get("base_url", "http://localhost:11434")
        timeout = kwargs.get("timeout", 180.0)
        options = kwargs.get("default_options")
        return LocalOllamaProvider(model_name=model, base_url=url, timeout=timeout, default_options=options)
    else:
        raise ValueError(f"Unknown provider_type '{provider_type}'. Supported: 'mock', 'ollama'.")
