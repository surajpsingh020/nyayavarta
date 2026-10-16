"""
End-to-End Evidence-Grounded RAG Pipeline for NyayaVarta (Milestone 5A).

Coordinates:
1. Hybrid retrieval over canonical 782 Supreme Court judgments (optional graph expansion, disabled by default).
2. Exact character-offset passage extraction and evidence assembly.
3. Strict grounding prompt construction with anti-hallucination instructions.
4. Local LLM answer generation via provider abstraction.
5. Citation validation, claim attribution, and abstention handling.
"""
import time
import json
from typing import Dict, Any, Optional, List
from services.graph.graph_retriever import GraphExpandedRetriever
from services.rag.models import (
    RAGResult,
    EvidencePassage,
    CitationValidationResult,
    ClaimAttribution,
    StructuredAnswer,
    get_structured_answer_schema
)
from services.rag.evidence import (
    EvidenceAssembler,
    verify_evidence_offsets,
    verify_and_filter_evidence,
    select_complementary_evidence_passages
)
from services.rag.prompt import (
    SYSTEM_PROMPT,
    build_rag_prompt,
    STRUCTURED_SYSTEM_PROMPT,
    build_structured_rag_prompt,
    format_evidence_block
)
from services.rag.providers import LLMProvider, MockLLMProvider, get_llm_provider
from services.rag.validator import CitationValidator
from services.rag.grounding_gate import PropositionGroundingGate, GroundingStatus, GroundingDecision

CANONICAL_ABSTENTION_MESSAGE = "INSUFFICIENT EVIDENCE: The retrieved judicial passages do not provide sufficient evidence to answer this question."


