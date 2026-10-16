"""
Claim-Level Evidence Review Infrastructure for NyayaVarta RAG (Milestone 5C).

Provides data models and export utilities for human-in-the-loop review of legal answer claims.
Enforces explicit claim-support labeling without conflating syntactic citation with semantic entailment:
Labels: 'supported', 'partially_supported', 'unsupported', 'contradicted', 'not_reviewed' (default).
"""
import json
import os
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from services.rag.models import RAGResult, EvidencePassage, ClaimAttribution


class ClaimReviewRecord(BaseModel):
    """Structured human-review unit for an individual generated legal claim."""
    review_id: str = Field(..., description="Stable unique identifier: CR_<query_id>_<idx>")
    query_id: str = Field(..., description="Query identifier from evaluation dataset")
    question: str = Field(..., description="Full user question")
    answer_text: str = Field(..., description="Full generated answer")
    claim_id: str = Field(..., description="Claim index within answer (e.g., C01, C02)")
    claim_sentence: str = Field(..., description="Individual substantive assertion text")
    cited_evidence_ids: List[str] = Field(default_factory=list, description="IDs of cited evidence passages")
    supporting_passages: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Exact text and provenance of passages cited for this claim"
    )
    support_label: str = Field(
        default="not_reviewed",
        description="Audit label: 'supported', 'partially_supported', 'unsupported', 'contradicted', 'not_reviewed'"
    )
    introduces_facts_absent_from_evidence: Optional[bool] = Field(
        default=None,
        description="Whether the claim introduces extrinsic facts not present in evidence"
    )
    omits_relevant_context: Optional[bool] = Field(
        default=None,
        description="Whether relevant judicial qualifications, exceptions, or dates were omitted"
    )
    should_have_abstained: Optional[bool] = Field(
        default=None,
        description="Whether the answer should have abstained due to insufficient evidence"
    )
    source_structural_nature: Optional[str] = Field(
        default=None,
        description="Nature of cited source: judicial_holding, party_submission, quoted_precedent, statutory_provision, court_analysis, background_fact"
    )
    directly_supports_claim: Optional[bool] = Field(
        default=None,
        description="Whether the cited text directly entails the substantive claim"
    )
    all_material_components_supported: Optional[bool] = Field(
        default=None,
        description="Whether every material proposition in the claim is supported"
    )
    omits_statutory_qualification_or_exception: Optional[bool] = Field(
        default=None,
        description="Whether an exception, proviso, or judicial qualification is omitted"
    )
    claim_overgeneralizes_holding: Optional[bool] = Field(
        default=None,
        description="Whether the claim overgeneralizes beyond the facts or ratio of the judgment"
    )
    citation_existence_valid: bool = Field(
        default=True,
        description="Whether cited evidence IDs exist in supplied passages"
    )
    curation_status: str = Field(
        default="developer_curated",
        description="Review provenance: developer_curated or independent_legal_review"
    )
    verification_status: Optional[str] = Field(
        default=None,
        description="Automated/audit verification status: 'supported', 'partially_supported', 'unsupported', 'contradicted', 'not_evaluated'"
    )
    verification_method: Optional[str] = Field(
        default=None,
        description="Method used for verification ('polarity_contradiction_check', 'structural_nature_check', 'direct_holding_entailment', 'unverified')"
    )
    unresolved_uncertainty: Optional[str] = Field(
        default=None,
        description="Any unresolved ambiguity, caveat, or qualification"
    )
    reviewer_notes: str = Field(
        default="",
        description="Notes, reasoning, or legal explanation from human reviewer"
    )
    annotated_by: Optional[str] = Field(
        default=None,
        description="Identifier of reviewer (e.g., 'developer_audit', 'legal_reviewer')"
    )
    annotation_date: Optional[str] = Field(
        default=None,
        description="Date of annotation (ISO-8601)"
    )


