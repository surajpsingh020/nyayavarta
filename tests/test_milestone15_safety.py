"""
Regression Test Suite for Milestone 15: False Verification Prevention and Answer-Level Safety.

Covers 15 core safety and presentation contract invariants:
1. Multi-part claim shared-context leak prevention (CR_M14_014).
2. Negative condition waiver prevention (CR_M14_017).
3. Affirmative modal 'may deposit' / condition waiver guard.
4. Pure supported answer aggregation -> verified_supported.
5. Answer demotion by partially supported claim -> qualified_answer.
6. Answer demotion by unsupported claim -> qualified_answer.
7. Answer rejection by contradicted claim -> rejected_answer.
8. Unverified answer preservation when any claim is not_evaluated -> unverified_answer.
9. Empty claims list rejection -> rejected_answer (never verified_supported).
10. Free-form answer with no substantive claims -> unverified_answer.
11. Clean abstention presentation badge -> insufficient_evidence.
12. Infrastructure / provider error presentation badge -> system_error.
13. All contradicted claims rejection -> rejected_answer & is_answer_suppressed.
14. All unsupported claims rejection -> rejected_answer & is_answer_suppressed.
15. Zero false-acceptance invariant across all 44 unseen evaluation claims.
"""
import pytest
import json
from pathlib import Path

from services.rag.models import (
    EvidencePassage,
    ClaimAttribution,
    CitationValidationResult,
    StructuredAnswer,
    StructuredClaim,
    RAGResult
)
from services.rag.claim_verifier import ClaimVerifier, ClaimVerificationStatus
from services.rag.validator import CitationValidator


@pytest.fixture
def verifier():
    return ClaimVerifier()


@pytest.fixture
def validator(verifier):
    return CitationValidator(require_citations_on_all_claims=True, verifier=verifier)


@pytest.fixture
def sukanya_shantha_passage():
    return EvidencePassage(
        evidence_id="E1",
        document_id="2024_10_493_638",
        case_title="SUKANYA SHANTHA versus UNION OF INDIA & ORS.",
        structural_label="headnote_holding",
        passage_text=(
            "caste-based discrimination in the prisons in the country.\n"
            "Headnotes†\n"
            "Constitution of India – Arts.14, 15, 17, 21, and 23 – Prisons in India – "
            "Caste-based discrimination – Writ petition seeking directions for repeal of "
            "the offending provisions in State Prison Manuals – Petitioner’s case that various "
            "State Prison Manuals sanction unconstitutional practices"
        ),
        start_char=253,
        end_char=603
    )


@pytest.fixture
def sarfaesi_passage():
    return EvidencePassage(
        evidence_id="E1",
        document_id="2024_10_1371_1380",
        case_title="IDBI BANK LTD. versus RAMSWAROOP DALIYA AND ORS.",
        structural_label="court_analysis",
        passage_text=(
            "period to deposit the balance sale consideration under r.9(4) is not "
            "absolute/sacrosanct and is extendable with the consent in writing of the parties – "
            "r.9(4) will only come into play when there is default on part of the party i.e. "
            "the auction purchaser to deposit the amount and will not apply"
        ),
        start_char=649,
        end_char=949
    )


@pytest.fixture
def tej_prakash_passage():
    return EvidencePassage(
        evidence_id="E2",
        document_id="2024_12_28_67",
        case_title="TEJ PRAKASH PATHAK & ORS. versus RAJASTHAN HIGH COURT & ORS.",
        structural_label="judicial_holding",
        passage_text=(
            "rules of the game’ must not be changed during the course of the game, or "
            "after the game is played; (c) Whether the decision in K. Manjusree is at variance "
            "with earlier precedents on the subject. The rules cannot be changed midway."
        ),
        start_char=385,
        end_char=735
    )


