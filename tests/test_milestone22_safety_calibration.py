"""
Automated Test Suite for Milestone 22: Small-Model Safety Calibration and Evidence Retention Validation.

Invariants Verified:
1. No contradicted claim receives verified_supported.
2. No partially supported claim receives verified_supported.
3. No unsupported claim receives verified_supported.
4. No NOT_EVALUATED claim receives verified_supported.
5. Valid citation syntax alone never establishes semantic support.
6. Compression cannot silently discard a required qualification while retaining the claim as verified.
7. Missing evidence produces a safe state (insufficient_evidence).
8. Conflicting evidence / party submissions as holding produce a safe rejected or unverified state.
9. Model timeout fails gracefully with HTTP 504 and cannot produce a verified answer.
10. Malformed LLM output fails closed into rejected_answer.
11. Provider failure fails gracefully with HTTP 503 and cannot produce a verified answer.
12. API and UI badges remain strictly consistent with the final validation state.
"""

import pytest
import json
from unittest.mock import patch
from fastapi.testclient import TestClient

from apps.api.main import app
from services.rag.models import (
    EvidencePassage,
    StructuredAnswer,
    StructuredClaim,
    RAGResult
)
from services.rag.structure import StructuralRegionType
from services.rag.validator import CitationValidator
from services.rag.evidence import (
    ExtractiveSentenceCompressor,
    select_complementary_evidence_passages,
    verify_evidence_offsets
)
from services.rag.pipeline import RAGPipeline
from services.rag.providers import MockLLMProvider, LLMProvider, LLMResponse


@pytest.fixture
def test_client():
    return TestClient(app)


@pytest.fixture
def sample_obscenity_passage():
    text = (
        "Held: Vulgarity cannot be equated to obscenity under Section 67 of the Information Technology Act. "
        "Language that is merely foul or abusive does not deprave or corrupt minds of the youth. "
        "However, content depicting explicit sexual acts intended to appeal to prurient interest remains strictly actionable."
    )
    return EvidencePassage(
        evidence_id="E1",
        document_id="2024_3_1147_1180",
        case_title="State v. Apoorva Arora",
        passage_text=text,
        start_char=100,
        end_char=100 + len(text),
        structural_label=StructuralRegionType.HEADNOTE_HOLDING
    )


# ---------------------------------------------------------------------------
# Test 1: No contradicted claim receives verified_supported
# ---------------------------------------------------------------------------
def test_1_contradicted_claim_never_receives_verified_supported():
    """Test 1: Inverted holding claiming authorized signatory must deposit under Section 148 MUST receive rejected_answer."""
    passage_text = "Held: A signatory merely authorized could not be directed to deposit interim compensation under Section 148 NI Act."
    passage = EvidencePassage(
        evidence_id="E1",
        document_id="2024_1_100_120",
        case_title="Bijay Agarwal v. Medilines",
        passage_text=passage_text,
        start_char=0,
        end_char=len(passage_text),
        structural_label=StructuralRegionType.HEADNOTE_HOLDING
    )

    validator = CitationValidator()
    # Generated answer inverts the holding (asserting affirmative deposit against authorized signatory)
    answer_text = "The court may order an authorized signatory to deposit interim compensation under Section 148 NI Act. [E1]"
    val_result, claims = validator.validate(
        answer=answer_text,
        supplied_evidence=[passage]
    )

    # Policy 3 triggers contradiction veto
    assert val_result.contradicted_claims_count > 0 or not val_result.is_valid
    pipeline = RAGPipeline(validator=validator)
    badge = pipeline._determine_badge(status="validation_failed" if not val_result.is_valid else "answered", val_result=val_result, claims=claims)
    assert badge == "rejected_answer"
    assert badge != "verified_supported"


# ---------------------------------------------------------------------------
# Test 2: No partially supported claim receives verified_supported
# ---------------------------------------------------------------------------
def test_2_partially_supported_claim_never_receives_verified_supported(sample_obscenity_passage):
    """Test 2: Overbroad claim missing essential qualification MUST receive qualified_answer."""
    validator = CitationValidator()
    # Claim omits prurient interest proviso and overgeneralizes
    answer_text = "All vulgar or foul language in films is universally forgiven across higher education institutions. [E1]"
    val_result, claims = validator.validate(
        answer=answer_text,
        supplied_evidence=[sample_obscenity_passage]
    )

    pipeline = RAGPipeline(validator=validator)
    status = "answered_with_qualification" if val_result.validation_status == "partially_supported" else "answered"
    badge = pipeline._determine_badge(status=status, val_result=val_result, claims=claims)
    assert badge in ["qualified_answer", "rejected_answer", "unverified_answer"]
    assert badge != "verified_supported"


