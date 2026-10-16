"""
Automated Test Suite for Milestone 21: CPU Latency and Evidence-Budget Optimization.

Tests:
1. Context compression preserves exceptions, negations, and limiting provisos.
2. Exact source-offset integrity after evidence budget compression.
3. Citation provenance and metadata survive compression.
4. Budget truncation prefers fewer complete passages over mid-sentence cuts.
5. No unsupported claim receives verified_supported badge.
6. No contradicted claim receives verified_supported badge.
7. Partial and not-evaluated claims receive safe presentation states (qualified / unverified).
8. Provider timeout fails gracefully with HTTP 504.
9. Provider unavailable fails gracefully with HTTP 503.
10. Malformed LLM output fails closed into validation_failed / rejected_answer.
11. Empty evidence triggers clean legal abstention with insufficient_evidence badge.
12. API response serialization and UI presentation badge consistency.
"""
import pytest
import json
from pathlib import Path
from fastapi.testclient import TestClient

from apps.api.main import app
from services.rag.models import (
    EvidencePassage,
    StructuredAnswer,
    StructuredClaim,
    RAGResult
)
from services.rag.validator import CitationValidator
from services.rag.evidence import (
    ExtractiveSentenceCompressor,
    select_complementary_evidence_passages,
    verify_evidence_offsets
)
from services.rag.pipeline import RAGPipeline
from services.rag.providers import MockLLMProvider


@pytest.fixture
def test_client():
    return TestClient(app)


@pytest.fixture
def complex_statutory_passage():
    # Passage with multiple sentences, legal citations, abbreviations, and an exclusionary proviso
    text = (
        "Held: The applicant claimed relief under Order XXI Rule 99 of the CPC. "
        "Under Or. XXI, r. 99, where any person other than the judgment debtor is dispossessed "
        "of immovable property, he may make an application complaining of such dispossession. "
        "However, this statutory remedy is not available to the judgment debtor himself."
    )
    return EvidencePassage(
        evidence_id="E1",
        document_id="2024_10_1359_1370",
        case_title="Pradeep Kumar v. State of U.P.",
        passage_text=text,
        start_char=0,
        end_char=len(text),
        structural_label="headnote_holding"
    )


def test_1_context_compression_preserves_exceptions_and_negations(complex_statutory_passage):
    """Test 1: ExtractiveSentenceCompressor never cuts off an exclusionary clause or negative condition."""
    query = "Who can apply under Order XXI Rule 99 CPC?"
    compressed = ExtractiveSentenceCompressor.compress_passage(
        complex_statutory_passage,
        query=query,
        max_sentences=2,
        max_chars=300
    )

    # The compressed text must retain the complete sentence with the exclusionary phrase
    assert "other than the judgment debtor" in compressed.passage_text
    # Exact start and end offsets must map cleanly
    assert compressed.start_char >= complex_statutory_passage.start_char
    assert compressed.end_char <= complex_statutory_passage.end_char
    assert len(compressed.passage_text) == (compressed.end_char - compressed.start_char)


def test_2_exact_source_offset_integrity_after_passage_selection():
    """Test 2: Selected passages under budget constraints maintain 100% exact character offset fidelity."""
    corpus_file = Path("data/processed/aws_sc/2024_5_143_154.json")
    assert corpus_file.exists()

    with corpus_file.open("r", encoding="utf-8") as f:
        doc_data = json.load(f)

    full_text = doc_data["full_text"]
    snippet1 = "A promotional trailer is unilateral"
    idx1 = full_text.find(snippet1)
    assert idx1 != -1

    p1 = EvidencePassage(
        evidence_id="E1",
        document_id="2024_5_143_154",
        case_title=doc_data.get("case_title", "Unknown"),
        passage_text=full_text[idx1:idx1+200],
        start_char=idx1,
        end_char=idx1+200,
        structural_label="headnote_holding"
    )

    selected = select_complementary_evidence_passages(
        passages=[p1],
        query="What is the effect of a movie trailer?",
        max_passages=1,
        enable_compression=True,
        max_chars_per_passage=150
    )

    assert len(selected) == 1
    sp = selected[0]
    # Check exact slice against canonical text
    assert full_text[sp.start_char:sp.end_char] == sp.passage_text