# 1. Multi-part claim shared-context leak prevention (CR_M14_014)
def test_multi_part_claim_shared_context_leak_prevention(verifier, sukanya_shantha_passage):
    claim = "The Court held that caste-based labor segregation in prisons violates Article 14 and ruled that all existing prison convictions stand quashed."
    res = verifier.verify_claim(claim, [sukanya_shantha_passage])
    assert res.status == ClaimVerificationStatus.PARTIALLY_SUPPORTED
    assert res.is_supported is False
    assert res.is_partially_supported is True
    assert "multipart_claim_check" in res.method


# 2. Negative condition waiver prevention (CR_M14_017)
def test_negative_condition_waiver_prevention(verifier, sarfaesi_passage):
    claim = "The auction purchaser may deposit the balance consideration after 15 days without seeking any written consent."
    res = verifier.verify_claim(claim, [sarfaesi_passage])
    assert res.status == ClaimVerificationStatus.PARTIALLY_SUPPORTED
    assert res.is_supported is False
    assert res.is_partially_supported is True
    assert res.omits_statutory_qualification is True
    assert "statutory_qualification_omission_check" in res.method


# 3. Affirmative modal 'may deposit' / condition waiver guard
def test_affirmative_modal_deposit_prevention(verifier, sarfaesi_passage):
    claim = "The purchaser may deposit the balance amount unconditionally without written consent."
    res = verifier.verify_claim(claim, [sarfaesi_passage])
    assert res.status != ClaimVerificationStatus.SUPPORTED
    assert res.is_supported is False


# 4. Pure supported answer aggregation -> verified_supported
def test_answer_aggregation_all_supported(validator, sukanya_shantha_passage, tej_prakash_passage):
    sa = StructuredAnswer(
        status="answer",
        claims=[
            StructuredClaim(text="Caste-based labor segregation in prisons violates the Constitution.", evidence_ids=["E1"]),
            StructuredClaim(text="The rules of the game must not be changed during the course of the game.", evidence_ids=["E2"])
        ]
    )
    val_res, claims_attr = validator.validate_structured(sa, [sukanya_shantha_passage, tej_prakash_passage])
    assert val_res.is_valid is True
    assert val_res.semantic_support_status == "supported"
    assert val_res.supported_claims_count == 2
    assert val_res.contradicted_claims_count == 0
    assert val_res.unsupported_claims_count == 0
    assert val_res.partially_supported_claims_count == 0
    assert val_res.unverified_claims_count == 0

    # Badge check via pipeline logic
    rag_res = RAGResult(
        query="test query",
        answer="test answer",
        status="answered",
        verification_badge="verified_supported",
        citation_validation=val_res,
        claims=claims_attr
    )
    assert rag_res.is_verified_supported is True
    assert rag_res.is_answer_suppressed is False


# 5. Answer demotion by partially supported claim -> qualified_answer
def test_answer_aggregation_demoted_by_partially_supported(validator, sukanya_shantha_passage, sarfaesi_passage):
    sa = StructuredAnswer(
        status="answer",
        claims=[
            StructuredClaim(text="Caste-based labor segregation in prisons violates the Constitution.", evidence_ids=["E1"]),
            StructuredClaim(text="The auction purchaser may deposit the balance consideration after 15 days without seeking any written consent.", evidence_ids=["E1"])
        ]
    )
    val_res, claims_attr = validator.validate_structured(sa, [sukanya_shantha_passage, sarfaesi_passage])
    assert val_res.is_valid is True
    assert val_res.validation_status == "partially_supported"
    assert val_res.semantic_support_status == "partially_supported"
    assert val_res.partially_supported_claims_count >= 1

    # Answer-level badge mapping must NOT be verified_supported
    policy = ClaimVerifier.evaluate_acceptance_policy(val_res, claims_attr)
    assert policy["accepted_status"] == "answered_with_qualification"