def extract_claim_review_records(
    rag_result: RAGResult,
    query_id: str,
    default_label: str = "not_reviewed"
) -> List[ClaimReviewRecord]:
    """
    Extract claim review records from a RAGResult.
    Maps cited evidence IDs to exact supporting passages.
    """
    records: List[ClaimReviewRecord] = []
    evidence_by_id: Dict[str, EvidencePassage] = {
        ep.evidence_id.upper(): ep for ep in rag_result.evidence_passages
    }

    # If the answer is an explicit abstention, emit a single record tracking abstention validity
    if rag_result.status in ["insufficient_evidence", "empty_retrieval"] or rag_result.answer.strip().lower().startswith("insufficient evidence"):
        rec = ClaimReviewRecord(
            review_id=f"CR_{query_id}_ABSTAIN",
            query_id=query_id,
            question=rag_result.query,
            answer_text=rag_result.answer,
            claim_id="C00_ABSTAIN",
            claim_sentence=rag_result.answer.strip(),
            cited_evidence_ids=[],
            supporting_passages=[],
            support_label="supported" if rag_result.status == "insufficient_evidence" else default_label,
            introduces_facts_absent_from_evidence=False,
            omits_relevant_context=False,
            should_have_abstained=True,
            reviewer_notes="Explicit system abstention due to insufficient evidence."
        )
        return [rec]

    # For answered queries, process each substantive claim
    claim_idx = 1
    for claim in rag_result.claims:
        # Skip pure structural section headers or disclaimers if empty
        s_clean = claim.sentence.strip()
        if not s_clean or len(s_clean) < 10:
            continue

        c_passages = []
        for eid in claim.cited_evidence_ids:
            ep = evidence_by_id.get(eid.upper())
            if ep:
                c_passages.append({
                    "evidence_id": ep.evidence_id,
                    "document_id": ep.document_id,
                    "case_title": ep.case_title,
                    "citation": ep.citation,
                    "start_char": ep.start_char,
                    "end_char": ep.end_char,
                    "structural_label": ep.structural_label,
                    "passage_text": ep.passage_text
                })

        struct_labels = [p.get("structural_label") for p in c_passages if p.get("structural_label")]
        if any(l in ("headnote_holding", "judicial_holding") for l in struct_labels):
            struct_nature = "judicial_holding"
        elif any(l == "party_submissions" for l in struct_labels):
            struct_nature = "party_submission"
        elif any(l == "court_analysis" for l in struct_labels):
            struct_nature = "court_analysis"
        elif any(l == "statutory_provision" for l in struct_labels):
            struct_nature = "statutory_provision"
        elif any(l == "facts_procedural" for l in struct_labels):
            struct_nature = "background_fact"
        else:
            struct_nature = "judicial_holding" if c_passages else "unspecified"

        c_exists = bool(claim.cited_evidence_ids and all(eid.upper() in evidence_by_id for eid in claim.cited_evidence_ids))

        rec = ClaimReviewRecord(
            review_id=f"CR_{query_id}_{claim_idx:02d}",
            query_id=query_id,
            question=rag_result.query,
            answer_text=rag_result.answer,
            claim_id=f"C{claim_idx:02d}",
            claim_sentence=claim.sentence,
            cited_evidence_ids=claim.cited_evidence_ids,
            supporting_passages=c_passages,
            support_label=default_label,
            source_structural_nature=struct_nature,
            citation_existence_valid=c_exists,
            introduces_facts_absent_from_evidence=None,
            omits_relevant_context=None,
            should_have_abstained=None,
            reviewer_notes=""
        )
        records.append(rec)
        claim_idx += 1

    return records


def export_claim_review_artifact(
    records: List[ClaimReviewRecord],
    output_path: str = "evaluation/rag/claim_review_artifact.jsonl"
) -> int:
    """Export claim review records to a JSONL file."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec.model_dump(), ensure_ascii=False) + "\n")
    return len(records)


def load_claim_review_artifact(
    input_path: str = "evaluation/rag/claim_review_artifact.jsonl"
) -> List[ClaimReviewRecord]:
    """Load claim review records from a JSONL file."""
    if not os.path.exists(input_path):
        return []
    records: List[ClaimReviewRecord] = []
    with open(input_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(ClaimReviewRecord(**json.loads(line)))
    return records


def summarize_claim_reviews(records: List[ClaimReviewRecord]) -> Dict[str, Any]:
    """Calculate summary statistics over claim review records."""
    total = len(records)
    label_counts = {
        "supported": 0,
        "partially_supported": 0,
        "unsupported": 0,
        "contradicted": 0,
        "not_reviewed": 0
    }
    extrinsic_facts_count = 0
    context_omitted_count = 0
    wrong_answering_count = 0

    for r in records:
        lbl = r.support_label if r.support_label in label_counts else "not_reviewed"
        label_counts[lbl] += 1
        if r.introduces_facts_absent_from_evidence is True:
            extrinsic_facts_count += 1
        if r.omits_relevant_context is True:
            context_omitted_count += 1
        if r.should_have_abstained is True and r.claim_id != "C00_ABSTAIN":
            wrong_answering_count += 1

    reviewed_count = total - label_counts["not_reviewed"]

    return {
        "total_claims": total,
        "reviewed_claims": reviewed_count,
        "pending_review_claims": label_counts["not_reviewed"],
        "label_breakdown": label_counts,
        "extrinsic_facts_introduced": extrinsic_facts_count,
        "relevant_context_omitted": context_omitted_count,
        "unwarranted_answering_claims": wrong_answering_count
    }