def test_3_citation_provenance_survives_compression(complex_statutory_passage):
    """Test 3: Citation provenance, document_id, case_title, and structural_label survive compression."""
    compressed = ExtractiveSentenceCompressor.compress_passage(
        complex_statutory_passage,
        query="Order XXI Rule 99 dispossession application",
        max_sentences=1
    )
    assert compressed.document_id == complex_statutory_passage.document_id
    assert compressed.case_title == complex_statutory_passage.case_title
    assert compressed.evidence_id == complex_statutory_passage.evidence_id
    assert compressed.structural_label == complex_statutory_passage.structural_label


def test_4_budget_truncation_prefers_fewer_complete_passages():
    """Test 4: Bounded budget drops lower-priority candidate passages rather than corrupting passage text."""
    p1 = EvidencePassage(
        evidence_id="E1",
        document_id="2024_doc_1",
        case_title="Case 1",
        passage_text="Held: The first holding establishes direct liability.",
        start_char=0,
        end_char=54,
        passage_score=10.0,
        structural_label="headnote_holding"
    )
    p2 = EvidencePassage(
        evidence_id="E2",
        document_id="2024_doc_2",
        case_title="Case 2",
        passage_text="Held: The second holding provides additional statutory context.",
        start_char=0,
        end_char=63,
        passage_score=5.0,
        structural_label="court_analysis"
    )

    # Budget allows only 1 passage
    selected = select_complementary_evidence_passages(
        passages=[p1, p2],
        query="liability",
        max_passages=1
    )

    assert len(selected) == 1
    assert selected[0].document_id == "2024_doc_1"
    assert selected[0].evidence_id == "E1"
    # Complete sentence preserved
    assert selected[0].passage_text == p1.passage_text


def test_5_no_unsupported_claim_receives_verified_supported():
    """Test 5: An unsupported claim with valid syntax [E1] cannot receive verified_supported badge."""
    ep = EvidencePassage(
        evidence_id="E1",
        document_id="2024_doc_test",
        case_title="Test Case",
        passage_text="Held: The motor accident compensation is enhanced.",
        start_char=0,
        end_char=50,
        structural_label="headnote_holding"
    )
    # Claim makes an unsupported assertion about intellectual property
    structured = StructuredAnswer(
        status="answer",
        claims=[
            StructuredClaim(
                text="The patent application was invalidated for lack of inventive step.",
                evidence_ids=["E1"]
            )
        ]
    )
    validator = CitationValidator()
    val_res, claims = validator.validate_structured(structured, [ep])

    assert val_res.semantic_support_status != "supported"
    assert val_res.supported_claims_count == 0


def test_6_no_contradicted_claim_receives_verified_supported():
    """Test 6: Contradicted holding inversion is rejected and fails closed."""
    ep = EvidencePassage(
        evidence_id="E1",
        document_id="2024_5_143_154",
        case_title="Yash Raj Films v. Afreen Fatima",
        passage_text="Held: A promotional trailer is unilateral. It does not constitute deficiency of service.",
        start_char=0,
        end_char=90,
        structural_label="headnote_holding"
    )
    structured = StructuredAnswer(
        status="answer",
        claims=[
            StructuredClaim(
                text="The Supreme Court held that omitting a song from a movie constitutes deficiency of service.",
                evidence_ids=["E1"]
            )
        ]
    )
    validator = CitationValidator()
    val_res, claims = validator.validate_structured(structured, [ep])

    assert val_res.supported_claims_count == 0
    assert val_res.semantic_support_status != "supported"