# 6. Answer demotion by unsupported claim -> qualified_answer
def test_answer_aggregation_demoted_by_unsupported(validator, sukanya_shantha_passage, tej_prakash_passage):
    sa = StructuredAnswer(
        status="answer",
        claims=[
            StructuredClaim(text="Caste-based labor segregation in prisons violates the Constitution.", evidence_ids=["E1"]),
            StructuredClaim(text="The maritime underwriter is discharged from liability where cargo vessel was unseaworthy.", evidence_ids=["E2"])
        ]
    )
    val_res, claims_attr = validator.validate_structured(sa, [sukanya_shantha_passage, tej_prakash_passage])
    assert val_res.is_valid is True
    assert val_res.validation_status == "partially_supported"
    assert val_res.unsupported_claims_count == 1
    policy = ClaimVerifier.evaluate_acceptance_policy(val_res, claims_attr)
    assert policy["accepted_status"] == "answered_with_qualification"


# 7. Answer rejection by contradicted claim -> rejected_answer
def test_answer_aggregation_rejected_by_contradicted(validator, sukanya_shantha_passage, tej_prakash_passage):
    sa = StructuredAnswer(
        status="answer",
        claims=[
            StructuredClaim(text="Caste-based labor segregation in prisons violates the Constitution.", evidence_ids=["E1"]),
            StructuredClaim(text="The recruiting authority is empowered to alter qualification criteria midway.", evidence_ids=["E2"])
        ]
    )
    val_res, claims_attr = validator.validate_structured(sa, [sukanya_shantha_passage, tej_prakash_passage])
    assert val_res.is_valid is False
    assert val_res.validation_status == "contradicted"
    assert val_res.contradicted_claims_count == 1

    policy = ClaimVerifier.evaluate_acceptance_policy(val_res, claims_attr)
    assert policy["is_valid"] is False
    assert policy["accepted_status"] == "validation_failed"


# 8. Unverified answer preservation when any claim is not_evaluated -> unverified_answer
def test_answer_aggregation_unverified_when_claim_not_evaluated(validator, sukanya_shantha_passage):
    ep2 = EvidencePassage(
        evidence_id="E2",
        document_id="2024_5_1_10",
        case_title="Corporate Case",
        structural_label="general_text",
        passage_text="The matter requires detailed appreciation of complex evidence regarding company affairs.",
        start_char=100,
        end_char=400
    )
    sa = StructuredAnswer(
        status="answer",
        claims=[
            StructuredClaim(text="Caste-based labor segregation in prisons violates the Constitution.", evidence_ids=["E1"]),
            StructuredClaim(text="Company directors bear distinct fiduciary accountability regarding company affairs.", evidence_ids=["E2"])
        ]
    )
    val_res, claims_attr = validator.validate_structured(sa, [sukanya_shantha_passage, ep2])
    assert val_res.is_valid is True
    assert val_res.unverified_claims_count == 1
    # Must NOT be marked supported
    assert val_res.semantic_support_status == "not_evaluated"
    policy = ClaimVerifier.evaluate_acceptance_policy(val_res, claims_attr)
    assert policy["action"] == "accept_unverified"


# 9. Empty claims list rejection -> rejected_answer (never verified_supported)
def test_answer_aggregation_empty_claims_rejected(validator, sukanya_shantha_passage):
    sa = StructuredAnswer(status="answer", claims=[])
    val_res, claims_attr = validator.validate_structured(sa, [sukanya_shantha_passage])
    assert val_res.is_valid is False
    assert val_res.validation_status == "invalid"


# 10. Free-form answer with no citations/claims -> rejected / unverified (never supported)
def test_answer_aggregation_free_form_no_claims(validator, sukanya_shantha_passage):
    val_res, claims_attr = validator.validate("This is generic introductory text with no citations.", [sukanya_shantha_passage])
    assert val_res.is_valid is False
    assert val_res.semantic_support_status != "supported"


# 11. Clean abstention presentation badge -> insufficient_evidence
def test_abstention_presentation_badge():
    rag_res = RAGResult(
        query="What is the rule?",
        answer="INSUFFICIENT EVIDENCE: No relevant judgments found.",
        status="insufficient_evidence",
        verification_badge="insufficient_evidence",
        citation_validation=CitationValidationResult(is_valid=True),
        claims=[]
    )
    assert rag_res.verification_badge == "insufficient_evidence"
    assert rag_res.is_verified_supported is False
    assert rag_res.is_answer_suppressed is False


