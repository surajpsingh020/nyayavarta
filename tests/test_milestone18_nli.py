"""
Milestone 18: NLI Verification Feasibility and Shadow Safety Tests.

Validates:
1. Correct premise-hypothesis direction.
2. Negation and polarity reversals.
3. Permission versus prohibition.
4. A partially supported multi-part claim.
5. Missing statutory conditions.
6. Party submissions versus judicial holdings.
7. Quoted precedent versus current-court holdings.
8. Neutral NLI outputs remaining uncertain.
9. Invalid or empty model outputs failing safely.
10. CPU-only execution and resource limits.
11. Preservation of all existing answer-level badge rules.
12. The six Milestone 17 partial-to-supported regression cases.
"""
import os
import json
from pathlib import Path
import pytest
import numpy as np

from services.rag.models import (
    EvidencePassage,
    ClaimAttribution,
    CitationValidationResult,
    StructuredAnswer,
    StructuredClaim
)
from services.rag.claim_verifier import ClaimVerifier, ClaimVerificationStatus
from services.rag.validator import CitationValidator
from services.rag.nli_verifier import LocalNLIVerifier, NLIClassificationResult


@pytest.fixture(scope="module")
def nli_verifier():
    """Module-level fixture to load LocalNLIVerifier on CPU once for test execution."""
    verifier = LocalNLIVerifier()
    if not verifier.is_available:
        pytest.skip("Local NLI ONNX model is not available in the environment.")
    return verifier


def test_1_premise_hypothesis_direction(nli_verifier):
    """Test 1: Verify correct directional entailment (Premise -> Hypothesis)."""
    premise = "Held: s.118 sub-clause (e) provides a clear presumption regarding indorsements made on the negotiable instrument being in order in which they appear thereupon."
    hypothesis = "Under Section 118(e) there is a legal presumption that indorsements on a negotiable instrument were made in the order in which they appear."
    
    # Forward: Premise entails Hypothesis
    res_fwd = nli_verifier.predict(premise=premise, hypothesis=hypothesis)
    assert res_fwd.label == "entailment"
    assert res_fwd.probabilities["entailment"] > 0.90

    # Reversed: General premise cannot entail specific factual holding
    general_premise = "The Supreme Court decides appeals under Article 136 of the Constitution of India."
    specific_hyp = "The appellant's conviction under Section 302 IPC was quashed in this specific appeal."
    res_rev = nli_verifier.predict(premise=general_premise, hypothesis=specific_hyp)
    assert res_rev.label != "entailment"
    assert res_rev.label in ["neutral", "contradiction"]


def test_2_negation_and_polarity_reversals(nli_verifier):
    """Test 2: Negation and polarity reversals must be flagged as contradiction."""
    premise = "Held: Section 18 of the SC/ST Act does not impose an absolute bar on granting anticipatory bail."
    hypothesis = "Section 18 of the SC/ST Act creates an absolute bar precluding any grant of anticipatory bail."

    res = nli_verifier.predict(premise=premise, hypothesis=hypothesis)
    assert res.label == "contradiction"
    assert res.probabilities["contradiction"] > 0.85


def test_3_permission_versus_prohibition(nli_verifier):
    """Test 3: Permission versus prohibition assertions must be detected."""
    premise = "Held: A daughter is entitled to equal coparcenary rights in Hindu joint family property."
    hypothesis = "A daughter cannot claim equal coparcenary rights in joint family property."

    res = nli_verifier.predict(premise=premise, hypothesis=hypothesis)
    assert res.label == "contradiction"
    assert res.probabilities["contradiction"] > 0.80


def test_4_partially_supported_multipart_claim(nli_verifier):
    """Test 4: Multi-part claim where one part is ungrounded must not receive entailment."""
    premise = "Held: Conviction under Section 306 IPC requires proof of active instigation proximate to the suicide."
    # Second clause is ungrounded / contradicted
    hypothesis = "Conviction under Section 306 IPC requires instigation and may be based solely on domestic discord."

    res = nli_verifier.predict(premise=premise, hypothesis=hypothesis)
    assert res.label != "entailment"
    assert res.probabilities["entailment"] < 0.50


def test_5_missing_statutory_conditions(nli_verifier):
    """Test 5: Claims omitting mandatory statutory conditions must not be verified as entailed."""
    premise = "Held: The period to deposit balance sale consideration is extendable only with the written consent of all parties."
    hypothesis = "The period to deposit balance sale consideration is extendable without any written consent."

    res = nli_verifier.predict(premise=premise, hypothesis=hypothesis)
    assert res.label == "contradiction"
    assert res.probabilities["contradiction"] > 0.80


def test_6_party_submissions_versus_judicial_holdings(nli_verifier):
    """Test 6: Party submissions must not be verified as judicial holdings."""
    ep_submission = EvidencePassage(
        evidence_id="E1",
        document_id="2024_test_sub",
        case_title="Test v. State",
        passage_text="Learned counsel for the appellant submitted that the prosecution failed to prove motive.",
        start_char=100,
        end_char=200,
        structural_label="party_submissions"
    )
    claim = ClaimAttribution(
        sentence="The prosecution failed to prove motive in this case.",
        cited_evidence_ids=["E1"]
    )

    det_verifier = ClaimVerifier(shadow_verifier=nli_verifier, enable_shadow_nli=True)
    det_verifier.verify_claims([claim], supplied_evidence=[ep_submission])

    # Must be partially supported or flagged due to submission reliance
    assert claim.verification_status == ClaimVerificationStatus.PARTIALLY_SUPPORTED.value
    assert claim.verification_method == "structural_party_submission_context"


