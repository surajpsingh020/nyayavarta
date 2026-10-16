"""
Regression and Hardening Test Suite for Milestone 6.1:
Answer Quality and Citation Integrity Hardening.

Covers 14 mandatory test cases:
1. Malformed citation marker [E#].
2. Unknown evidence ID.
3. Citation ID belonging to a previous request rather than current evidence set.
4. Substantive claim without required citation.
5. Answer with one supported claim and one unsupported claim.
6. Multi-part claim with only one supported component.
7. Statutory exception or qualification missing from cited evidence.
8. Party submission misrepresented as judicial holding.
9. Contradictory evidence passages.
10. Valid answer with multiple properly attributed citations.
11. Safe abstention for unsupported questions.
12. Ollama timeout or provider failure.
13. API serialization of invalid and partially supported answers.
14. Warning or diagnostic that must not be exposed as successful validation result.
"""
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from services.rag.models import EvidencePassage, ClaimAttribution, CitationValidationResult, RAGResult
from services.rag.validator import CitationValidator
from services.rag.pipeline import RAGPipeline
from services.rag.providers import MockLLMProvider
from services.rag.grounding_gate import PropositionGroundingGate, GroundingStatus
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


# Case 1: Malformed citation marker [E#]
def test_case_1_malformed_citation_marker_e_hash(sample_evidence):
    validator = CitationValidator()
    answer = "The Supreme Court granted equitable admission to the IIT candidate [E#]."
    val_result, claims = validator.validate(answer, sample_evidence)
    
    assert val_result.is_valid is False
    assert val_result.validation_status == "invalid"
    assert val_result.citation_syntax_valid is False
    assert any("malformed" in note.lower() for note in val_result.validation_notes)


# Case 2: Unknown evidence ID
def test_case_2_unknown_evidence_id(sample_evidence):
    validator = CitationValidator()
    answer = "Under Section 45 of PMLA, twin conditions must be satisfied [E99]."
    val_result, claims = validator.validate(answer, sample_evidence)
    
    assert val_result.is_valid is False
    assert val_result.validation_status == "invalid"
    assert val_result.citation_existence_valid is False
    assert "E99" in val_result.invalid_source_ids
    assert any("unknown/hallucinated" in note.lower() for note in val_result.validation_notes)


# Case 3: Citation ID belonging to a previous request rather than current evidence set
def test_case_3_citation_id_from_previous_request(sample_evidence):
    # Request A had E1 and E2. Request B only provides E1.
    evidence_request_b = [sample_evidence[0]]  # Only E1
    validator = CitationValidator()
    
    answer_b = "The twin conditions under Section 45 PMLA were examined by the court [E2]."
    val_result, claims = validator.validate(answer_b, evidence_request_b)
    
    assert val_result.is_valid is False
    assert val_result.validation_status == "invalid"
    assert "E2" in val_result.invalid_source_ids
    assert val_result.valid_source_ids == []


# Case 4: Substantive claim without required citation
def test_case_4_substantive_claim_without_citation(sample_evidence):
    validator = CitationValidator()
    answer = "The Supreme Court held that bail cannot be denied arbitrarily without recording exceptional reasons."
    val_result, claims = validator.validate(answer, sample_evidence)
    
    assert val_result.is_valid is False
    assert val_result.validation_status == "invalid"
    assert val_result.attribution_complete is False
    assert len(val_result.unsupported_sentences) == 1
    assert "The Supreme Court held that bail cannot be denied arbitrarily" in val_result.unsupported_sentences[0]


# Case 5: Answer with one supported claim and one unsupported claim
def test_case_5_partially_attributed_answer(sample_evidence):
    validator = CitationValidator()
    answer = (
        "Article 142 enables the court to grant equitable relief in rare educational hardships [E1]. "
        "Furthermore, all administrative universities must automatically waive all fees for reserved category students."
    )
    val_result, claims = validator.validate(answer, sample_evidence)
    
    assert val_result.is_valid is False
    assert val_result.validation_status == "invalid"
    assert val_result.attribution_complete is False
    assert len(val_result.unsupported_sentences) == 1
    assert "administrative universities" in val_result.unsupported_sentences[0]
    assert claims[0].is_attributed is True
    assert claims[1].is_attributed is False


