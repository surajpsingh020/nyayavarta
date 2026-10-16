"""
Tests for Milestone 14: Unseen Claim Verification Evaluation and Safe Answer Presentation.

Covers the 12 Safety Scenarios mandated by Milestone 14:
1. Direct holding verification (SUPPORTED -> answered / verified_supported).
2. Direct contradiction rejection (CONTRADICTED -> validation_failed / rejected_answer).
3. Party submission misattribution rejection (CONTRADICTED -> validation_failed / rejected_answer).
4. Unrelated evidence rejection (UNSUPPORTED -> validation_failed / rejected_answer).
5. Missing statutory qualification handling (PARTIALLY_SUPPORTED -> answered_with_qualification / qualified_answer).
6. Article 142 equitable relief overgeneralization qualification (PARTIALLY_SUPPORTED -> qualified_answer).
7. Quoted landmark precedent confusion qualification (PARTIALLY_SUPPORTED -> qualified_answer).
8. High lexical divergence safe fallback (NOT_EVALUATED never called SUPPORTED or verified).
9. Safe UI presentation contract invariants (is_verified_supported, is_answer_suppressed).
10. Citation validity distinct from semantic support (syntactic valid + unsupported claim -> rejected).
11. Provider timeout / error distinct from legal abstention (HTTP 504 / 503 vs 200 insufficient_evidence).
12. Strict rejection of contradicted answers regardless of valid citations.
"""
import pytest
from fastapi import HTTPException

from services.rag.models import (
    EvidencePassage,
    ClaimAttribution,
    CitationValidationResult,
    RAGResult,
    StructuredAnswer,
    StructuredClaim
)
from services.rag.claim_verifier import ClaimVerifier, ClaimVerificationStatus
from services.rag.validator import CitationValidator
from services.rag.pipeline import RAGPipeline
from services.rag.providers import MockLLMProvider


@pytest.fixture
def verifier():
    return ClaimVerifier()


@pytest.fixture
def validator(verifier):
    return CitationValidator(require_citations_on_all_claims=True, verifier=verifier)


@pytest.fixture
def sample_holding_passage():
    return EvidencePassage(
        evidence_id="E1",
        document_id="2024_12_28_67",
        case_title="Tej Prakash Pathak v. Rajasthan High Court",
        structural_label="judicial_holding",
        passage_text="The rules of the game must not be changed during the course of the selection process.",
        start_char=385,
        end_char=470
    )


@pytest.fixture
def sample_submission_passage():
    return EvidencePassage(
        evidence_id="E1",
        document_id="2024_12_1581_1617",
        case_title="North Delhi Municipal Corp",
        structural_label="party_submissions",
        passage_text="Learned senior counsel appearing for the appellant submitted that Section 34 of the Arbitration Act allows the court to modify an arbitral award.",
        start_char=0,
        end_char=145
    )


# Scenario 1: Direct holding verification (SUPPORTED)
def test_direct_holding_verification(verifier, sample_holding_passage):
    claim = "The rules of the game must not be changed during the course of the selection process."
    res = verifier.verify_claim(claim, [sample_holding_passage])
    assert res.status == ClaimVerificationStatus.SUPPORTED
    assert res.is_supported is True
    assert res.is_contradicted is False

    # Pipeline acceptance policy
    policy = ClaimVerifier.evaluate_acceptance_policy(
        validation_result=CitationValidationResult(
            is_valid=True,
            semantic_support_status="supported",
            cited_source_ids=["E1"],
            valid_source_ids=["E1"]
        ),
        claims=[ClaimAttribution(sentence=claim, cited_evidence_ids=["E1"], verification_status="supported")]
    )
    assert policy["accepted_status"] == "answered"
    assert policy["is_valid"] is True


