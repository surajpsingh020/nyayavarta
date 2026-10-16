"""
Local Natural Language Inference (NLI) Verifier for NyayaVarta (Milestone 18).

Provides:
1. Local CPU inference using ONNX Runtime and Hugging Face Tokenizers.
2. Standard 3-way directional entailment: [contradiction, entailment, neutral].
3. Strict Premise (source passage) -> Hypothesis (generated claim) formulation.
4. Shadow mode evaluation ensuring NLI diagnostics never weaken production safety gates.
5. Safe fail-closed error handling for empty inputs, model unavailability, and edge cases.
"""
import os
import time
import logging
from typing import Dict, Any, Optional, List, Tuple
from pydantic import BaseModel, Field
import numpy as np

logger = logging.getLogger(__name__)

# Default model identifiers and file constants
DEFAULT_NLI_MODEL_ID = "cross-encoder/nli-deberta-v3-small"
DEFAULT_ONNX_FILENAME = "onnx/model_quint8_avx2.onnx"
FALLBACK_ONNX_FILENAME = "onnx/model.onnx"
DEFAULT_TOKENIZER_FILENAME = "tokenizer.json"
DEFAULT_MAX_LENGTH = 512

# Standard 3-class label mapping for cross-encoder/nli-deberta-v3-small
# id2label: {0: 'contradiction', 1: 'entailment', 2: 'neutral'}
NLI_LABELS = ["contradiction", "entailment", "neutral"]


class NLIClassificationResult(BaseModel):
    """Normalized result of an NLI inference pass over a premise-hypothesis pair."""
    label: str = Field(..., description="Predicted label: 'contradiction', 'entailment', 'neutral', or 'error'")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Softmax probability of the predicted class")
    probabilities: Dict[str, float] = Field(default_factory=dict, description="Softmax probabilities for each NLI class")
    raw_logits: List[float] = Field(default_factory=list, description="Raw unnormalized logits from the ONNX session")
    premise: str = Field(..., description="Premise text (source judicial passage)")
    hypothesis: str = Field(..., description="Hypothesis text (generated legal assertion)")
    model_name: str = Field(default=DEFAULT_NLI_MODEL_ID, description="Identifier of the NLI model")
    latency_ms: float = Field(default=0.0, description="CPU inference latency in milliseconds")
    is_uncertain: bool = Field(default=False, description="True if output is neutral or confidence is below threshold")
    error_message: Optional[str] = Field(default=None, description="Error details if inference failed")


class NLIShadowVerdict(BaseModel):
    """Diagnostic comparison between deterministic verifier status and NLI semantic prediction."""
    deterministic_status: str
    nli_label: str
    nli_confidence: float
    shadow_recommended_status: str
    has_disagreement: bool
    disagreement_type: Optional[str] = None
    audit_rationale: str


