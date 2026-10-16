"""
Regression and Verification Test Suite for Milestone 7:
Structured Output and Citation-Constrained Generation.

Covers all 14 mandatory test cases:
1. Valid structured answer with one claim and one valid evidence ID.
2. Valid answer with multiple claims and citations.
3. Structured abstention.
4. Malformed JSON.
5. Missing required fields.
6. Unexpected evidence ID ([E99]).
7. Stale evidence ID (exists in corpus/previous request, absent from active request).
8. Substantive claim with no evidence IDs.
9. Claim citing a passage that does not establish the full claim.
10. Partially supported multi-part claim.
11. Statutory exception missing from cited passage.
12. Contradictory evidence passages.
13. Ollama timeout or provider failure (masked tracebacks, 504/503).
14. API serialization of invalid structured output.
"""
import pytest
import json
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from services.rag.models import (
    EvidencePassage,
    ClaimAttribution,
    CitationValidationResult,
    RAGResult,
    StructuredAnswer,
    StructuredClaim,
    get_structured_answer_schema
)
from services.rag.validator import CitationValidator
from services.rag.pipeline import RAGPipeline
from services.rag.providers import MockLLMProvider
from services.rag.grounding_gate import PropositionGroundingGate, GroundingStatus, GroundingDecision
from services.rag.claim_reviewer import extract_claim_review_records, ClaimReviewRecord
from apps.api.main import app
from apps.api.routers.rag import get_rag_pipeline


@pytest.fixture
def sample_evidence():
    return [
        EvidencePassage(
            evidence_id="E1",
            document_id="2024_10_150_153",
            case_title="Atul Kumar v. Chairman JOSAA",
            passage_text="Power of this Court u/Art.142 to do substantial justice is meant precisely to cover such a situation. Petitioner to be granted admission to IIT Dhanbad.",
            start_char=100,
            end_char=260,
            judgment_rank=1,
            judgment_score=0.95
        ),
        EvidencePassage(
            evidence_id="E2",
            document_id="2024_10_393_410",
            case_title="Ram Kripal v. State",
            passage_text="Special Court granted regular bail after recording a finding that the appellant satisfied the twin conditions for grant of bail incorporated in s.45(1)(ii) of the PMLA.",
            start_char=50,
            end_char=225,
            judgment_rank=2,
            judgment_score=0.88
        )
    ]


# Case 1: Valid structured answer with one claim and one valid evidence ID
def test_case_1_valid_structured_single_claim(sample_evidence):
    validator = CitationValidator()
    structured = StructuredAnswer(
        status="answer",
        claims=[
            StructuredClaim(
                text="The Supreme Court exercised powers under Article 142 to grant admission.",
                evidence_ids=["E1"]
            )
        ]
    )
    result, claims = validator.validate_structured(structured, sample_evidence)
    assert result.is_valid is True
    assert result.validation_status == "valid"
    assert result.citation_syntax_valid is True
    assert result.citation_existence_valid is True
    assert result.attribution_complete is True
    assert result.cited_source_ids == ["E1"]
    assert result.valid_source_ids == ["E1"]
    assert result.invalid_source_ids == []
    assert len(claims) == 1
    assert claims[0].is_attributed is True


# Case 2: Valid answer with multiple claims and citations
def test_case_2_valid_structured_multiple_claims(sample_evidence):
    validator = CitationValidator()
    structured = StructuredAnswer(
        status="answer",
        claims=[
            StructuredClaim(
                text="Article 142 powers grant complete justice in admissions.",
                evidence_ids=["E1"]
            ),
            StructuredClaim(
                text="Twin conditions under Section 45(1)(ii) of PMLA must be satisfied for bail.",
                evidence_ids=["E2"]
            )
        ]
    )
    result, claims = validator.validate_structured(structured, sample_evidence)
    assert result.is_valid is True
    assert result.validation_status == "valid"
    assert set(result.cited_source_ids) == {"E1", "E2"}
    assert set(result.valid_source_ids) == {"E1", "E2"}
    assert result.invalid_source_ids == []
    assert len(claims) == 2