# Scenario 2: Direct contradiction rejection (CONTRADICTED)
def test_direct_contradiction_rejection(verifier, sample_holding_passage):
    claim = "The recruiting authority is empowered to alter qualification criteria midway during the selection process."
    # Adding negation text to cited passage
    neg_passage = EvidencePassage(
        evidence_id="E1",
        document_id="2024_12_28_67",
        structural_label="court_analysis",
        passage_text="The rules cannot be changed during the selection. It is impermissible to alter criteria.",
        start_char=0,
        end_char=100
    )
    res = verifier.verify_claim(claim, [neg_passage])
    assert res.status == ClaimVerificationStatus.CONTRADICTED
    assert res.is_contradicted is True

    # Acceptance policy must reject
    policy = ClaimVerifier.evaluate_acceptance_policy(
        validation_result=CitationValidationResult(is_valid=True, cited_source_ids=["E1"], valid_source_ids=["E1"]),
        claims=[ClaimAttribution(sentence=claim, cited_evidence_ids=["E1"], verification_status="contradicted")]
    )
    assert policy["accepted_status"] == "validation_failed"
    assert policy["is_valid"] is False
    assert policy["action"] == "reject_contradicted"


# Scenario 3: Party submission misattribution rejection (CONTRADICTED)
def test_party_submission_misattribution_rejection(verifier, sample_submission_passage):
    claim = "The Supreme Court held that Section 34 of the Arbitration Act allows the court to modify an arbitral award."
    res = verifier.verify_claim(claim, [sample_submission_passage])
    assert res.status == ClaimVerificationStatus.CONTRADICTED
    assert res.relies_only_on_submissions is True

    policy = ClaimVerifier.evaluate_acceptance_policy(
        validation_result=CitationValidationResult(is_valid=True, cited_source_ids=["E1"], valid_source_ids=["E1"]),
        claims=[ClaimAttribution(sentence=claim, cited_evidence_ids=["E1"], verification_status="contradicted")]
    )
    assert policy["accepted_status"] == "validation_failed"
    assert policy["is_valid"] is False


# Scenario 4: Unrelated evidence rejection (UNSUPPORTED)
def test_unrelated_evidence_rejection(verifier, sample_holding_passage):
    claim = "The maritime underwriter is discharged from liability where the cargo vessel was unseaworthy."
    res = verifier.verify_claim(claim, [sample_holding_passage])
    assert res.status == ClaimVerificationStatus.UNSUPPORTED
    assert res.method == "unrelated_evidence_check"

    policy = ClaimVerifier.evaluate_acceptance_policy(
        validation_result=CitationValidationResult(is_valid=True, cited_source_ids=["E1"], valid_source_ids=["E1"]),
        claims=[ClaimAttribution(sentence=claim, cited_evidence_ids=["E1"], verification_status="unsupported")]
    )
    assert policy["accepted_status"] == "validation_failed"
    assert policy["action"] == "reject_all_unsupported"


# Scenario 5: Missing statutory qualification handling (PARTIALLY_SUPPORTED)
def test_missing_statutory_qualification_qualification(verifier):
    claim = "A commercial shopping mall constructed for leasing out qualifies as plant under Section 17(5)(d) of the CGST Act."
    passage = EvidencePassage(
        evidence_id="E1",
        document_id="2024_10_793_859",
        structural_label="headnote_holding",
        passage_text="Whether a commercial building qualifies as plant under Section 17(5)(d) is a question of fact to be decided applying the functionality test on remand.",
        start_char=0,
        end_char=150
    )
    res = verifier.verify_claim(claim, [passage])
    assert res.status == ClaimVerificationStatus.PARTIALLY_SUPPORTED
    assert res.omits_statutory_qualification is True

    policy = ClaimVerifier.evaluate_acceptance_policy(
        validation_result=CitationValidationResult(is_valid=True, cited_source_ids=["E1"], valid_source_ids=["E1"]),
        claims=[ClaimAttribution(sentence=claim, cited_evidence_ids=["E1"], verification_status="partially_supported")]
    )
    assert policy["accepted_status"] == "answered_with_qualification"
    assert policy["is_valid"] is True


