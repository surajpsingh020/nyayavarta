"""
Data models for NyayaVarta Evidence-Grounded RAG Subsystem (Milestone 5A).
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class EvidencePassage(BaseModel):
    """A grounded textual excerpt from a canonical judgment with verified character spans."""
    evidence_id: str = Field(..., description="Stable evidence identifier (e.g., 'E1', 'E2')")
    document_id: str = Field(..., description="Canonical corpus document ID")
    case_title: str = Field(default="Unknown Case", description="Full case title of the judgment")
    citation: Optional[str] = Field(None, description="Neutral or reporter citation if available")
    case_number: Optional[str] = Field(None, description="Court case or appeal number")
    decision_date: Optional[str] = Field(None, description="Date of decision")
    passage_text: str = Field(..., description="Exact textual excerpt from canonical judgment full_text")
    start_char: int = Field(..., ge=0, description="Start character index in canonical full_text")
    end_char: int = Field(..., ge=0, description="End character index in canonical full_text")
    judgment_rank: int = Field(default=1, ge=1, description="Rank of the source judgment in retrieval results")
    judgment_score: float = Field(default=1.0, description="Hybrid retrieval score of the source judgment")
    passage_score: float = Field(default=0.0, description="Relevance score of this specific passage")
    structural_label: Optional[str] = Field(default=None, description="Heuristic structural category")
    structural_confidence: float = Field(default=0.0, description="Confidence in structural classification (0.0 to 1.0)")
    detection_method: Optional[str] = Field(default=None, description="Method used to detect structure ('explicit_heading', 'preamble_marker', 'paragraph_heuristic', 'fallback_chunk')")



class ClaimAttribution(BaseModel):
    """Sentence-level attribution linking a generated legal assertion to evidence sources (Milestone 5A, 12 & 13)."""
    sentence: str = Field(..., description="Generated sentence or claim")
    cited_evidence_ids: List[str] = Field(default_factory=list, description="Evidence IDs cited in this sentence")
    citation_syntax_valid: bool = Field(default=True, description="Whether citation markers in this sentence are well-formed")
    citation_existence_valid: bool = Field(default=True, description="Whether all cited IDs exist in the supplied evidence")
    is_attributed: bool = Field(default=True, description="Whether this sentence contains at least one valid evidence reference or is an explicit abstention/meta-statement")
    semantic_support_status: str = Field(
        default="not_evaluated",
        description="Status of factual/legal support evaluation: 'not_evaluated', 'supported', 'partially_supported', 'unsupported', 'contradicted'"
    )
    verification_status: str = Field(
        default="not_evaluated",
        description="Explicit verification state: 'supported', 'partially_supported', 'unsupported', 'contradicted', 'not_evaluated'"
    )
    verification_method: str = Field(
        default="unverified",
        description="Method used for verification ('polarity_contradiction_check', 'structural_nature_check', 'direct_holding_entailment', 'unverified')"
    )
    verification_reason: str = Field(
        default="",
        description="Specific explanation of why the claim received its verification status"
    )
    unresolved_uncertainty: Optional[str] = Field(
        default=None,
        description="Any unresolved legal ambiguity, qualification, or caveat"
    )
    source_offsets: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Exact source metadata, document_id, and character offsets for cited passages"
    )
    is_grounded: bool = Field(default=True, description="Legacy compatibility: true if all cited IDs exist in supplied evidence")
    structural_natures: List[str] = Field(default_factory=list, description="Structural classification of cited evidence passages")
    relies_only_on_party_submissions: bool = Field(default=False, description="True if claim references only party submissions")
    shadow_nli_label: Optional[str] = Field(default=None, description="Diagnostic NLI prediction in shadow mode ('contradiction', 'entailment', 'neutral')")
    shadow_nli_confidence: Optional[float] = Field(default=None, description="Softmax confidence of NLI prediction")
    shadow_nli_disagreement: bool = Field(default=False, description="True if shadow NLI disagrees with deterministic status")
    shadow_nli_rationale: Optional[str] = Field(default=None, description="Audit rationale for shadow NLI recommendation")
    omits_statutory_qualification: bool = Field(default=False, description="True if claim omits mandatory statutory qualification or prerequisite")
    claim_overgeneralizes_holding: bool = Field(default=False, description="True if claim overgeneralizes a specific or equitable holding into a universal rule")


class CitationValidationResult(BaseModel):
    """Detailed audit of citations and substantive claim verification in generated text against supplied evidence."""
    is_valid: bool = Field(..., description="Overall status: True only if citations exist, are well-formed, reference supplied evidence, and no material claim is contradicted or unsupported")
    validation_status: str = Field(
        default="valid",
        description="Validation classification: 'valid', 'invalid', 'not_evaluated', 'partially_supported', 'contradicted', or 'unsupported'"
    )
    citation_syntax_valid: bool = Field(default=True, description="Whether all detected citation markers are correctly formatted bracket notation [E#]")
    citation_existence_valid: bool = Field(default=True, description="Whether all cited IDs refer to evidence supplied to the generator")
    attribution_complete: bool = Field(default=True, description="Whether all substantive assertions have source citations")
    evidence_integrity_valid: bool = Field(default=True, description="Whether all cited evidence passages passed exact offset checks")
    semantic_support_status: str = Field(
        default="not_evaluated",
        description="Explicit semantic support status: 'not_evaluated', 'partially_supported', 'supported', 'contradicted', or 'unsupported'"
    )
    contradicted_claims_count: int = Field(default=0, description="Count of claims verified as contradicted by cited evidence")
    unsupported_claims_count: int = Field(default=0, description="Count of claims verified as unsupported by cited evidence")
    partially_supported_claims_count: int = Field(default=0, description="Count of claims verified as partially supported")
    supported_claims_count: int = Field(default=0, description="Count of claims verified as directly supported")
    unverified_claims_count: int = Field(default=0, description="Count of claims whose verification status is not_evaluated")
    cited_source_ids: List[str] = Field(default_factory=list, description="All citation IDs found in generated text")
    valid_source_ids: List[str] = Field(default_factory=list, description="Citations that correctly match supplied evidence")
    invalid_source_ids: List[str] = Field(default_factory=list, description="Citations referencing unknown/hallucinated IDs")
    unsupported_sentences: List[str] = Field(default_factory=list, description="Sentences making factual/legal claims without citations")
    has_invalid_citations: bool = Field(default=False, description="True if any hallucinated citation IDs were detected")
    validation_notes: List[str] = Field(default_factory=list, description="Diagnostic notes from validator")
    verification_notes: List[str] = Field(default_factory=list, description="Detailed claim verification audit notes")
    shadow_nli_disagreements_count: int = Field(default=0, description="Count of claims where shadow NLI disagreed with deterministic status")



class StructuredClaim(BaseModel):
    """Substantive legal assertion with explicitly declared evidence references (Milestone 7)."""
    text: str = Field(..., description="Substantive legal proposition, judicial holding, or factual finding")
    evidence_ids: List[str] = Field(default_factory=list, description="Exact evidence IDs supporting this claim from active request (e.g., ['E1'])")


class StructuredAnswer(BaseModel):
    """Structured response container constraining legal generation to explicit claims and evidence (Milestone 7)."""
    status: str = Field(..., description="High-level answer status: 'answer' or 'abstain'")
    claims: List[StructuredClaim] = Field(default_factory=list, description="Substantive legal claims establishing the answer")
    abstention_reason: Optional[str] = Field(None, description="Explanation when status is 'abstain'")


def get_structured_answer_schema(allowed_evidence_ids: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Generate minimal JSON Schema for Ollama / LLM structured generation.
    If allowed_evidence_ids are provided, restricts evidence_ids items via enum constraints.
    """
    evidence_id_schema: Dict[str, Any] = {"type": "string"}
    if allowed_evidence_ids:
        # Enforce exact allowed evidence IDs
        evidence_id_schema["enum"] = [eid.upper() for eid in allowed_evidence_ids]

    return {
        "type": "object",
        "properties": {
            "status": {
                "type": "string",
                "enum": ["answer", "abstain"]
            },
            "claims": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string"},
                        "evidence_ids": {
                            "type": "array",
                            "items": evidence_id_schema
                        }
                    },
                    "required": ["text", "evidence_ids"]
                }
            },
            "abstention_reason": {"type": "string"}
        },
        "required": ["status", "claims"]
    }