# Case 6: Multi-part claim with only one supported component
def test_case_6_multipart_claim_partial_support():
    gate = PropositionGroundingGate()
    # Passage only supports Order XXI Rule 99 stranger redelivery; does not support anticipatory bail
    passage = EvidencePassage(
        evidence_id="E1",
        document_id="2024_10_108_130",
        case_title="Renjith K.G.",
        passage_text="Held: A third-party stranger dispossessed in execution of decree may maintain an application under Order XXI Rule 99 CPC.",
        start_char=0,
        end_char=130,
        judgment_rank=1,
        judgment_score=0.9
    )
    query = "Does Order XXI Rule 99 apply to strangers and simultaneously grant anticipatory bail under Section 438 CrPC?"
    decision = gate.assess_grounding(query, [passage])
    
    assert decision.is_grounded is False
    assert decision.status == GroundingStatus.TOPICALLY_RELEVANT_BUT_INSUFFICIENT_GROUNDING
    assert "compound" in decision.rationale.lower() or "conjunctive" in decision.rationale.lower() or "missing" in decision.rationale.lower() or "insufficient" in decision.rationale.lower()


# Case 7: Statutory exception or qualification missing from cited evidence
def test_case_7_statutory_exception_unmet():
    gate = PropositionGroundingGate()
    # General rule SARFAESI Rule 9(4) subject to written mutual consent
    passage = EvidencePassage(
        evidence_id="E1",
        document_id="2024_10_500_525",
        case_title="IDBI Bank",
        passage_text="Rule 9(4) mandates payment within 15 days, provided that the period may be extended up to 90 days with mutual written consent of the parties.",
        start_char=0,
        end_char=145,
        judgment_rank=1,
        judgment_score=0.9
    )
    # Query asks if buyer has absolute unilateral right to 90-day extension
    query = "Does the auction purchaser have an unconditional absolute right to extend payment to 90 days under Rule 9(4)?"
    decision = gate.assess_grounding(query, [passage])
    
    assert decision.is_grounded is False
    assert decision.status == GroundingStatus.TOPICALLY_RELEVANT_BUT_INSUFFICIENT_GROUNDING


# Case 8: Party submission misrepresented as judicial holding
def test_case_8_party_submission_misrepresented():
    gate = PropositionGroundingGate()
    passage = EvidencePassage(
        evidence_id="E1",
        document_id="2024_10_800_825",
        case_title="Vidyasagar Prasad",
        passage_text="Mr. Senior Counsel appearing for the appellant vehemently submitted that balance sheet entries do not constitute acknowledgment of debt under Section 18 of the Limitation Act.",
        start_char=0,
        end_char=180,
        judgment_rank=1,
        judgment_score=0.88
    )
    query = "Did the Supreme Court hold that balance sheet entries cannot constitute acknowledgment of debt?"
    decision = gate.assess_grounding(query, [passage])
    
    assert decision.is_grounded is False
    assert decision.status == GroundingStatus.TOPICALLY_RELEVANT_BUT_INSUFFICIENT_GROUNDING
    assert "submission" in decision.rationale.lower() or "holding" in decision.rationale.lower() or "insufficient" in decision.rationale.lower()


# Case 9: Contradictory evidence passages
def test_case_9_contradictory_evidence_passages():
    gate = PropositionGroundingGate()
    p1 = EvidencePassage(
        evidence_id="E1",
        document_id="2024_1",
        case_title="Case A",
        passage_text="The statutory time limit of fifteen days under Rule 9(4) is strictly non-extendable under any circumstances.",
        start_char=0,
        end_char=105,
        judgment_rank=1,
        judgment_score=0.9
    )
    p2 = EvidencePassage(
        evidence_id="E2",
        document_id="2024_2",
        case_title="Case B",
        passage_text="The timeline under Rule 9(4) is not absolute or sacrosanct and is extendable with the consent of parties.",
        start_char=0,
        end_char=105,
        judgment_rank=2,
        judgment_score=0.85
    )
    query = "Is the timeline under Rule 9(4) strictly non-extendable?"
    decision = gate.assess_grounding(query, [p1, p2])
    
    assert decision.is_grounded is False
    assert decision.status == GroundingStatus.TOPICALLY_RELEVANT_BUT_INSUFFICIENT_GROUNDING
    assert "contradict" in decision.rationale.lower() or "conflict" in decision.rationale.lower()


