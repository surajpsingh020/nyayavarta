"""
Milestone 13 Regression Tests: Claim-Level Verification Layer and Contradiction Guard.

Covers the 15 core verification scenarios:
1. test_holding_inversion_contradiction (M10_004 holding inversion)
2. test_party_submission_as_holding_contradicted (Party submission masquerading as holding)
3. test_party_submission_context_partially_supported (Party submission accurately characterized)
4. test_statutory_qualification_omission (Safari Retreats Section 17(5)(d) functionality test omission)
5. test_overgeneralized_holding_partially_supported (Atul Kumar Article 142 overgeneralization)
6. test_multipart_claim_partial_support (Grounded proposition + ungrounded conjunctive proposition)
7. test_unrelated_evidence_unsupported (Syntactically valid citation ID referencing unrelated passage)
8. test_direct_holding_entailment_supported (Direct textual holding entailment)
9. test_unverified_fallback_not_evaluated (Preserving uncertainty when deterministic rules cannot decide)
10. test_conservative_policy_rejects_contradicted (Contradiction guard fail-closed enforcement)
11. test_conservative_policy_rejects_all_unsupported (All unsupported claims rejected)
12. test_conservative_policy_qualifies_partial_support (Partial support accepted with qualification)
13. test_conservative_policy_accepts_clean_abstention (Explicit abstention cleanly accepted)
14. test_m10_034_grounding_fix (M10_034 Section 18 caveat grounding and complementary selection)
15. test_end_to_end_pipeline_verification (End-to-end RAG pipeline with verification counts and notes)
"""
import pytest
import json
from services.rag.models import (
    EvidencePassage,
    ClaimAttribution,
    CitationValidationResult,
    StructuredAnswer,
    StructuredClaim
)
from services.rag.claim_verifier import (
    ClaimVerifier,
    ClaimVerificationStatus,
    ClaimVerificationResult
)
from services.rag.validator import CitationValidator
from services.rag.pipeline import RAGPipeline
from services.rag.providers import LLMProvider, LLMResponse


class DeterministicMockProvider(LLMProvider):
    def __init__(self, content: str):
        self.content = content

    def generate(self, prompt: str, **kwargs) -> LLMResponse:
        return LLMResponse(content=self.content, model_name="deterministic-mock", latency_ms=5.0)


@pytest.fixture
def verifier():
    return ClaimVerifier()


@pytest.fixture
def validator():
    return CitationValidator()


@pytest.fixture
def bijay_agarwal_passage():
    return EvidencePassage(
        evidence_id="E1",
        document_id="2024_8_647_655",
        start_char=1000,
        end_char=1800,
        passage_text=(
            "The High Court fell in error in directing deposit of 20% of the compensation "
            "under Section 148 of the Negotiable Instruments Act. The appellant was merely an "
            "authorized signatory of the company and not the drawer of the cheque. An authorized "
            "signatory who is not the drawer could not be directed to pay interim compensation "
            "under Section 148. The impugned condition is accordingly set aside."
        ),
        case_title="Bijay Agarwal v. M/s Medilines",
        structural_label="judicial_holding"
    )


@pytest.fixture
def submissions_only_passage():
    return EvidencePassage(
        evidence_id="E1",
        document_id="2024_1_100_150",
        start_char=2000,
        end_char=2500,
        passage_text=(
            "Learned senior counsel appearing for the appellant submitted that Section 34 of the "
            "Arbitration and Conciliation Act permits the court to modify the arbitral award where "
            "manifest injustice would otherwise result. Counsel contended that judicial review inherently "
            "includes the power of variation."
        ),
        case_title="Sample Arbitration Matter",
        structural_label="party_submissions"
    )


@pytest.fixture
def safari_retreats_passage():
    return EvidencePassage(
        evidence_id="E1",
        document_id="2024_9_100_200",
        start_char=5000,
        end_char=5800,
        passage_text=(
            "Whether a building constructed for the purpose of letting out qualifies as a plant "
            "under Section 17(5)(d) of the CGST Act is a question of fact that must be determined "
            "by applying the functionality test. If the building satisfies the functionality test, "
            "it can be classified as a plant. We accordingly remand the matter to the High Court."
        ),
        case_title="Chief Commissioner of Central Goods and Services Tax v. M/s Safari Retreats Pvt. Ltd.",
        structural_label="judicial_holding"
    )