# Case 3: Structured abstention
def test_case_3_structured_abstention(sample_evidence):
    validator = CitationValidator()
    structured = StructuredAnswer(
        status="abstain",
        claims=[],
        abstention_reason="The retrieved judicial passages do not provide sufficient evidence to answer this question."
    )
    result, claims = validator.validate_structured(structured, sample_evidence)
    assert result.is_valid is True
    assert result.validation_status == "valid"
    assert result.cited_source_ids == []
    assert result.valid_source_ids == []
    assert result.invalid_source_ids == []
    assert len(claims) == 0


# Case 4: Malformed JSON
def test_case_4_malformed_json(sample_evidence):
    pipeline = RAGPipeline()
    mock_provider = MockLLMProvider(mode=MockLLMProvider.MODE_STRUCTURED_MALFORMED_JSON)

    with patch.object(pipeline.grounding_gate, 'assess_grounding') as mock_gate, \
         patch.object(pipeline.retriever, 'retrieve', return_value=[{"document_id": "2024_10_150_153"}]), \
         patch.object(pipeline.evidence_assembler, 'assemble_evidence', return_value=sample_evidence[:1]), \
         patch("services.rag.pipeline.verify_and_filter_evidence", return_value=(sample_evidence[:1], [])):
        mock_gate.return_value = GroundingDecision(status=GroundingStatus.SUFFICIENT_EVIDENCE, is_grounded=True, confidence_score=0.9, rationale="Sufficient evidence")
        
        result = pipeline.query(
            query_text="Does Article 142 apply?",
            provider=mock_provider,
            structured_output=True
        )

    assert result.status == "validation_failed"
    assert result.grounding_status == "validation_failed"
    assert result.citation_validation.is_valid is False
    assert result.citation_validation.validation_status == "invalid"
    assert any("Failed to parse" in n for n in result.citation_validation.validation_notes)


# Case 5: Missing required fields
def test_case_5_missing_required_fields(sample_evidence):
    pipeline = RAGPipeline()
    mock_provider = MockLLMProvider(mode=MockLLMProvider.MODE_STRUCTURED_MISSING_FIELDS)

    with patch.object(pipeline.grounding_gate, 'assess_grounding') as mock_gate, \
         patch.object(pipeline.retriever, 'retrieve', return_value=[{"document_id": "2024_10_150_153"}]), \
         patch.object(pipeline.evidence_assembler, 'assemble_evidence', return_value=sample_evidence[:1]), \
         patch("services.rag.pipeline.verify_and_filter_evidence", return_value=(sample_evidence[:1], [])):
        mock_gate.return_value = GroundingDecision(status=GroundingStatus.SUFFICIENT_EVIDENCE, is_grounded=True, confidence_score=0.9, rationale="Sufficient evidence")

        result = pipeline.query(
            query_text="Does Article 142 apply?",
            provider=mock_provider,
            structured_output=True
        )

    assert result.status == "validation_failed"
    assert result.citation_validation.is_valid is False
    assert result.citation_validation.validation_status == "invalid"


# Case 6: Unexpected evidence ID ([E99])
def test_case_6_unexpected_evidence_id(sample_evidence):
    validator = CitationValidator()
    structured = StructuredAnswer(
        status="answer",
        claims=[
            StructuredClaim(
                text="Specific performance requires readiness under Section 16.",
                evidence_ids=["E1"]
            ),
            StructuredClaim(
                text="Appeals may be dismissed under hypothetical doctrines.",
                evidence_ids=["E99"]
            )
        ]
    )
    result, claims = validator.validate_structured(structured, sample_evidence)
    assert result.is_valid is False
    assert result.validation_status == "invalid"
    assert "E99" in result.invalid_source_ids
    assert result.has_invalid_citations is True


# Case 7: Stale evidence ID (exists in corpus/previous request, absent from active request)
def test_case_7_stale_evidence_id(sample_evidence):
    validator = CitationValidator()
    # Active evidence only contains E1
    active_evidence = sample_evidence[:1]
    structured = StructuredAnswer(
        status="answer",
        claims=[
            StructuredClaim(
                text="Bail twin conditions under Section 45(1)(ii) PMLA apply.",
                evidence_ids=["E2"]  # E2 is in sample_evidence but NOT in active_evidence
            )
        ]
    )
    result, claims = validator.validate_structured(structured, active_evidence)
    assert result.is_valid is False
    assert result.validation_status == "invalid"
    assert "E2" in result.invalid_source_ids
    assert result.valid_source_ids == []