class LocalNLIVerifier:
    """
    Locally runnable NLI inference engine for claim-level verification feasibility.
    Operates on CPU via ONNX Runtime and Tokenizers.
    """

    def __init__(
        self,
        model_id: str = DEFAULT_NLI_MODEL_ID,
        onnx_filename: str = DEFAULT_ONNX_FILENAME,
        max_length: int = DEFAULT_MAX_LENGTH,
        confidence_threshold: float = 0.60,
        lazy_load: bool = False
    ):
        self.model_id = model_id
        self.onnx_filename = onnx_filename
        self.max_length = max_length
        self.confidence_threshold = confidence_threshold
        
        self._tokenizer = None
        self._session = None
        self._is_initialized = False
        self._initialization_error = None
        self._model_load_latency_ms = 0.0

        if not lazy_load:
            self._initialize()

    def _initialize(self) -> bool:
        """Download (if needed) and initialize ONNX session and tokenizer."""
        if self._is_initialized:
            return True

        t0 = time.perf_counter()
        try:
            from huggingface_hub import hf_hub_download
            from tokenizers import Tokenizer
            import onnxruntime as ort

            # Download or load from cache
            try:
                tok_path = hf_hub_download(repo_id=self.model_id, filename=DEFAULT_TOKENIZER_FILENAME)
            except Exception as e_tok:
                logger.warning(f"Failed to fetch tokenizer for {self.model_id}: {e_tok}")
                self._initialization_error = str(e_tok)
                return False

            try:
                model_path = hf_hub_download(repo_id=self.model_id, filename=self.onnx_filename)
            except Exception as e_mod:
                logger.info(f"Preferred ONNX file {self.onnx_filename} not found, trying fallback: {e_mod}")
                model_path = hf_hub_download(repo_id=self.model_id, filename=FALLBACK_ONNX_FILENAME)

            # Load tokenizer
            self._tokenizer = Tokenizer.from_file(tok_path)
            self._tokenizer.enable_truncation(max_length=self.max_length)

            # Load ONNX session on CPU with optimized settings
            sess_options = ort.SessionOptions()
            cpu_cnt = os.cpu_count() or 1
            sess_options.intra_op_num_threads = max(1, cpu_cnt // 2 if cpu_cnt > 2 else cpu_cnt)
            sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

            self._session = ort.InferenceSession(
                model_path,
                sess_options=sess_options,
                providers=["CPUExecutionProvider"]
            )
            self._is_initialized = True
            self._model_load_latency_ms = (time.perf_counter() - t0) * 1000.0
            logger.info(f"LocalNLIVerifier initialized {self.model_id} on CPU in {self._model_load_latency_ms:.1f}ms")
            return True

        except Exception as e:
            self._initialization_error = str(e)
            logger.warning(f"Could not initialize local NLI verifier: {e}")
            return False

    @property
    def is_available(self) -> bool:
        """Returns True if local NLI model is successfully loaded and ready on CPU."""
        if not self._is_initialized:
            self._initialize()
        return self._is_initialized and self._session is not None

    @property
    def model_load_latency_ms(self) -> float:
        return self._model_load_latency_ms

    def predict(self, premise: str, hypothesis: str) -> NLIClassificationResult:
        """
        Execute directional NLI inference:
        Premise (source text) -> Hypothesis (asserted claim).
        """
        p_clean = (premise or "").strip()
        h_clean = (hypothesis or "").strip()

        # Handle empty or invalid inputs gracefully
        if not p_clean or not h_clean:
            return NLIClassificationResult(
                label="neutral",
                confidence=0.0,
                probabilities={"contradiction": 0.0, "entailment": 0.0, "neutral": 1.0},
                raw_logits=[],
                premise=p_clean,
                hypothesis=h_clean,
                model_name=self.model_id,
                latency_ms=0.0,
                is_uncertain=True,
                error_message="Premise or hypothesis is empty."
            )

        if not self.is_available:
            return NLIClassificationResult(
                label="neutral",
                confidence=0.0,
                probabilities={"contradiction": 0.0, "entailment": 0.0, "neutral": 1.0},
                raw_logits=[],
                premise=p_clean,
                hypothesis=h_clean,
                model_name=self.model_id,
                latency_ms=0.0,
                is_uncertain=True,
                error_message=f"Model unavailable: {self._initialization_error}"
            )

        t0 = time.perf_counter()
        try:
            # Tokenize sequence pair: (premise, hypothesis)
            encoding = self._tokenizer.encode(p_clean, h_clean)
            input_ids = np.array([encoding.ids], dtype=np.int64)
            attention_mask = np.array([encoding.attention_mask], dtype=np.int64)

            feed_dict = {
                "input_ids": input_ids,
                "attention_mask": attention_mask
            }

            # Run ONNX inference
            outputs = self._session.run(None, feed_dict)
            logits = outputs[0][0]  # shape: [3]

            # Numerically stable softmax
            shift_logits = logits - np.max(logits)
            exp_logits = np.exp(shift_logits)
            probs = exp_logits / np.sum(exp_logits)

            pred_idx = int(np.argmax(probs))
            pred_label = NLI_LABELS[pred_idx]
            pred_conf = float(probs[pred_idx])

            probs_dict = {
                NLI_LABELS[i]: round(float(probs[i]), 4) for i in range(len(NLI_LABELS))
            }
            elapsed_ms = (time.perf_counter() - t0) * 1000.0

            # Consider output uncertain if neutral or confidence is low
            is_uncertain = (pred_label == "neutral") or (pred_conf < self.confidence_threshold)

            return NLIClassificationResult(
                label=pred_label,
                confidence=round(pred_conf, 4),
                probabilities=probs_dict,
                raw_logits=[round(float(x), 4) for x in logits],
                premise=p_clean,
                hypothesis=h_clean,
                model_name=self.model_id,
                latency_ms=round(elapsed_ms, 2),
                is_uncertain=is_uncertain,
                error_message=None
            )

        except Exception as e_inf:
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            logger.warning(f"NLI inference error: {e_inf}")
            return NLIClassificationResult(
                label="neutral",
                confidence=0.0,
                probabilities={"contradiction": 0.0, "entailment": 0.0, "neutral": 1.0},
                raw_logits=[],
                premise=p_clean,
                hypothesis=h_clean,
                model_name=self.model_id,
                latency_ms=round(elapsed_ms, 2),
                is_uncertain=True,
                error_message=str(e_inf)
            )

    def evaluate_shadow(
        self,
        claim: str,
        passage: str,
        deterministic_status: str,
        deterministic_method: Optional[str] = None
    ) -> NLIShadowVerdict:
        """
        Evaluate a claim against cited evidence in shadow mode.
        Compares deterministic output against NLI prediction and computes safe shadow recommendation.
        
        Strict Safety Contract:
        - NLI ALONE CANNOT PROMOTE A CLAIM TO SUPPORTED.
        - Neutral NLI is NEVER treated as support.
        - High-confidence contradiction from NLI acts as a warning or demotion signal against false support.
        - Deterministic contradictions and unsupported statuses are never overturned by NLI.
        """
        nli_res = self.predict(premise=passage, hypothesis=claim)
        n_label = nli_res.label
        n_conf = nli_res.confidence
        n_probs = nli_res.probabilities

        p_contra = n_probs.get("contradiction", 0.0)
        p_entail = n_probs.get("entailment", 0.0)
        p_neut = n_probs.get("neutral", 0.0)

        # Baseline: default recommendation preserves deterministic status
        rec_status = deterministic_status
        disagreement = False
        disagreement_type = None
        rationale = "Deterministic status preserved."

        # Scenario 1: Deterministic is CONTRADICTED
        if deterministic_status == "contradicted":
            # Never overturn deterministic contradiction
            rec_status = "contradicted"
            if n_label != "contradiction":
                disagreement = True
                disagreement_type = "deterministic_contradicted_nli_non_contradicted"
                rationale = f"Deterministic verifier found explicit negation/conflict; preserved 'contradicted' despite NLI {n_label}."
            else:
                rationale = "Both deterministic verifier and NLI confirm contradiction."

        # Scenario 2: Deterministic is UNSUPPORTED
        elif deterministic_status == "unsupported":
            rec_status = "unsupported"
            if n_label == "entailment" and n_conf >= self.confidence_threshold:
                disagreement = True
                disagreement_type = "deterministic_unsupported_nli_entailed"
                rationale = "Deterministic verifier found citation unrelated; preserved 'unsupported' (NLI cannot promote unrelated citation)."
            else:
                rationale = "Deterministic verifier found citation unrelated; NLI confirms absence of support."

        # Scenario 3: Deterministic is SUPPORTED
        elif deterministic_status == "supported":
            if p_contra >= 0.80:
                # NLI strongly detects contradiction in what deterministic heuristic considered supported
                rec_status = "contradicted"
                disagreement = True
                disagreement_type = "false_support_averted_by_nli_contradiction"
                rationale = f"Deterministic heuristic accepted holding, but NLI detected strong semantic contradiction (P={p_contra:.3f}). Demoted to 'contradicted'."
            elif n_label == "neutral" or p_entail < self.confidence_threshold:
                # NLI finds proposition neutral / not entailed by passage
                rec_status = "not_evaluated"
                disagreement = True
                disagreement_type = "false_support_averted_by_nli_neutral"
                rationale = f"Deterministic heuristic accepted holding via keyword overlap, but NLI shows absence of entailment (P_entail={p_entail:.3f}, P_neutral={p_neut:.3f}). Demoted safely to 'not_evaluated'."
            else:
                # Both agree on support
                rec_status = "supported"
                rationale = f"Deterministic holding entailment confirmed by NLI entailment (P={p_entail:.3f})."

        # Scenario 4: Deterministic is PARTIALLY_SUPPORTED or NOT_EVALUATED
        else:
            if p_contra >= 0.80:
                rec_status = "contradicted"
                disagreement = (deterministic_status != "contradicted")
                disagreement_type = "unverified_flagged_as_contradicted"
                rationale = f"Deterministic status was '{deterministic_status}', but NLI detected high-confidence contradiction (P={p_contra:.3f}). Demoted to 'contradicted'."
            elif n_label == "entailment" and p_entail >= self.confidence_threshold:
                # Disagreement noted, BUT CANNOT PROMOTE TO SUPPORTED IN PRODUCTION (Rule 8)
                rec_status = deterministic_status  # Preserved!
                disagreement = True
                disagreement_type = "nli_entailment_suppressed_by_safety_contract"
                rationale = f"NLI predicted entailment (P={p_entail:.3f}), but promotion to 'supported' is barred by shadow contract without deterministic confirmation."
            else:
                rec_status = deterministic_status
                rationale = f"Deterministic status '{deterministic_status}' preserved; NLI predicts '{n_label}' (uncertain)."

        return NLIShadowVerdict(
            deterministic_status=deterministic_status,
            nli_label=n_label,
            nli_confidence=n_conf,
            shadow_recommended_status=rec_status,
            has_disagreement=disagreement,
            disagreement_type=disagreement_type,
            audit_rationale=rationale
        )