class RAGResult(BaseModel):
    """End-to-end result of a grounded question-answering query."""
    query: str
    answer: str
    status: str = Field(..., description="High-level status: 'answered', 'answered_with_qualification', 'insufficient_evidence', 'empty_retrieval', 'error', 'validation_failed'")
    grounding_status: str = Field(
        default="sufficient_evidence",
        description="Explicit pipeline grounding state: 'sufficient_evidence', 'topically_relevant_but_insufficient_grounding', 'no_relevant_evidence', 'grounding_check_unavailable', 'generation_failed', 'validation_failed'"
    )
    evidence_passages: List[EvidencePassage] = Field(default_factory=list)
    citation_validation: CitationValidationResult
    claims: List[ClaimAttribution] = Field(default_factory=list)
    structured_answer: Optional[StructuredAnswer] = Field(
        default=None,
        description="Structured answer container when structured generation is enabled (Milestone 7)"
    )
    verification_badge: str = Field(
        default="unverified_answer",
        description="Explicit user-facing presentation status (Milestone 14): "
                    "'verified_supported' (all claims directly verified by judicial authority), "
                    "'qualified_answer' (one or more claims partially supported or qualified), "
                    "'unverified_answer' (syntactic citations valid but semantic entailment unverified - MUST NOT be labelled 'verified'), "
                    "'rejected_answer' (contradicted or unsupported claims; answer suppressed or flagged), "
                    "'insufficient_evidence' (clean system abstention due to inadequate grounding), "
                    "'system_error' (provider error or infrastructure failure)"
    )
    retrieval_metadata: Dict[str, Any] = Field(default_factory=dict)
    timing_ms: Dict[str, float] = Field(default_factory=dict)
    grounding_decision: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Detailed audit decision from Proposition Grounding Gate"
    )
    legal_disclaimer: str = Field(
        default="NyayaVarta evidence citations reflect observational text in the retrieved judgments. "
                "The system does not verify whether cited judgments remain good law or represent binding precedent."
    )

    @property
    def is_verified_supported(self) -> bool:
        """True only if verification_badge is 'verified_supported'."""
        return self.verification_badge == "verified_supported"

    @property
    def is_answer_suppressed(self) -> bool:
        """True if the answer contains contradicted/unsupported claims and should be suppressed or flagged."""
        return self.verification_badge in ["rejected_answer", "system_error"]