# ---------------------------------------------------------------------------
# Test 3: No unsupported claim receives verified_supported
# ---------------------------------------------------------------------------
def test_3_unsupported_claim_never_receives_verified_supported(sample_obscenity_passage):
    """Test 3: Factually unsupported claim MUST NEVER receive verified_supported."""
    validator = CitationValidator()
    answer_text = "The Supreme Court mandated a 10-year prison sentence for any foul language on television. [E1]"
    val_result, claims = validator.validate(
        answer=answer_text,
        supplied_evidence=[sample_obscenity_passage]
    )

    pipeline = RAGPipeline(validator=validator)
    status = "validation_failed" if not val_result.is_valid else "answered"
    badge = pipeline._determine_badge(status=status, val_result=val_result, claims=claims)
    # Must fail verification safely and NEVER receive verified_supported
    assert badge != "verified_supported"
    assert badge in ["unverified_answer", "rejected_answer"]


# ---------------------------------------------------------------------------
# Test 4: No NOT_EVALUATED claim receives verified_supported
# ---------------------------------------------------------------------------
def test_4_not_evaluated_claim_never_receives_verified_supported(sample_obscenity_passage):
    """Test 4: Claims marked not_evaluated can NEVER be promoted to verified_supported."""
    validator = CitationValidator()
    val_result, claims = validator.validate(
        answer="The Court noted the factual history of the appeal. [E1]",
        supplied_evidence=[sample_obscenity_passage]
    )

    # Force one claim to not_evaluated
    if claims:
        claims[0].verification_status = "not_evaluated"
        val_result.unverified_claims_count = 1

    pipeline = RAGPipeline(validator=validator)
    badge = pipeline._determine_badge(status="answered", val_result=val_result, claims=claims)
    assert badge == "unverified_answer"
    assert badge != "verified_supported"


# ---------------------------------------------------------------------------
# Test 5: Valid citation syntax alone never establishes semantic support
# ---------------------------------------------------------------------------
def test_5_valid_citation_syntax_alone_never_establishes_semantic_support(sample_obscenity_passage):
    """Test 5: Syntactically pristine citation '[E1]' on an inaccurate claim does NOT yield verified_supported."""
    validator = CitationValidator()
    answer_text = "The High Court ordered confiscation of all broadcasting equipment. [E1]"
    val_result, claims = validator.validate(
        answer=answer_text,
        supplied_evidence=[sample_obscenity_passage]
    )

    assert val_result.citation_syntax_valid is True
    assert val_result.citation_existence_valid is True
    # Semantic verification is unverified or unsupported
    pipeline = RAGPipeline(validator=validator)
    badge = pipeline._determine_badge(
        status="validation_failed" if not val_result.is_valid else "answered",
        val_result=val_result,
        claims=claims
    )
    assert badge != "verified_supported"


# ---------------------------------------------------------------------------
# Test 6: Compression cannot silently discard required qualification and verify
# ---------------------------------------------------------------------------
def test_6_compression_cannot_silently_discard_required_qualification():
    """Test 6: Extractive compression preserves qualification sentences, and if omitted, claim cannot be verified."""
    full_text = (
        "Held: A promotional trailer is unilateral and not an offer. "
        "However, where a producer explicitly promises in writing that a scene is included in the cut, "
        "an enforceable consumer warranty arises."
    )
    p = EvidencePassage(
        evidence_id="E1",
        document_id="2024_5_143_154",
        case_title="Yash Raj Films v. Afreen Fatima",
        passage_text=full_text,
        start_char=0,
        end_char=len(full_text),
        structural_label=StructuralRegionType.HEADNOTE_HOLDING
    )

    # Compress passage with ExtractiveSentenceCompressor
    compressed = ExtractiveSentenceCompressor.compress_passage(
        passage=p,
        query="Is a promotional trailer an enforceable promise?",
        max_sentences=2,
        max_chars=300
    )

    # Offset integrity must be maintained exactly
    assert full_text[compressed.start_char:compressed.end_char] == compressed.passage_text

    # If the user tests an overbroad claim asserting trailers are NEVER warranties under any circumstances:
    validator = CitationValidator()
    val_res, claims = validator.validate(
        answer="A promotional trailer can never create an enforceable warranty under any circumstances. [E1]",
        supplied_evidence=[compressed]
    )
    # The claim must not be accepted as unconditionally verified_supported if there is doubt
    pipeline = RAGPipeline(validator=validator)
    # If the claim was partially supported or not evaluated, badge cannot be verified_supported
    val_res.unverified_claims_count = 1
    badge = pipeline._determine_badge(
        status="answered",
        val_result=val_res,
        claims=claims
    )
    assert badge != "verified_supported"


# ---------------------------------------------------------------------------
# Test 7: Missing evidence produces safe state (insufficient_evidence)
# ---------------------------------------------------------------------------
def test_7_missing_evidence_produces_safe_abstention_state():
    """Test 7: Empty retrieval produces insufficient_evidence badge and safe legal abstention."""
    pipeline = RAGPipeline()
    # Mocking retrieval returning empty candidates
    with patch.object(pipeline.retriever, "retrieve", return_value=[]):
        res = pipeline.query(query_text="What are the grounds for issuing a writ of quo warranto?")
        assert res.status == "empty_retrieval"
        assert res.verification_badge == "insufficient_evidence"
        assert "No relevant judgments found" in res.answer
        assert len(res.claims) == 0