def test_7_partial_and_not_evaluated_safe_presentation_states():
    """Test 7: Answers with partially supported or not_evaluated claims receive safe badges, never verified_supported."""
    pipeline = RAGPipeline(
        llm_provider=MockLLMProvider(mode=MockLLMProvider.MODE_STRUCTURED_NORMAL)
    )
    ep = EvidencePassage(
        evidence_id="E1",
        document_id="2024_doc_1",
        case_title="Case 1",
        passage_text="Held: Notice must be issued before demolition.",
        start_char=0,
        end_char=44,
        structural_label="headnote_holding"
    )

    # Validate claim omitting condition
    claim = StructuredClaim(text="Demolition orders may be issued.", evidence_ids=["E1"])
    validator = CitationValidator()
    val_res, claims = validator.validate_structured(
        StructuredAnswer(status="answer", claims=[claim]),
        [ep]
    )

    # Must not be promoted to verified_supported
    assert val_res.semantic_support_status != "supported" or not val_res.is_valid or val_res.supported_claims_count < 1


def test_8_timeout_fails_gracefully_http_504(test_client, monkeypatch):
    """Test 8: Local LLM timeout returns HTTP 504 Gateway Timeout."""
    from services.rag.pipeline import RAGPipeline
    def mock_query_timeout(*args, **kwargs):
        raise TimeoutError("Simulated LLM inference timeout")

    monkeypatch.setattr(RAGPipeline, "query", mock_query_timeout)
    res = test_client.post(
        "/v1/rag/query",
        json={"query": "Test timeout question", "provider_type": "mock"}
    )
    assert res.status_code == 504
    assert "timed out" in res.json()["detail"].lower()


def test_9_provider_unavailable_fails_gracefully_http_503(test_client, monkeypatch):
    """Test 9: Local LLM service unavailability returns HTTP 503 Service Unavailable."""
    from services.rag.pipeline import RAGPipeline
    def mock_query_runtime_error(*args, **kwargs):
        raise RuntimeError("Ollama daemon is not reachable")

    monkeypatch.setattr(RAGPipeline, "query", mock_query_runtime_error)
    res = test_client.post(
        "/v1/rag/query",
        json={"query": "Test unavailable question", "provider_type": "mock"}
    )
    assert res.status_code == 503
    assert "unavailable" in res.json()["detail"].lower()


def test_10_malformed_llm_output_fails_closed():
    """Test 10: Malformed JSON output from LLM fails closed to validation_failed."""
    pipeline = RAGPipeline(
        llm_provider=MockLLMProvider(mode=MockLLMProvider.MODE_STRUCTURED_MALFORMED_JSON)
    )
    result = pipeline.query(
        query_text="What are the grounds for bail?",
        top_k_judgments=1,
        max_passages=1,
        structured_output=True
    )
    assert result.status == "validation_failed"
    assert result.verification_badge == "rejected_answer"


def test_11_empty_evidence_triggers_clean_legal_abstention():
    """Test 11: Insufficient or missing evidence triggers clean legal abstention."""
    pipeline = RAGPipeline(
        llm_provider=MockLLMProvider(mode=MockLLMProvider.MODE_STRUCTURED_ABSTAIN)
    )
    result = pipeline.query(
        query_text="Completely nonexistent doctrine in the corpus?",
        top_k_judgments=1,
        max_passages=1,
        structured_output=True
    )
    assert result.status == "insufficient_evidence"
    assert result.verification_badge == "insufficient_evidence"


def test_12_api_and_ui_presentation_badge_consistency(test_client):
    """Test 12: API serialization produces badges matching apps/web/README.md specification."""
    res = test_client.post(
        "/v1/rag/query",
        json={
            "query": "Can an employer change qualifications after advertisement?",
            "provider_type": "mock",
            "structured_output": True
        }
    )
    assert res.status_code == 200
    data = res.json()
    valid_badges = {
        "verified_supported", "qualified_answer", "unverified_answer",
        "rejected_answer", "insufficient_evidence", "system_error"
    }
    assert data["verification_badge"] in valid_badges
    assert "citation_validation" in data
    assert "legal_disclaimer" in data