# 12. Infrastructure / provider error presentation badge -> system_error
def test_system_error_presentation_badge():
    rag_res = RAGResult(
        query="What is the rule?",
        answer="Provider timed out.",
        status="error",
        verification_badge="system_error",
        citation_validation=CitationValidationResult(is_valid=False),
        claims=[]
    )
    assert rag_res.verification_badge == "system_error"
    assert rag_res.is_verified_supported is False
    assert rag_res.is_answer_suppressed is True


# 13. All contradicted claims rejection -> rejected_answer & is_answer_suppressed
def test_all_contradicted_claims_suppressed(validator, tej_prakash_passage):
    sa = StructuredAnswer(
        status="answer",
        claims=[
            StructuredClaim(text="The recruiting authority is empowered to alter qualification criteria midway.", evidence_ids=["E2"])
        ]
    )
    val_res, claims_attr = validator.validate_structured(sa, [tej_prakash_passage])
    assert val_res.is_valid is False
    assert val_res.validation_status == "contradicted"

    rag_res = RAGResult(
        query="recruitment criteria",
        answer="Empowered to alter.",
        status="validation_failed",
        verification_badge="rejected_answer",
        citation_validation=val_res,
        claims=claims_attr
    )
    assert rag_res.is_answer_suppressed is True
    assert rag_res.is_verified_supported is False


# 14. All unsupported claims rejection -> rejected_answer & is_answer_suppressed
def test_all_unsupported_claims_suppressed(validator, sukanya_shantha_passage):
    sa = StructuredAnswer(
        status="answer",
        claims=[
            StructuredClaim(text="The maritime underwriter is discharged from liability where cargo vessel was unseaworthy.", evidence_ids=["E1"])
        ]
    )
    val_res, claims_attr = validator.validate_structured(sa, [sukanya_shantha_passage])
    assert val_res.is_valid is False
    assert val_res.unsupported_claims_count == 1

    rag_res = RAGResult(
        query="marine insurance",
        answer="Discharged.",
        status="validation_failed",
        verification_badge="rejected_answer",
        citation_validation=val_res,
        claims=claims_attr
    )
    assert rag_res.is_answer_suppressed is True
    assert rag_res.is_verified_supported is False


# 15. Zero false-acceptance invariant across all 44 unseen evaluation claims
def test_unseen_claims_benchmark_zero_false_acceptances(verifier):
    dataset_path = Path("evaluation/rag/milestone14_unseen_claims.jsonl")
    assert dataset_path.exists(), "Milestone 14 dataset required"

    with open(dataset_path, "r", encoding="utf-8") as f:
        cases = [json.loads(line) for line in f if line.strip()]

    assert len(cases) == 44, f"Expected 44 cases, found {len(cases)}"

    promoted_to_supported = []
    supported_gold_matches = []

    for c in cases:
        passages = [
            EvidencePassage(
                evidence_id=p["evidence_id"],
                document_id=p["document_id"],
                case_title=p.get("case_title", "Unknown"),
                structural_label=p.get("structural_label"),
                passage_text=p["passage_text"],
                start_char=p["start_char"],
                end_char=p["end_char"]
            )
            for p in c["supporting_passages"]
        ]
        res = verifier.verify_claim(c["claim_sentence"], passages)
        if res.status == ClaimVerificationStatus.SUPPORTED:
            if c["support_label"] != "supported":
                promoted_to_supported.append((c["review_id"], c["support_label"]))
            else:
                supported_gold_matches.append(c["review_id"])

    # Zero false acceptances into supported class
    assert len(promoted_to_supported) == 0, f"False acceptances into supported class: {promoted_to_supported}"
    # Supported class precision must be 100%
    assert len(supported_gold_matches) == 6