# Case 10: Valid answer with multiple properly attributed citations
def test_case_10_valid_multiple_citations(sample_evidence):
    validator = CitationValidator()
    answer = (
        "The Supreme Court invoked Article 142 to grant admission to an IIT candidate [E1]. "
        "In PMLA proceedings, regular bail requires satisfaction of Section 45 twin conditions [E2]."
    )
    val_result, claims = validator.validate(answer, sample_evidence)
    
    assert val_result.is_valid is True
    assert val_result.validation_status == "valid"
    assert val_result.citation_syntax_valid is True
    assert val_result.citation_existence_valid is True
    assert val_result.attribution_complete is True
    assert val_result.cited_source_ids == ["E1", "E2"]
    assert val_result.valid_source_ids == ["E1", "E2"]
    assert val_result.invalid_source_ids == []
    assert len(val_result.unsupported_sentences) == 0


# Case 11: Safe abstention for unsupported questions
def test_case_11_safe_abstention():
    pipeline = RAGPipeline()
    # Query completely outside 2024 SC corpus
    result = pipeline.query("What is the suspension procedure under Section 18 of the Foreign Contribution Regulation Act 2010?")
    
    assert result.status == "insufficient_evidence"
    assert result.grounding_status in [
        GroundingStatus.TOPICALLY_RELEVANT_BUT_INSUFFICIENT_GROUNDING.value,
        GroundingStatus.NO_RELEVANT_EVIDENCE.value
    ]
    assert result.answer.startswith("INSUFFICIENT EVIDENCE:")
    assert result.citation_validation.is_valid is True  # Valid abstention
    assert result.citation_validation.validation_status == "valid"


# Case 12: Ollama timeout or provider failure
def test_case_12_provider_timeout_and_failure():
    client = TestClient(app)
    
    # Timeout -> HTTP 504
    mock_pipeline_to = MagicMock()
    mock_pipeline_to.query.side_effect = TimeoutError("CPU inference timed out after 240s")
    app.dependency_overrides[get_rag_pipeline] = lambda: mock_pipeline_to
    try:
        resp = client.post("/v1/rag/query", json={"query": "What are bail conditions?", "provider_type": "mock"})
        assert resp.status_code == 504
        assert "timed out" in resp.json()["detail"].lower()
    finally:
        app.dependency_overrides.pop(get_rag_pipeline, None)
    
    # Provider unreachable -> HTTP 503 with masked tracebacks
    with patch("apps.api.routers.rag.get_llm_provider", side_effect=RuntimeError("Connection refused to 11434")):
        resp = client.post("/v1/rag/query", json={"query": "What are bail conditions?", "provider_type": "ollama"})
        assert resp.status_code == 503
        assert "currently unavailable" in resp.json()["detail"].lower()
        assert "traceback" not in resp.json()["detail"].lower()
        assert "11434" not in resp.json()["detail"].lower()


# Case 13: API serialization of invalid and partially supported answers
def test_case_13_api_serialization_invalid_and_partially_supported():
    client = TestClient(app)
    
    # Invalid answer serialization
    mock_pipeline_inv = MagicMock()
    mock_invalid_result = RAGResult(
        query="What are bail conditions?",
        answer="The court granted bail [E#].",
        status="validation_failed",
        grounding_status="validation_failed",
        evidence_passages=[],
        citation_validation=CitationValidationResult(
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
            unsupported_sentences=["The court granted bail [E#]."],
            has_invalid_citations=True,
            validation_notes=["Detected 1 malformed marker: [E#]"]
        ),
        claims=[]
    )
    app.dependency_overrides[get_rag_pipeline] = lambda: mock_pipeline_inv
    mock_pipeline_inv.query.return_value = mock_invalid_result
    try:
        resp = client.post("/v1/rag/query", json={"query": "What are bail conditions?", "provider_type": "mock"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "validation_failed"
        assert data["citation_validation"]["is_valid"] is False
        assert data["citation_validation"]["validation_status"] == "invalid"
        assert len(data["citation_validation"]["validation_notes"]) > 0
    finally:
        app.dependency_overrides.pop(get_rag_pipeline, None)


# Case 14: Warning or diagnostic that must not be exposed as a successful validation result
def test_case_14_warning_diagnostic_never_promoted_to_valid(sample_evidence):
    validator = CitationValidator()
    # Sentence with malformed tag generates warning diagnostic
    answer = "The high court judgment was set aside [E#]."
    val_result, claims = validator.validate(answer, sample_evidence)
    
    assert val_result.is_valid is False
    assert val_result.validation_status == "invalid"
    assert len(val_result.validation_notes) > 0
    # Must never be promoted to valid when malformed warning exists
    assert val_result.is_valid is not True
    assert val_result.validation_status != "valid"