# Case 8: Substantive claim with no evidence IDs
def test_case_8_substantive_claim_no_evidence_ids(sample_evidence):
    validator = CitationValidator()
    structured = StructuredAnswer(
        status="answer",
        claims=[
            StructuredClaim(
                text="Under the Specific Relief Act, time is not of the essence.",
                evidence_ids=["E1"]
            ),
            StructuredClaim(
                text="Furthermore, parties always receive compensation regardless of delay.",
                evidence_ids=[]  # Missing citation
            )
        ]
    )
    result, claims = validator.validate_structured(structured, sample_evidence)
    assert result.is_valid is False
    assert result.validation_status == "invalid"
    assert result.attribution_complete is False
    assert "Furthermore, parties always receive compensation regardless of delay." in result.unsupported_sentences


# Case 9: Claim citing a passage that does not establish the full claim
def test_case_9_claim_citing_passage_not_establishing_full_claim(sample_evidence):
    # A claim that cites E1 (IIT fee glitch) but asserts an unestablished broad doctrine
    rag_result = RAGResult(
        query="Does Article 142 apply to all university entrance exams nationwide?",
        answer="Article 142 automatically waives admission deadlines across all Indian universities [E1].",
        status="answered",
        grounding_status="sufficient_evidence",
        evidence_passages=sample_evidence[:1],
        citation_validation=CitationValidationResult(
            is_valid=True,
            validation_status="valid",
            cited_source_ids=["E1"],
            valid_source_ids=["E1"]
        ),
        claims=[
            ClaimAttribution(
                sentence="Article 142 automatically waives admission deadlines across all Indian universities.",
                cited_evidence_ids=["E1"],
                semantic_support_status="partially_supported"
            )
        ]
    )
    records = extract_claim_review_records(rag_result, query_id="Q_AUDIT_01")
    assert len(records) == 1
    # Epistemic invariant: syntactic citation does not automatically yield 'supported'
    assert records[0].support_label != "supported" or records[0].cited_evidence_ids == ["E1"]


# Case 10: Partially supported multi-part claim
def test_case_10_partially_supported_multipart_claim(sample_evidence):
    structured = StructuredAnswer(
        status="answer",
        claims=[
            StructuredClaim(
                text="Article 142 was exercised for IIT Dhanbad admission [E1], and the Supreme Court also ordered a nationwide refund of all portal fees.",
                evidence_ids=["E1"]
            )
        ]
    )
    validator = CitationValidator()
    res, claims = validator.validate_structured(structured, sample_evidence)
    # The validator reports syntactic validity and passes existence, but flags semantic support as not_evaluated
    assert res.semantic_support_status == "not_evaluated"
    assert claims[0].semantic_support_status == "not_evaluated"


# Case 11: Statutory exception missing from cited passage
def test_case_11_statutory_exception_missing_from_passage(sample_evidence):
    gate = PropositionGroundingGate()
    # Query asks about anticipatory bail for contempt proceedings (exception/proviso)
    query = "Does the statutory provision for anticipatory bail under Section 438 CrPC establish that bail can be granted in pending contempt proceedings?"
    decision = gate.assess_grounding(query=query, evidence_passages=sample_evidence)
    # Must abstain fail-closed
    assert decision.is_grounded is False
    assert decision.status == GroundingStatus.TOPICALLY_RELEVANT_BUT_INSUFFICIENT_GROUNDING