class RAGPipeline:
    def __init__(
        self,
        retriever: Optional[GraphExpandedRetriever] = None,
        evidence_assembler: Optional[EvidenceAssembler] = None,
        llm_provider: Optional[LLMProvider] = None,
        validator: Optional[CitationValidator] = None,
        grounding_gate: Optional[PropositionGroundingGate] = None
    ):
        self.retriever = retriever or GraphExpandedRetriever()
        self.evidence_assembler = evidence_assembler or EvidenceAssembler()
        self.llm_provider = llm_provider or MockLLMProvider()
        self.validator = validator or CitationValidator()
        self.grounding_gate = grounding_gate or PropositionGroundingGate()


    def query(
        self,
        query_text: str,
        top_k_judgments: int = 3,
        max_passages: int = 5,
        enable_graph: bool = False,
        provider: Optional[LLMProvider] = None,
        max_chars_per_passage: Optional[int] = None,
        max_total_chars: Optional[int] = None,
        enable_compression: bool = False,
        structured_output: bool = False,
        enable_issue_holding_pairing: bool = True
    ) -> RAGResult:
        """
        Execute end-to-end question answering grounded in corpus evidence.
        Supports free-form text generation and structured JSON schema constrained output (Milestone 7).
        """
        t_start = time.perf_counter()
        timing_ms = {}
        active_provider = provider or self.llm_provider

        # Step 1: Retrieval
        t0 = time.perf_counter()
        candidates = self.retriever.retrieve(
            query=query_text,
            top_k=top_k_judgments,
            enable_graph=enable_graph
        )
        timing_ms["retrieval_ms"] = round((time.perf_counter() - t0) * 1000.0, 2)

        if not candidates:
            elapsed_total = round((time.perf_counter() - t_start) * 1000.0, 2)
            timing_ms["total_ms"] = elapsed_total
            return RAGResult(
                query=query_text,
                answer="No relevant judgments found in the corpus for this query.",
                status="empty_retrieval",
                verification_badge="insufficient_evidence",
                grounding_status=GroundingStatus.NO_RELEVANT_EVIDENCE.value,
                evidence_passages=[],
                citation_validation=CitationValidationResult(
                    is_valid=True,
                    cited_source_ids=[],
                    valid_source_ids=[],
                    invalid_source_ids=[],
                    unsupported_sentences=[],
                    has_invalid_citations=False,
                    validation_notes=["Retriever returned 0 candidates."]
                ),
                claims=[],
                retrieval_metadata={"candidates_count": 0, "enable_graph": enable_graph},
                timing_ms=timing_ms,
                grounding_decision={
                    "status": GroundingStatus.NO_RELEVANT_EVIDENCE.value,
                    "is_grounded": False,
                    "rationale": "Retriever returned 0 candidates."
                }
            )

        # Step 2: Evidence Assembly
        t0 = time.perf_counter()
        evidence_passages = self.evidence_assembler.assemble_evidence(
            query=query_text,
            retrieved_candidates=candidates
        )
        timing_ms["evidence_assembly_ms"] = round((time.perf_counter() - t0) * 1000.0, 2)

        if not evidence_passages:
            elapsed_total = round((time.perf_counter() - t_start) * 1000.0, 2)
            timing_ms["total_ms"] = elapsed_total
            return RAGResult(
                query=query_text,
                answer="INSUFFICIENT EVIDENCE: The retrieved judicial passages do not provide sufficient evidence to answer this question.",
                status="insufficient_evidence",
                verification_badge="insufficient_evidence",
                grounding_status=GroundingStatus.NO_RELEVANT_EVIDENCE.value,
                evidence_passages=[],
                citation_validation=CitationValidationResult(
                    is_valid=True,
                    cited_source_ids=[],
                    valid_source_ids=[],
                    invalid_source_ids=[],
                    unsupported_sentences=[],
                    has_invalid_citations=False,
                    validation_notes=["No qualifying evidence passages found in retrieved judgments."]
                ),
                claims=[],
                retrieval_metadata={
                    "candidates_count": len(candidates),
                    "enable_graph": enable_graph
                },
                timing_ms=timing_ms,
                grounding_decision={
                    "status": GroundingStatus.NO_RELEVANT_EVIDENCE.value,
                    "is_grounded": False,
                    "rationale": "No qualifying evidence passages extracted from candidates."
                }
            )

        # Step 2b: Fail-closed evidence offset and integrity verification
        valid_passages, offset_diagnostics = verify_and_filter_evidence(evidence_passages)

        if not valid_passages:
            elapsed_total = round((time.perf_counter() - t_start) * 1000.0, 2)
            timing_ms["total_ms"] = elapsed_total
            return RAGResult(
                query=query_text,
                answer="INSUFFICIENT EVIDENCE: The retrieved judicial passages do not provide sufficient evidence to answer this question.",
                status="insufficient_evidence",
                verification_badge="insufficient_evidence",
                grounding_status=GroundingStatus.NO_RELEVANT_EVIDENCE.value,
                evidence_passages=[],
                citation_validation=CitationValidationResult(
                    is_valid=True,
                    citation_syntax_valid=True,
                    citation_existence_valid=True,
                    attribution_complete=True,
                    evidence_integrity_valid=False if offset_diagnostics else True,
                    semantic_support_status="not_evaluated",
                    cited_source_ids=[],
                    valid_source_ids=[],
                    invalid_source_ids=[],
                    unsupported_sentences=[],
                    has_invalid_citations=False,
                    validation_notes=[
                        f"All {len(evidence_passages)} evidence passage(s) failed offset verification and were excluded."
                        if offset_diagnostics else
                        "No qualifying evidence passages found in retrieved judgments."
                    ]
                ),
                claims=[],
                retrieval_metadata={
                    "candidates_count": len(candidates),
                    "enable_graph": enable_graph,
                    "offsets_verified": False if offset_diagnostics else True,
                    "offset_diagnostics": offset_diagnostics
                },
                timing_ms=timing_ms,
                grounding_decision={
                    "status": GroundingStatus.NO_RELEVANT_EVIDENCE.value,
                    "is_grounded": False,
                    "rationale": "All evidence passages failed canonical offset slicing verification."
                }
            )

        # Step 2c: Proposition Grounding Gate over candidate retrieved evidence
        t0 = time.perf_counter()
        grounding_decision = self.grounding_gate.assess_grounding(
            query=query_text,
            evidence_passages=valid_passages
        )
        timing_ms["grounding_gate_ms"] = round((time.perf_counter() - t0) * 1000.0, 2)

        if not grounding_decision.is_grounded:
            elapsed_total = round((time.perf_counter() - t_start) * 1000.0, 2)
            timing_ms["total_ms"] = elapsed_total
            return RAGResult(
                query=query_text,
                answer=f"INSUFFICIENT EVIDENCE: {grounding_decision.rationale}",
                status="insufficient_evidence",
                verification_badge="insufficient_evidence",
                grounding_status=grounding_decision.status.value,
                evidence_passages=valid_passages[:max_passages],
                citation_validation=CitationValidationResult(
                    is_valid=True,
                    citation_syntax_valid=True,
                    citation_existence_valid=True,
                    attribution_complete=True,
                    evidence_integrity_valid=True,
                    semantic_support_status="insufficient_grounding",
                    cited_source_ids=[],
                    valid_source_ids=[],
                    invalid_source_ids=[],
                    unsupported_sentences=[],
                    has_invalid_citations=False,
                    validation_notes=[f"Proposition Grounding Gate: {grounding_decision.rationale}"]
                ),
                claims=[],
                retrieval_metadata={
                    "candidates_count": len(candidates),
                    "top_candidates": [c["document_id"] for c in candidates],
                    "enable_graph": enable_graph,
                    "evidence_count": len(valid_passages),
                    "active_evidence_count": 0,
                    "max_passages": max_passages,
                    "max_chars_per_passage": max_chars_per_passage,
                    "max_total_chars": max_total_chars,
                    "enable_compression": enable_compression,
                    "context_budget": {
                        "max_passages": max_passages,
                        "max_chars_per_passage": max_chars_per_passage,
                        "max_total_chars": max_total_chars,
                        "enable_compression": enable_compression,
                        "candidate_passages_count": len(valid_passages),
                        "candidate_text_chars": sum(len(p.passage_text) for p in valid_passages),
                        "active_passages_count": 0,
                        "active_passages_raw_chars": 0,
                        "formatted_evidence_chars": 0,
                        "prompt_chars": 0,
                        "total_prompt_chars": 0,
                        "prompt_tokens": 0,
                        "eval_tokens": 0
                    },
                    "excluded_passages_count": len(offset_diagnostics),
                    "offset_diagnostics": offset_diagnostics,
                    "offsets_verified": len(offset_diagnostics) == 0,
                    "grounding_status": grounding_decision.status.value,
                    "grounding_rationale": grounding_decision.rationale
                },
                timing_ms=timing_ms,
                grounding_decision=grounding_decision.model_dump()
            )

        # Step 2d: Bounded, Complementary Evidence Selection (Milestone 8 Task 2)
        active_passages = select_complementary_evidence_passages(
            passages=valid_passages,
            query=query_text,
            max_passages=max_passages,
            max_total_chars=max_total_chars,
            enable_compression=enable_compression,
            enable_issue_holding_pairing=enable_issue_holding_pairing,
            max_chars_per_passage=max_chars_per_passage
        )
        assert len(active_passages) <= max_passages, f"Active passages count {len(active_passages)} exceeds max_passages {max_passages}"

        # Step 2e: Active Evidence Sufficiency Check (Milestone 8 Task 3)
        active_gate_decision = self.grounding_gate.check_active_evidence_sufficiency(
            query=query_text,
            active_passages=active_passages
        )
        if not active_gate_decision.is_grounded:
            elapsed_total = round((time.perf_counter() - t_start) * 1000.0, 2)
            timing_ms["total_ms"] = elapsed_total
            return RAGResult(
                query=query_text,
                answer=f"INSUFFICIENT EVIDENCE: {active_gate_decision.rationale}",
                status="insufficient_evidence",
                verification_badge="insufficient_evidence",
                grounding_status=active_gate_decision.status.value,
                evidence_passages=active_passages,
                citation_validation=CitationValidationResult(
                    is_valid=True,
                    citation_syntax_valid=True,
                    citation_existence_valid=True,
                    attribution_complete=True,
                    evidence_integrity_valid=True,
                    semantic_support_status="insufficient_grounding",
                    cited_source_ids=[],
                    valid_source_ids=[],
                    invalid_source_ids=[],
                    unsupported_sentences=[],
                    has_invalid_citations=False,
                    validation_notes=[f"Active Evidence Sufficiency Gate: {active_gate_decision.rationale}"]
                ),
                claims=[],
                retrieval_metadata={
                    "candidates_count": len(candidates),
                    "top_candidates": [c["document_id"] for c in candidates],
                    "enable_graph": enable_graph,
                    "evidence_count": len(valid_passages),
                    "active_evidence_count": len(active_passages),
                    "max_passages": max_passages,
                    "max_chars_per_passage": max_chars_per_passage,
                    "max_total_chars": max_total_chars,
                    "enable_compression": enable_compression,
                    "context_budget": {
                        "max_passages": max_passages,
                        "max_chars_per_passage": max_chars_per_passage,
                        "max_total_chars": max_total_chars,
                        "enable_compression": enable_compression,
                        "candidate_passages_count": len(valid_passages),
                        "candidate_text_chars": sum(len(p.passage_text) for p in valid_passages),
                        "active_passages_count": len(active_passages),
                        "active_passages_raw_chars": sum(len(p.passage_text) for p in active_passages),
                        "formatted_evidence_chars": 0,
                        "prompt_chars": 0,
                        "total_prompt_chars": 0,
                        "prompt_tokens": 0,
                        "eval_tokens": 0
                    },
                    "excluded_passages_count": len(offset_diagnostics),
                    "offset_diagnostics": offset_diagnostics,
                    "offsets_verified": len(offset_diagnostics) == 0,
                    "grounding_status": active_gate_decision.status.value,
                    "grounding_rationale": active_gate_decision.rationale
                },
                timing_ms=timing_ms,
                grounding_decision=active_gate_decision.model_dump()
            )

        # Step 3: Prompt Construction using verified active passages
        allowed_eids = [ep.evidence_id.upper() for ep in active_passages]
        t0 = time.perf_counter()

        if structured_output:
            prompt = build_structured_rag_prompt(
                query=query_text,
                evidence_passages=active_passages,
                max_chars_per_passage=max_chars_per_passage
            )
            structured_schema = get_structured_answer_schema(allowed_evidence_ids=allowed_eids)
            system_prompt = STRUCTURED_SYSTEM_PROMPT
        else:
            prompt = build_rag_prompt(
                query=query_text,
                evidence_passages=active_passages,
                max_chars_per_passage=max_chars_per_passage
            )
            structured_schema = None
            system_prompt = SYSTEM_PROMPT

        timing_ms["prompt_construction_ms"] = round((time.perf_counter() - t0) * 1000.0, 2)

        # Step 4: Local Generation
        t0 = time.perf_counter()
        llm_response = active_provider.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            structured_schema=structured_schema
        )
        timing_ms["generation_ms"] = round((time.perf_counter() - t0) * 1000.0, 2)

        # Step 5: Citation & Claim Validation against active supplied evidence
        t0 = time.perf_counter()
        structured_obj: Optional[StructuredAnswer] = None

        if structured_output:
            raw_content = llm_response.content.strip()
            try:
                data = json.loads(raw_content)
                if not isinstance(data, dict):
                    raise ValueError("Structured LLM output must be a JSON object.")
                structured_obj = StructuredAnswer.model_validate(data)
                val_result, claims = self.validator.validate_structured(
                    structured_answer=structured_obj,
                    supplied_evidence=active_passages
                )
                if structured_obj.status == "abstain":
                    answer_text = CANONICAL_ABSTENTION_MESSAGE
                    status = "insufficient_evidence"
                    grounding_status = GroundingStatus.TOPICALLY_RELEVANT_BUT_INSUFFICIENT_GROUNDING.value
                else:
                    answer_text = " ".join([f"{c.text} [{', '.join(c.evidence_ids)}]." for c in structured_obj.claims])
                    if not val_result.is_valid:
                        status = "validation_failed"
                        grounding_status = GroundingStatus.VALIDATION_FAILED.value
                    elif val_result.validation_status == "partially_supported":
                        status = "answered_with_qualification"
                        grounding_status = GroundingStatus.SUFFICIENT_EVIDENCE.value
                    else:
                        status = "answered"
                        grounding_status = GroundingStatus.SUFFICIENT_EVIDENCE.value
            except Exception as e:
                structured_obj = None
                answer_text = raw_content
                val_result = CitationValidationResult(
                    is_valid=False,
                    validation_status="invalid",
                    citation_syntax_valid=False,
                    citation_existence_valid=False,
                    attribution_complete=False,
                    evidence_integrity_valid=True,
                    semantic_support_status="not_evaluated",
                    cited_source_ids=[],
                    valid_source_ids=[],
                    invalid_source_ids=[],
                    unsupported_sentences=[],
                    has_invalid_citations=True,
                    validation_notes=[f"Failed to parse LLM response into StructuredAnswer schema: {e}"]
                )
                claims = []
                status = "validation_failed"
                grounding_status = GroundingStatus.VALIDATION_FAILED.value
        else:
            val_result, claims = self.validator.validate(
                answer=llm_response.content,
                supplied_evidence=active_passages
            )
            raw_model_content = llm_response.content
            ans_trimmed = raw_model_content.strip()

            # Determine whether the generation is a genuinely clean abstention
            is_clean_abs = (
                self.validator.is_clean_abstention(ans_trimmed) and
                val_result.is_valid and
                len(val_result.cited_source_ids) == 0
            )

            if not ans_trimmed:
                status = "error"
                grounding_status = GroundingStatus.GENERATION_FAILED.value
                answer_text = raw_model_content
            elif is_clean_abs:
                status = "insufficient_evidence"
                grounding_status = GroundingStatus.TOPICALLY_RELEVANT_BUT_INSUFFICIENT_GROUNDING.value
                answer_text = CANONICAL_ABSTENTION_MESSAGE
            elif not val_result.is_valid:
                status = "validation_failed"
                grounding_status = GroundingStatus.VALIDATION_FAILED.value
                answer_text = raw_model_content
            elif val_result.validation_status == "partially_supported":
                status = "answered_with_qualification"
                grounding_status = GroundingStatus.SUFFICIENT_EVIDENCE.value
                answer_text = raw_model_content
            else:
                status = "answered"
                grounding_status = GroundingStatus.SUFFICIENT_EVIDENCE.value
                answer_text = raw_model_content

        timing_ms["validation_ms"] = round((time.perf_counter() - t0) * 1000.0, 2)
        timing_ms["total_ms"] = round((time.perf_counter() - t_start) * 1000.0, 2)

        formatted_evidence_str = format_evidence_block(active_passages, max_chars_per_passage=max_chars_per_passage)
        p_usage = llm_response.usage or {}

        retrieval_meta = {
            "candidates_count": len(candidates),
            "top_candidates": [c["document_id"] for c in candidates],
            "enable_graph": enable_graph,
            "evidence_count": len(valid_passages),
            "active_evidence_count": len(active_passages),
            "max_passages": max_passages,
            "max_chars_per_passage": max_chars_per_passage,
            "max_total_chars": max_total_chars,
            "enable_compression": enable_compression,
            "raw_model_generation": llm_response.content if 'llm_response' in locals() and llm_response else None,
            "context_budget": {
                "max_passages": max_passages,
                "max_chars_per_passage": max_chars_per_passage,
                "max_total_chars": max_total_chars,
                "enable_compression": enable_compression,
                "candidate_passages_count": len(valid_passages),
                "candidate_text_chars": sum(len(p.passage_text) for p in valid_passages),
                "active_passages_count": len(active_passages),
                "active_passages_raw_chars": sum(len(p.passage_text) for p in active_passages),
                "formatted_evidence_chars": len(formatted_evidence_str),
                "prompt_chars": len(prompt),
                "total_prompt_chars": len(prompt) + len(system_prompt),
                "prompt_tokens": p_usage.get("prompt_tokens", 0),
                "eval_tokens": p_usage.get("eval_tokens", 0)
            },
            "excluded_passages_count": len(offset_diagnostics),
            "offset_diagnostics": offset_diagnostics,
            "model_name": llm_response.model_name,
            "offsets_verified": len(offset_diagnostics) == 0,
            "llm_usage": llm_response.usage,
            "grounding_status": grounding_status,
            "structured_output_enabled": structured_output
        }

        verification_badge = self.determine_verification_badge(
            status=status,
            val_result=val_result,
            claims=claims,
            offsets_verified=retrieval_meta.get("offsets_verified", True),
            evidence_passages=active_passages,
            answer_text=answer_text
        )

        # Enforce canonical abstention string when badge or status is insufficient_evidence
        if verification_badge == "insufficient_evidence" or status == "insufficient_evidence":
            answer_text = CANONICAL_ABSTENTION_MESSAGE

        return RAGResult(
            query=query_text,
            answer=answer_text,
            status=status,
            verification_badge=verification_badge,
            grounding_status=grounding_status,
            evidence_passages=active_passages,
            citation_validation=val_result,
            claims=claims,
            structured_answer=structured_obj,
            retrieval_metadata=retrieval_meta,
            timing_ms=timing_ms,
            grounding_decision=grounding_decision.model_dump()
        )

    @staticmethod
    def determine_verification_badge(
        status: str,
        val_result: Any,
        claims: Optional[List[Any]] = None,
        offsets_verified: bool = True,
        evidence_passages: Optional[List[Any]] = None,
        answer_text: Optional[str] = None
    ) -> str:
        """
        Determine safe presentation badge strictly enforcing Milestone 14/15/22/24 safety invariants:
        1. At least one substantive claim has been extracted.
        2. Every substantive claim has been evaluated with a valid status.
        3. 100% of claims must be affirmatively verified as supported.
        4. No claim is partially supported, unsupported, contradicted, or not_evaluated.
        5. Citation attribution is complete (no ungrounded substantive sentences).
        6. Citation references resolve to selected evidence and correct source documents.
        7. Required source-offset and evidence-integrity checks pass.
        8. The existing citation and claim validators report no blocking failures.
        9. No required substantive claim has been silently omitted from validation.
        10. Final badge is derived strictly from validation results, not model strings.
        11. Single-claim answers: any caveat, nuance, or verifier disagreement blocks verified_supported.
        """
        claims = claims or []

        # 1. Explicit abstention
        if status in ["insufficient_evidence", "empty_retrieval"]:
            return "insufficient_evidence"

        # 2. System error or generation failure
        elif status in ["error", "system_error"]:
            return "system_error"

        # 3. Blocking validation failures or contradicted claims
        if status == "validation_failed" or (val_result and not getattr(val_result, "is_valid", True)):
            return "rejected_answer"

        if val_result and (
            getattr(val_result, "validation_status", "") == "contradicted" or
            getattr(val_result, "contradicted_claims_count", 0) > 0 or
            getattr(val_result, "semantic_support_status", "") == "contradicted"
        ):
            return "rejected_answer"

        # 4. Evidence integrity and source-offset failures
        if not offsets_verified or (val_result and not getattr(val_result, "evidence_integrity_valid", True)):
            return "rejected_answer"

        # 5. Invalid, hallucinated, or malformed citations
        if val_result and (
            getattr(val_result, "has_invalid_citations", False) or
            len(getattr(val_result, "invalid_source_ids", [])) > 0 or
            not getattr(val_result, "citation_existence_valid", True) or
            not getattr(val_result, "citation_syntax_valid", True)
        ):
            return "rejected_answer"

        # 6. Any contradicted claim in claims list
        if any(getattr(c, "verification_status", "") == "contradicted" or getattr(c, "is_contradicted", False) for c in claims):
            return "rejected_answer"

        # 7. Partial support or qualifications
        if (
            status == "answered_with_qualification" or
            (val_result and getattr(val_result, "validation_status", "") == "partially_supported") or
            (val_result and getattr(val_result, "partially_supported_claims_count", 0) > 0) or
            any(getattr(c, "verification_status", "") == "partially_supported" or getattr(c, "is_partially_supported", False) for c in claims)
        ):
            return "qualified_answer"

        # 8. All unsupported claims
        if claims and all(getattr(c, "verification_status", "") == "unsupported" for c in claims):
            return "rejected_answer"

        # 9. Fully verified evaluation
        if status == "answered":
            # Must satisfy all invariants
            if not val_result:
                return "unverified_answer"

            # Invariant 1: At least one substantive claim
            if len(claims) == 0:
                return "unverified_answer"

            # Invariant 2: Every claim evaluated
            for c in claims:
                st = getattr(c, "verification_status", None)
                if not st or st not in ["supported", "partially_supported", "unsupported", "contradicted", "not_evaluated"]:
                    return "unverified_answer"

            # Invariant 3 & 4: 100% supported, 0 partial, 0 unsupp, 0 contra, 0 unverified
            if (
                getattr(val_result, "semantic_support_status", "") != "supported" or
                getattr(val_result, "supported_claims_count", 0) != len(claims) or
                getattr(val_result, "contradicted_claims_count", 0) != 0 or
                getattr(val_result, "unsupported_claims_count", 0) != 0 or
                getattr(val_result, "partially_supported_claims_count", 0) != 0 or
                getattr(val_result, "unverified_claims_count", 0) != 0
            ):
                return "unverified_answer"

            # Invariant 5: Attribution complete
            if not getattr(val_result, "attribution_complete", False) or len(getattr(val_result, "unsupported_sentences", [])) > 0:
                return "unverified_answer"

            # Invariant 6: References resolve to selected evidence
            if evidence_passages:
                valid_pass_ids = {ep.evidence_id.upper() for ep in evidence_passages if hasattr(ep, "evidence_id")}
                for cid in getattr(val_result, "cited_source_ids", []):
                    if cid.upper() not in valid_pass_ids:
                        return "rejected_answer"

            # Invariant 7: Offsets verified
            if not offsets_verified or not getattr(val_result, "evidence_integrity_valid", True):
                return "rejected_answer"

            # Invariant 8: Blocking validator failures
            if not getattr(val_result, "is_valid", False):
                return "rejected_answer"

            # Invariant 9: No silent omission of substantive qualifications
            for c in claims:
                if (
                    getattr(c, "omits_statutory_qualification", False) or
                    getattr(c, "claim_overgeneralizes_holding", False) or
                    getattr(c, "relies_only_on_party_submissions", False) or
                    getattr(c, "unresolved_uncertainty", None) is not None
                ):
                    return "qualified_answer"

            # Invariant 11: Single-Claim Safety Hardening
            if len(claims) == 1:
                sc = claims[0]
                if getattr(sc, "shadow_nli_disagreement", False):
                    return "qualified_answer"
                if getattr(sc, "shadow_nli_label", "") == "contradiction":
                    return "rejected_answer"
                conf = getattr(sc, "shadow_nli_confidence", None)
                if conf is not None and conf >= 0.40 and getattr(sc, "shadow_nli_label", "") == "contradiction":
                    return "rejected_answer"

            return "verified_supported"

        return "unverified_answer"

    _determine_badge = determine_verification_badge
    verify_answer_safety = determine_verification_badge