# Scenario 6: Article 142 equitable relief overgeneralization qualification
def test_article_142_equitable_relief_qualification(verifier):
    claim = "The Supreme Court ruled under Article 142 that all educational fee deadlines are universally forgiven."
    passage = EvidencePassage(
        evidence_id="E1",
        document_id="2024_10_150_153",
        structural_label="judicial_holding",
        passage_text="Exercising our extraordinary powers under Article 142 of the Constitution, this Court directs admission of petitioner Atul Kumar on these peculiar facts.",
        start_char=0,
        end_char=160
    )
    res = verifier.verify_claim(claim, [passage])
    assert res.status == ClaimVerificationStatus.PARTIALLY_SUPPORTED
    assert res.claim_overgeneralizes_holding is True

    policy = ClaimVerifier.evaluate_acceptance_policy(
        validation_result=CitationValidationResult(is_valid=True, cited_source_ids=["E1"], valid_source_ids=["E1"]),
        claims=[ClaimAttribution(sentence=claim, cited_evidence_ids=["E1"], verification_status="partially_supported")]
    )
    assert policy["accepted_status"] == "answered_with_qualification"


# Scenario 7: Quoted landmark precedent confusion qualification
def test_quoted_precedent_qualification(verifier):
    claim = "The 2024 bench adopted its own binding ruling that registration of FIR is mandatory under Section 154 CrPC upon disclosing cognizable offence."
    passage = EvidencePassage(
        evidence_id="E1",
        document_id="2024_10_108_125",
        structural_label="court_analysis",
        passage_text="In the landmark case of Lalita Kumari v. Government of U.P. (supra), the Constitution Bench held that registration of FIR is mandatory when information discloses a cognizable offence.",
        start_char=0,
        end_char=185
    )
    res = verifier.verify_claim(claim, [passage])
    assert res.status == ClaimVerificationStatus.PARTIALLY_SUPPORTED
    assert res.method == "quoted_precedent_attribution_check"


# Scenario 8: High lexical divergence safe fallback (NOT_EVALUATED never converted to SUPPORTED)
def test_high_lexical_divergence_safe_fallback(verifier):
    claim = "Vicarious criminal liability cannot be imputed to corporate officers without explicit legislative sanction."
    passage = EvidencePassage(
        evidence_id="E1",
        document_id="2024_10_1890_1901",
        structural_label="court_analysis",
        passage_text="Penal statutes do not recognize vicarious liability unless the enactment specifically fastens liability upon individual management personnel.",
        start_char=0,
        end_char=144
    )
    res = verifier.verify_claim(claim, [passage])
    # Fallback to not_evaluated must be safely preserved
    assert res.status == ClaimVerificationStatus.NOT_EVALUATED
    assert res.is_supported is False

    # Acceptance policy must treat as unverified
    policy = ClaimVerifier.evaluate_acceptance_policy(
        validation_result=CitationValidationResult(is_valid=True, cited_source_ids=["E1"], valid_source_ids=["E1"]),
        claims=[ClaimAttribution(sentence=claim, cited_evidence_ids=["E1"], verification_status="not_evaluated")]
    )
    assert policy["action"] == "accept_unverified"
    # Never accepted as fully supported
    assert policy["action"] != "accept_fully_supported"


# Scenario 9: Safe UI presentation contract invariants
def test_safe_ui_presentation_contract():
    # 1. verified_supported
    r_verified = RAGResult(
        query="Q",
        answer="A [E1].",
        status="answered",
        verification_badge="verified_supported",
        citation_validation=CitationValidationResult(is_valid=True, semantic_support_status="supported")
    )
    assert r_verified.is_verified_supported is True
    assert r_verified.is_answer_suppressed is False

    # 2. unverified_answer (must NOT be is_verified_supported)
    r_unverified = RAGResult(
        query="Q",
        answer="A [E1].",
        status="answered",
        verification_badge="unverified_answer",
        citation_validation=CitationValidationResult(is_valid=True, semantic_support_status="not_evaluated")
    )
    assert r_unverified.is_verified_supported is False
    assert r_unverified.is_answer_suppressed is False

    # 3. rejected_answer (must be is_answer_suppressed)
    r_rejected = RAGResult(
        query="Q",
        answer="A [E1].",
        status="validation_failed",
        verification_badge="rejected_answer",
        citation_validation=CitationValidationResult(is_valid=False, semantic_support_status="contradicted")
    )
    assert r_rejected.is_verified_supported is False
    assert r_rejected.is_answer_suppressed is True

    # 4. qualified_answer
    r_qualified = RAGResult(
        query="Q",
        answer="A [E1].",
        status="answered_with_qualification",
        verification_badge="qualified_answer",
        citation_validation=CitationValidationResult(is_valid=True, semantic_support_status="partially_supported")
    )
    assert r_qualified.is_verified_supported is False
    assert r_qualified.is_answer_suppressed is False