@pytest.fixture
def atul_kumar_passage():
    return EvidencePassage(
        evidence_id="E1",
        document_id="2024_10_200_300",
        start_char=1200,
        end_char=1900,
        passage_text=(
            "Petitioner Atul Kumar, belonging to a marginalized social background, could not deposit "
            "the seat acceptance fee before the deadline due to temporary portal login failure. "
            "Exercising our extraordinary powers under Article 142 of the Constitution, this Court directs "
            "that the petitioner be admitted to the allocated seat at IIT Dhanbad on these peculiar facts."
        ),
        case_title="Atul Kumar v. IIT Dhanbad",
        structural_label="judicial_holding"
    )


def test_holding_inversion_contradiction(verifier, bijay_agarwal_passage):
    """Scenario 1: Detect explicit negation / holding inversion (M10_004)."""
    claim = "The Appellate Court may order an authorized signatory to deposit interim compensation under Section 148."
    res = verifier.verify_claim(claim, [bijay_agarwal_passage])
    assert res.status == ClaimVerificationStatus.CONTRADICTED
    assert res.is_contradicted is True
    assert "polarity_contradiction_check" in res.method


def test_party_submission_as_holding_contradicted(verifier, submissions_only_passage):
    """Scenario 2: Party submission asserted as binding court holding is contradicted."""
    claim = "The Supreme Court held that Section 34 permits the court to modify an arbitral award."
    res = verifier.verify_claim(claim, [submissions_only_passage])
    assert res.status == ClaimVerificationStatus.CONTRADICTED
    assert res.is_contradicted is True
    assert "party_submission_as_holding" in res.method


def test_party_submission_context_partially_supported(verifier, submissions_only_passage):
    """Scenario 3: Party submission cited as argument is marked partially supported with uncertainty."""
    claim = "Counsel argued that Section 34 provides authority to vary awards."
    res = verifier.verify_claim(claim, [submissions_only_passage])
    assert res.status == ClaimVerificationStatus.PARTIALLY_SUPPORTED
    assert res.is_partially_supported is True
    assert res.unresolved_uncertainty is not None


def test_statutory_qualification_omission(verifier, safari_retreats_passage):
    """Scenario 4: Omission of required statutory condition/test (functionality test)."""
    claim = "A commercial building constructed for leasing qualifies as plant under Section 17(5)(d) of the CGST Act."
    res = verifier.verify_claim(claim, [safari_retreats_passage])
    assert res.status == ClaimVerificationStatus.PARTIALLY_SUPPORTED
    assert res.omits_statutory_qualification is True


def test_overgeneralized_holding_partially_supported(verifier, atul_kumar_passage):
    """Scenario 5: Overgeneralization of Article 142 order into universal doctrine."""
    claim = "The Supreme Court held that all educational fee deadlines are universally forgiven across higher education."
    res = verifier.verify_claim(claim, [atul_kumar_passage])
    assert res.status == ClaimVerificationStatus.PARTIALLY_SUPPORTED
    assert res.claim_overgeneralizes_holding is True


def test_multipart_claim_partial_support(verifier, atul_kumar_passage):
    """Scenario 6: Multi-part claim with supported antecedent and ungrounded conjunctive proposition."""
    claim = "The Court considered the case of Atul Kumar and ruled that all examination fees must be abolished."
    res = verifier.verify_claim(claim, [atul_kumar_passage])
    assert res.status == ClaimVerificationStatus.PARTIALLY_SUPPORTED
    assert "multipart_claim_check" in res.method


def test_unrelated_evidence_unsupported(verifier, bijay_agarwal_passage):
    """Scenario 7: Syntactically valid citation referencing completely unrelated subject matter."""
    claim = "Agricultural biotechnology patents cannot claim whole plants under Section 3(j)."
    res = verifier.verify_claim(claim, [bijay_agarwal_passage])
    assert res.status == ClaimVerificationStatus.UNSUPPORTED
    assert res.is_supported is False
    assert "unrelated_evidence_check" in res.method


def test_direct_holding_entailment_supported(verifier, bijay_agarwal_passage):
    """Scenario 8: Proposition faithful to court holding is directly supported."""
    claim = "An authorized signatory who is not the drawer could not be directed to pay interim compensation under Section 148."
    res = verifier.verify_claim(claim, [bijay_agarwal_passage])
    assert res.status == ClaimVerificationStatus.SUPPORTED
    assert res.is_supported is True
    assert res.is_contradicted is False


