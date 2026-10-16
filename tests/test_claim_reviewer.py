"""
Unit Tests for Claim-Level Evidence Review Infrastructure (Milestone 5C).
"""
import os
import json
import pytest

from services.rag.models import (
    RAGResult,
    EvidencePassage,
    CitationValidationResult,
    ClaimAttribution
)
from services.rag.claim_reviewer import (
    ClaimReviewRecord,
    extract_claim_review_records,
    export_claim_review_artifact,
    load_claim_review_artifact,
    summarize_claim_reviews
)


@pytest.fixture
def sample_rag_result():
    ep1 = EvidencePassage(
        evidence_id="E1",
        document_id="2024_10_1359_1370",
        case_title="Renjith K.G. v. Sheeba",
        citation="2024 INSC 773",
        passage_text="Order XXI Rule 99 of CPC allows any stranger complaining of dispossession to apply for restoration.",
        start_char=500,
        end_char=602,
        judgment_rank=1,
        judgment_score=0.95
    )
    claims = [
        ClaimAttribution(
            sentence="A third-party stranger dispossessed of immovable property can maintain an application under Order XXI Rule 99 [E1].",
            cited_evidence_ids=["E1"],
            citation_syntax_valid=True,
            citation_existence_valid=True,
            is_attributed=True,
            semantic_support_status="not_evaluated"
        ),
        ClaimAttribution(
            sentence="The executing court is required to determine all possessory rights under Rule 101 [E1].",
            cited_evidence_ids=["E1"],
            citation_syntax_valid=True,
            citation_existence_valid=True,
            is_attributed=True,
            semantic_support_status="not_evaluated"
        )
    ]
    val = CitationValidationResult(
        is_valid=True,
        citation_syntax_valid=True,
        citation_existence_valid=True,
        attribution_complete=True,
        evidence_integrity_valid=True,
        semantic_support_status="not_evaluated",
        cited_source_ids=["E1"],
        valid_source_ids=["E1"]
    )
    return RAGResult(
        query="Can a stranger dispossessed of property file an application under Order XXI Rule 99 CPC?",
        answer="A third-party stranger dispossessed of immovable property can maintain an application under Order XXI Rule 99 [E1]. The executing court is required to determine all possessory rights under Rule 101 [E1].",
        status="answered",
        evidence_passages=[ep1],
        citation_validation=val,
        claims=claims
    )


def test_extract_claim_review_records_answered(sample_rag_result):
    records = extract_claim_review_records(sample_rag_result, query_id="LAQ001")
    assert len(records) == 2
    rec1 = records[0]
    assert rec1.review_id == "CR_LAQ001_01"
    assert rec1.query_id == "LAQ001"
    assert rec1.claim_id == "C01"
    assert "Order XXI Rule 99" in rec1.claim_sentence
    assert rec1.cited_evidence_ids == ["E1"]
    assert len(rec1.supporting_passages) == 1
    assert rec1.supporting_passages[0]["document_id"] == "2024_10_1359_1370"
    # Verification of default label
    assert rec1.support_label == "not_reviewed"


def test_extract_claim_review_records_abstention():
    val = CitationValidationResult(
        is_valid=True,
        citation_syntax_valid=True,
        citation_existence_valid=True,
        attribution_complete=True,
        evidence_integrity_valid=True,
        semantic_support_status="not_evaluated"
    )
    rag_result = RAGResult(
        query="What are biotechnology patent claim drafting rules?",
        answer="INSUFFICIENT EVIDENCE: The retrieved judicial passages do not provide sufficient evidence to answer this question.",
        status="insufficient_evidence",
        evidence_passages=[],
        citation_validation=val,
        claims=[]
    )
    records = extract_claim_review_records(rag_result, query_id="LAQ011")
    assert len(records) == 1
    assert records[0].claim_id == "C00_ABSTAIN"
    assert records[0].should_have_abstained is True
    assert records[0].support_label == "supported"


def test_export_and_load_claim_review_artifact(sample_rag_result, tmp_path):
    temp_jsonl = str(tmp_path / "test_claims.jsonl")
    records = extract_claim_review_records(sample_rag_result, query_id="LAQ001")
    exported_count = export_claim_review_artifact(records, output_path=temp_jsonl)
    assert exported_count == 2
    assert os.path.exists(temp_jsonl)

    loaded = load_claim_review_artifact(input_path=temp_jsonl)
    assert len(loaded) == 2
    assert loaded[0].review_id == "CR_LAQ001_01"
    assert loaded[1].review_id == "CR_LAQ001_02"


def test_summarize_claim_reviews(sample_rag_result):
    records = extract_claim_review_records(sample_rag_result, query_id="LAQ001")
    # Initially all not_reviewed
    summary = summarize_claim_reviews(records)
    assert summary["total_claims"] == 2
    assert summary["pending_review_claims"] == 2
    assert summary["reviewed_claims"] == 0

    # Simulate manual annotation
    records[0].support_label = "supported"
    records[0].annotated_by = "manual_auditor"
    records[1].support_label = "partially_supported"
    records[1].omits_relevant_context = True

    summary2 = summarize_claim_reviews(records)
    assert summary2["reviewed_claims"] == 2
    assert summary2["label_breakdown"]["supported"] == 1
    assert summary2["label_breakdown"]["partially_supported"] == 1
    assert summary2["relevant_context_omitted"] == 1