def test_7_quoted_precedent_versus_current_court_holding(nli_verifier):
    """Test 7: Quoted precedent distinguished or rejected by the court."""
    premise = (
        "Held: While in the earlier decision in State of Punjab the Court took a contrary view, "
        "that decision is distinguishable and we hold that no compensation can be claimed."
    )
    hypothesis = "The Supreme Court awarded full compensation following the earlier decision in State of Punjab."

    res = nli_verifier.predict(premise=premise, hypothesis=hypothesis)
    assert res.label == "contradiction"
    assert res.probabilities["contradiction"] > 0.70


def test_8_neutral_nli_outputs_remain_uncertain(nli_verifier):
    """Test 8: Neutral NLI outputs must map to uncertainty (not_evaluated), never to supported."""
    premise = "Held: The appeal is allowed and conviction under Section 302 IPC is set aside."
    hypothesis = "The Supreme Court consists of the Chief Justice of India and up to 33 other judges."

    res = nli_verifier.predict(premise=premise, hypothesis=hypothesis)
    assert res.label == "neutral"
    assert res.is_uncertain is True

    verdict = nli_verifier.evaluate_shadow(
        claim=hypothesis,
        passage=premise,
        deterministic_status="supported"  # hypothetical loose heuristic match
    )
    # Must be demoted to not_evaluated!
    assert verdict.shadow_recommended_status == "not_evaluated"


def test_9_invalid_or_empty_model_outputs_fail_safely(nli_verifier):
    """Test 9: Invalid or empty inputs must fail safely without raising exceptions."""
    # Empty premise
    r1 = nli_verifier.predict(premise="", hypothesis="Valid hypothesis text.")
    assert r1.label == "neutral"
    assert r1.is_uncertain is True
    assert r1.confidence == 0.0

    # Empty hypothesis
    r2 = nli_verifier.predict(premise="Valid premise text.", hypothesis="")
    assert r2.label == "neutral"
    assert r2.is_uncertain is True

    # None inputs
    r3 = nli_verifier.predict(premise=None, hypothesis=None)
    assert r3.label == "neutral"
    assert r3.is_uncertain is True


def test_10_cpu_only_execution_and_resource_limits(nli_verifier):
    """Test 10: Model execution must run on CPU and satisfy latency limits."""
    premise = "Held: The second appeal cannot be heard without formulating substantial questions of law."
    hypothesis = "Formulation of substantial questions of law is mandatory for hearing a second appeal."

    res = nli_verifier.predict(premise=premise, hypothesis=hypothesis)
    assert res.latency_ms > 0.0
    assert res.latency_ms < 1000.0  # Must be sub-second on CPU


def test_11_preservation_of_all_existing_answer_level_badge_rules(nli_verifier):
    """Test 11: Production badge rules remain fail-closed regardless of shadow NLI."""
    ep = EvidencePassage(
        evidence_id="E1",
        document_id="2024_test_doc",
        case_title="A v. B",
        passage_text="Held: The appeal is dismissed.",
        start_char=0,
        end_char=50,
        structural_label="headnote_holding"
    )
    # Create structured answer with one supported claim and one unverified claim
    structured_ans = StructuredAnswer(
        status="answer",
        claims=[
            StructuredClaim(text="The appeal was dismissed.", evidence_ids=["E1"]),
            StructuredClaim(text="The court awarded punitive damages of ten crore rupees.", evidence_ids=["E1"])
        ]
    )

    validator = CitationValidator()
    result, claims = validator.validate_structured(structured_ans, [ep])

    # The second claim is not directly supported; overall status cannot be verified_supported
    assert result.semantic_support_status != "supported"
    assert result.validation_status in ["valid", "partially_supported", "invalid"]


def test_12_six_m17_regression_cases_eliminated_in_shadow_mode(nli_verifier):
    """Test 12: In shadow mode, all 6 false acceptances from M17 are safely averted."""
    m17_path = Path("evaluation/rag/milestone17_unseen_claims.jsonl")
    assert m17_path.exists(), "milestone17_unseen_claims.jsonl must exist"

    with open(m17_path, "r", encoding="utf-8") as f:
        cases = {json.loads(line)["case_id"]: json.loads(line) for line in f if line.strip()}

    target_case_ids = [
        "M17_UNSEEN_009",
        "M17_UNSEEN_011",
        "M17_UNSEEN_016",
        "M17_UNSEEN_024",
        "M17_UNSEEN_026",
        "M17_UNSEEN_028"
    ]

    for cid in target_case_ids:
        c_data = cases[cid]
        p_text = c_data["supporting_passages"][0]["passage_text"]
        claim_text = c_data["claim_sentence"]

        verdict = nli_verifier.evaluate_shadow(
            claim=claim_text,
            passage=p_text,
            deterministic_status="supported"  # deterministic heuristic had erroneously predicted supported
        )

        # In shadow mode, NLI must reject false support (demoting to either not_evaluated or contradicted)
        assert verdict.shadow_recommended_status != "supported", (
            f"Case {cid} was not demoted in shadow mode: NLI predicted {verdict.nli_label} "
            f"with confidence {verdict.nli_confidence}"
        )