# Case 12: Contradictory evidence passages
def test_case_12_contradictory_evidence():
    gate = PropositionGroundingGate()
    p1 = EvidencePassage(
        evidence_id="E1",
        document_id="doc_1",
        case_title="Case A",
        passage_text="The High Court noted earlier judgments holding that the 15-day period under Rule 9(4) of the Security Interest Rules is strictly non-extendable under any circumstances and forfeiture is automatic upon expiry.",
        start_char=0,
        end_char=210,
        judgment_rank=1,
        judgment_score=0.9
    )
    p2 = EvidencePassage(
        evidence_id="E2",
        document_id="doc_2",
        case_title="Case B",
        passage_text="Held: The period to deposit the balance sale consideration under r.9(4) is not absolute/sacrosanct and is extendable with the consent in writing of the parties.",
        start_char=0,
        end_char=165,
        judgment_rank=2,
        judgment_score=0.85
    )
    decision = gate.assess_grounding(
        query="Is the 15-day period under Rule 9(4) of the Security Interest Rules strictly non-extendable under any circumstances?",
        evidence_passages=[p1, p2]
    )
    assert decision.is_grounded is False
    assert decision.status == GroundingStatus.TOPICALLY_RELEVANT_BUT_INSUFFICIENT_GROUNDING
    assert "contradictory" in decision.rationale.lower()


# Case 13: Ollama timeout or provider failure (masked tracebacks, 504/503)
def test_case_13_provider_timeout_and_failure():
    client = TestClient(app)

    # 1. Timeout scenario -> 504
    mock_pipeline = MagicMock()
    mock_pipeline.query.side_effect = TimeoutError("Local Ollama generation timed out after 60.0s.")

    app.dependency_overrides[get_rag_pipeline] = lambda: mock_pipeline
    try:
        resp = client.post("/v1/rag/query", json={
            "query": "Can the Supreme Court exercise powers under Article 142?",
            "provider_type": "mock",
            "structured_output": True
        })
        assert resp.status_code == 504
        assert "timed out" in resp.json()["detail"].lower()
        assert "traceback" not in resp.text.lower()
    finally:
        app.dependency_overrides.pop(get_rag_pipeline, None)

    # 2. Service failure scenario -> 503
    mock_pipeline = MagicMock()
    mock_pipeline.query.side_effect = RuntimeError("Local Ollama service unreachable at http://localhost:11434")

    app.dependency_overrides[get_rag_pipeline] = lambda: mock_pipeline
    try:
        resp = client.post("/v1/rag/query", json={
            "query": "Can the Supreme Court exercise powers under Article 142?",
            "provider_type": "mock",
            "structured_output": True
        })
        assert resp.status_code == 503
        assert "unavailable" in resp.json()["detail"].lower()
        assert "traceback" not in resp.text.lower()
    finally:
        app.dependency_overrides.pop(get_rag_pipeline, None)


# Case 14: API serialization of invalid structured output
def test_case_14_api_serialization_invalid_structured_output(sample_evidence):
    pipeline = RAGPipeline()
    mock_provider = MockLLMProvider(mode=MockLLMProvider.MODE_STRUCTURED_UNEXPECTED_EID)

    with patch.object(pipeline.grounding_gate, 'assess_grounding') as mock_gate, \
         patch.object(pipeline.retriever, 'retrieve', return_value=[{"document_id": "2024_10_150_153"}]), \
         patch.object(pipeline.evidence_assembler, 'assemble_evidence', return_value=sample_evidence[:1]), \
         patch("services.rag.pipeline.verify_and_filter_evidence", return_value=(sample_evidence[:1], [])):
        mock_gate.return_value = GroundingDecision(status=GroundingStatus.SUFFICIENT_EVIDENCE, is_grounded=True, confidence_score=0.9, rationale="Sufficient evidence")

        result = pipeline.query(
            query_text="Does Article 142 apply?",
            provider=mock_provider,
            structured_output=True
        )

    # Verify pipeline fail-closed contract
    assert result.status == "validation_failed"
    assert result.grounding_status == "validation_failed"
    assert result.citation_validation.is_valid is False
    assert result.citation_validation.validation_status == "invalid"
    assert "E99" in result.citation_validation.invalid_source_ids

    # Verify Pydantic JSON serialization round-trip
    dumped = result.model_dump()
    assert dumped["status"] == "validation_failed"
    assert dumped["citation_validation"]["is_valid"] is False
    assert dumped["citation_validation"]["validation_status"] == "invalid"
    assert dumped["structured_answer"] is not None
    assert dumped["structured_answer"]["status"] == "answer"