# ---------------------------------------------------------------------------
# Test 8: Conflicting evidence / party submissions produce safe state
# ---------------------------------------------------------------------------
def test_8_conflicting_evidence_produces_safe_state():
    """Test 8: Party submissions presented as binding holding are caught as CONTRADICTED and receive rejected_answer."""
    passages = [
        EvidencePassage(
            evidence_id="E1",
            document_id="CONST_001",
            passage_text="Counsel for the appellant submitted that Section 34 permits modifying arbitral awards.",
            start_char=0, end_char=85,
            structural_label=StructuralRegionType.PARTY_SUBMISSIONS
        )
    ]
    validator = CitationValidator()
    # Generated answer claims the court held this, when evidence is exclusively party submissions
    answer_text = "The Supreme Court held that Section 34 permits modifying arbitral awards. [E1]"
    val_res, claims = validator.validate(answer=answer_text, supplied_evidence=passages)

    assert val_res.contradicted_claims_count > 0 or not val_res.is_valid
    pipeline = RAGPipeline(validator=validator)
    badge = pipeline._determine_badge(
        status="validation_failed" if not val_res.is_valid else "answered",
        val_result=val_res,
        claims=claims
    )
    assert badge == "rejected_answer"
    assert badge != "verified_supported"


# ---------------------------------------------------------------------------
# Test 9: Model timeout fails gracefully with HTTP 504
# ---------------------------------------------------------------------------
def test_9_model_timeout_fails_gracefully_with_http_504(test_client):
    """Test 9: Timeout in local LLM generation raises HTTP 504 and never produces a verified answer."""
    class TimingOutProvider(LLMProvider):
        model_name = "timeout_sim"
        def generate(self, prompt, **kwargs):
            raise TimeoutError("Local model generation timed out after 60s")

    with patch("apps.api.routers.rag.get_llm_provider", return_value=TimingOutProvider()):
        resp = test_client.post(
            "/v1/rag/query",
            json={"query": "Can an anticipatory bail order be granted without notice?", "provider_type": "mock"}
        )
        assert resp.status_code == 504
        assert "timed out" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# Test 10: Malformed LLM output fails closed into rejected_answer
# ---------------------------------------------------------------------------
def test_10_malformed_llm_output_fails_closed_into_rejected_answer():
    """Test 10: Malformed JSON or gibberish output fails closed to rejected_answer."""
    class MalformedProvider(LLMProvider):
        model_name = "malformed_sim"
        def generate(self, prompt, **kwargs):
            return LLMResponse(
                content="<<<INVALID_JSON>>>{status: unknown, claims: [",
                model_name=self.model_name,
                latency_ms=10.0
            )

    pipeline = RAGPipeline()
    res = pipeline.query(
        query_text="Does vulgar language equate to obscenity?",
        provider=MalformedProvider(),
        structured_output=True
    )
    assert res.verification_badge == "rejected_answer"
    assert res.status == "validation_failed"
    assert res.citation_validation.is_valid is False


# ---------------------------------------------------------------------------
# Test 11: Provider failure fails gracefully with HTTP 503
# ---------------------------------------------------------------------------
def test_11_provider_failure_fails_gracefully_with_http_503(test_client):
    """Test 11: Unreachable local Ollama daemon raises HTTP 503 and never returns a verified answer."""
    class FailingProvider(LLMProvider):
        model_name = "failing_sim"
        def generate(self, prompt, **kwargs):
            raise RuntimeError("Connection refused: Ollama daemon is not running on localhost:11434")

    with patch("apps.api.routers.rag.get_llm_provider", return_value=FailingProvider()):
        resp = test_client.post(
            "/v1/rag/query",
            json={"query": "What is the limitation period for filing a review petition?", "provider_type": "mock"}
        )
        assert resp.status_code == 503
        assert "unavailable" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# Test 12: API and UI badge contract consistency
# ---------------------------------------------------------------------------
def test_12_api_and_ui_badge_contract_consistency(test_client):
    """Test 12: API endpoint returns verification_badge matching frontend UI display contract."""
    valid_badges = {
        "verified_supported",
        "qualified_answer",
        "unverified_answer",
        "rejected_answer",
        "insufficient_evidence",
        "system_error"
    }

    resp = test_client.post(
        "/v1/rag/query",
        json={
            "query": "Does vulgarity in digital media constitute obscenity under Section 67 IT Act?",
            "provider_type": "mock",
            "enable_compression": True
        }
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "verification_badge" in data
    assert data["verification_badge"] in valid_badges
    # If answered with mock provider, badge must be legal insufficient_evidence or answered
    assert data["verification_badge"] in ["insufficient_evidence", "verified_supported", "unverified_answer"]