def test_unverified_fallback_not_evaluated(verifier):
    """Scenario 9: Complex proposition where deterministic rules cannot verify semantic truth."""
    ep = EvidencePassage(
        evidence_id="E1",
        document_id="2024_5_1_10",
        start_char=100,
        end_char=400,
        passage_text="The matter requires detailed appreciation of complex evidence regarding company affairs.",
        structural_label="general_text"
    )
    claim = "Company directors bear distinct fiduciary accountability regarding company affairs under state corporate jurisprudence."
    res = verifier.verify_claim(claim, [ep])
    assert res.status == ClaimVerificationStatus.NOT_EVALUATED
    assert res.unresolved_uncertainty is not None


def test_conservative_policy_rejects_contradicted(validator, bijay_agarwal_passage):
    """Scenario 10: Contradicted claim forces validation_status='contradicted', is_valid=False."""
    structured = StructuredAnswer(
        status="answer",
        claims=[
            StructuredClaim(
                text="The Appellate Court may order an authorized signatory to deposit interim compensation under Section 148.",
                evidence_ids=["E1"]
            )
        ]
    )
    res, attributions = validator.validate_structured(structured, [bijay_agarwal_passage])
    assert res.is_valid is False
    assert res.validation_status == "contradicted"
    assert res.semantic_support_status == "contradicted"
    assert res.contradicted_claims_count == 1


def test_conservative_policy_rejects_all_unsupported(validator, bijay_agarwal_passage):
    """Scenario 11: All unsupported substantive claims force rejection."""
    structured = StructuredAnswer(
        status="answer",
        claims=[
            StructuredClaim(
                text="Agricultural seed gene sequences qualify for patenting under biological law.",
                evidence_ids=["E1"]
            )
        ]
    )
    res, attributions = validator.validate_structured(structured, [bijay_agarwal_passage])
    assert res.is_valid is False
    assert res.validation_status == "invalid"
    assert res.unsupported_claims_count == 1


def test_conservative_policy_qualifies_partial_support(validator, safari_retreats_passage):
    """Scenario 12: Partial support returns is_valid=True with validation_status='partially_supported'."""
    structured = StructuredAnswer(
        status="answer",
        claims=[
            StructuredClaim(
                text="A commercial building qualifies as plant under Section 17(5)(d) of the CGST Act.",
                evidence_ids=["E1"]
            )
        ]
    )
    res, attributions = validator.validate_structured(structured, [safari_retreats_passage])
    assert res.is_valid is True
    assert res.validation_status == "partially_supported"
    assert res.semantic_support_status == "partially_supported"
    assert res.partially_supported_claims_count == 1


def test_conservative_policy_accepts_clean_abstention(validator):
    """Scenario 13: Clean abstention accepted without contradiction errors."""
    structured = StructuredAnswer(
        status="abstain",
        claims=[],
        abstention_reason="No relevant judgments on this specific issue in the corpus."
    )
    res, attributions = validator.validate_structured(structured, [])
    assert res.is_valid is True
    assert res.validation_status == "valid"
    assert res.contradicted_claims_count == 0


def test_m10_034_grounding_fix():
    """Scenario 14: M10_034 Section 18 caveat query passes grounding and selects evidence."""
    pipeline = RAGPipeline()
    q = "Does Section 18 of the Limitation Act extend limitation if a balance sheet entry is accompanied by an express, unequivocal disclaimer denying debt liability?"
    
    candidates = pipeline.retriever.retrieve(q, top_k=3, enable_graph=False)
    assert len(candidates) > 0
    assert candidates[0]["document_id"] == "2024_10_1462_1474"
    
    evidence = pipeline.evidence_assembler.assemble_evidence(q, candidates)
    decision = pipeline.grounding_gate.assess_grounding(q, evidence)
    assert decision.is_grounded is True


def test_end_to_end_pipeline_verification():
    """Scenario 15: Pipeline integrates claim verification end-to-end with verification counts and notes."""
    pipeline = RAGPipeline()
    q = "Can an authorized signatory be directed to pay interim compensation under Section 148 of the NI Act?"
    
    # Inverted holding payload
    inverted_payload = json.dumps({
        "status": "answer",
        "claims": [
            {
                "text": "The appellate court may order an authorized signatory to deposit compensation under Section 148.",
                "evidence_ids": ["E1"]
            }
        ]
    })
    provider = DeterministicMockProvider(inverted_payload)
    res = pipeline.query(q, structured_output=True, provider=provider)
    
    assert res.status == "validation_failed"
    assert res.citation_validation.is_valid is False
    assert res.citation_validation.validation_status == "contradicted"
    assert res.citation_validation.contradicted_claims_count == 1
    assert any("polarity_contradiction_check" in note for note in res.citation_validation.verification_notes)