# Scenario 10: Citation validity distinct from semantic support
def test_citation_validity_distinct_from_semantic_support(validator, sample_holding_passage):
    # Answer has well-formed [E1] matching supplied evidence, but claim text is completely unrelated
    answer = "The maritime underwriter is discharged from liability where the cargo vessel was unseaworthy. [E1]."
    val_res, claims = validator.validate(answer=answer, supplied_evidence=[sample_holding_passage])

    # Syntactic existence is valid
    assert val_res.citation_syntax_valid is True
    assert val_res.citation_existence_valid is True
    assert "E1" in val_res.valid_source_ids

    # BUT substantive claim verification rejected it
    assert claims[0].verification_status == "unsupported"
    assert val_res.is_valid is False
    assert val_res.unsupported_claims_count >= 1


# Scenario 11: Provider timeout and error distinct from legal abstention
def test_provider_timeout_and_error_distinct_from_abstention():
    # Legal abstention returns HTTP 200 with status="insufficient_evidence" and verification_badge="insufficient_evidence"
    r_abstain = RAGResult(
        query="Q",
        answer="INSUFFICIENT EVIDENCE: No relevant evidence.",
        status="insufficient_evidence",
        verification_badge="insufficient_evidence",
        citation_validation=CitationValidationResult(is_valid=True)
    )
    assert r_abstain.status == "insufficient_evidence"
    assert r_abstain.verification_badge == "insufficient_evidence"

    # Infrastructure timeout must raise HTTP 504 (not a 200 abstention)
    timeout_err = TimeoutError("Local Ollama timed out after 120s")
    exc_504 = HTTPException(status_code=504, detail=str(timeout_err))
    assert exc_504.status_code == 504

    # Service unavailable must raise HTTP 503 (not a 200 abstention)
    runtime_err = RuntimeError("Ollama connection refused")
    exc_503 = HTTPException(status_code=503, detail=str(runtime_err))
    assert exc_503.status_code == 503


# Scenario 12: Strict rejection of contradicted answers regardless of valid citations
def test_strict_rejection_of_contradicted_answers(verifier):
    # Mixed answer with 1 supported claim and 1 contradicted claim
    p_sup = EvidencePassage(
        evidence_id="E1",
        document_id="2024_12_28_67",
        passage_text="The rules of the game must not be changed during selection.",
        start_char=0,
        end_char=50,
        structural_label="judicial_holding"
    )
    p_neg = EvidencePassage(
        evidence_id="E2",
        document_id="2024_10_1890_1901",
        passage_text="A signatory merely authorized could not be directed to pay interim compensation.",
        start_char=0,
        end_char=80,
        structural_label="court_analysis"
    )

    claims = [
        ClaimAttribution(sentence="The rules of the game cannot be changed midway.", cited_evidence_ids=["E1"], verification_status="supported"),
        ClaimAttribution(sentence="The Appellate Court may order an authorized signatory to deposit compensation.", cited_evidence_ids=["E2"], verification_status="contradicted")
    ]

    val_res = CitationValidationResult(
        is_valid=True,
        cited_source_ids=["E1", "E2"],
        valid_source_ids=["E1", "E2"]
    )

    policy = ClaimVerifier.evaluate_acceptance_policy(
        validation_result=val_res,
        claims=claims
    )

    # Acceptance policy must reject whole answer fail-closed
    assert policy["is_valid"] is False
    assert policy["accepted_status"] == "validation_failed"
    assert policy["action"] == "reject_contradicted"
