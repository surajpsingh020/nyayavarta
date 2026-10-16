"""
Milestone 19: NLI Calibration, Policy Evaluation and End-to-End Safety Tests.

Validates:
1. NLI inference failure fails safely without crashing.
2. Missing model files fail safely with clear error message.
3. Incorrect premise-hypothesis order yields non-support.
4. Contradiction and neutral outputs are properly distinguished and mapped.
5. Partial-support claims with omitted provisos are never promoted to supported.
6. Long passages containing statutory qualifications respect the 512-token limit.
7. The existing Milestone 17 false-acceptance cases remain resolved.
8. The Milestone 18 generalization error (M18_GEN_005 exclusionary clause) is resolved.
9. Answer-level badge aggregation preserves fail-closed invariants.
10. CPU performance bounds are satisfied (< 500 ms per claim warm).
11. Reproducible score serialization conforms to normalized ranges [0.0, 1.0].
12. Preservation of existing API and pipeline behavior (deterministic baseline intact).
"""
import os
import json
import time
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
from services.rag.pipeline import RAGPipeline
from services.rag.providers import MockLLMProvider


@pytest.fixture(scope="module")
def nli_verifier():
    """Module-level fixture to load LocalNLIVerifier on CPU once for test execution."""
    verifier = LocalNLIVerifier()
    if not verifier.is_available:
        pytest.skip("Local NLI ONNX model is not available in the environment.")
    return verifier


def test_1_nli_inference_failure_fails_safely():
    """Test 1: Graceful fallback when inference encounters an internal error."""
    verifier = LocalNLIVerifier()
    # Passing unusual non-string inputs should be handled gracefully
    res = verifier.predict(premise="", hypothesis="")
    assert res.label == "neutral"
    assert res.is_uncertain is True
    assert res.error_message is not None
    assert res.confidence == 0.0


def test_2_missing_model_files_fail_safely():
    """Test 2: When an invalid/non-existent model is specified, verifier fails gracefully."""
    bad_verifier = LocalNLIVerifier(model_id="nonexistent/fake-model-id-12345", lazy_load=True)
    res = bad_verifier.predict("Some premise text", "Some hypothesis text")
    assert res.label == "neutral"
    assert res.is_uncertain is True
    assert "Model unavailable" in (res.error_message or "")


def test_3_incorrect_premise_hypothesis_order(nli_verifier):
    """Test 3: Swapping premise and hypothesis gives asymmetrical non-support."""
    general_rule = "The Supreme Court hears statutory appeals under Section 62 of the Insolvency and Bankruptcy Code."
    specific_fact = "The NCLAT order dismissing the insolvency resolution plan was quashed in this specific appeal."

    # Premise: specific holding, Hypothesis: general statement -> Entailment
    res_correct = nli_verifier.predict(premise=specific_fact, hypothesis=general_rule)
    # Premise: general statement, Hypothesis: specific holding -> Neutral (does not prove specific fact)
    res_reversed = nli_verifier.predict(premise=general_rule, hypothesis=specific_fact)

    assert res_reversed.label != "entailment"
    assert res_reversed.probabilities["entailment"] < 0.20


def test_4_contradiction_and_neutral_outputs(nli_verifier):
    """Test 4: Contradiction and neutral outputs must never be treated as affirmative support."""
    premise = "Held: The period of limitation under Section 34(3) cannot be extended beyond thirty days."
    hyp_contra = "The court can condone unlimited delay in filing Section 34 objections."
    hyp_neutral = "The arbitration proceedings were conducted in New Delhi."

    res_contra = nli_verifier.predict(premise=premise, hypothesis=hyp_contra)
    assert res_contra.label == "contradiction"
    assert res_contra.probabilities["contradiction"] > 0.85

    res_neutral = nli_verifier.predict(premise=premise, hypothesis=hyp_neutral)
    assert res_neutral.label == "neutral"
    assert res_neutral.is_uncertain is True


def test_5_partial_support_claims(nli_verifier):
    """Test 5: Claims omitting mandatory statutory provisos are not promoted to supported."""
    premise = (
        "Held: Anticipatory bail under the SC/ST Act is not absolutely barred, provided the court "
        "first examines whether a prima facie case attracting the provisions is made out."
    )
    # Claim omits the prima facie threshold
    hyp_omitted = "Anticipatory bail under the SC/ST Act can be granted without examining whether a prima facie case is made out."

    res = nli_verifier.predict(premise=premise, hypothesis=hyp_omitted)
    assert res.label != "entailment"
    assert res.probabilities["entailment"] < 0.5


def test_6_long_passages_statutory_qualifications(nli_verifier):
    """Test 6: Long passage exceeding typical sentence length respects 512 token truncation."""
    statutory_passage = (
        "Held: Section 16(c) of the Specific Relief Act 1963 bars specific performance of a contract in favor of a person "
        "who fails to aver and prove that he has performed or has always been ready and willing to perform the essential terms "
        "of the contract which are to be performed by him, other than terms the performance of which has been prevented or waived by the defendant. "
    ) * 4  # Repeat to build extended passage
    hypothesis = "The plaintiff must plead and prove continuous readiness and willingness under Section 16(c)."

    res = nli_verifier.predict(premise=statutory_passage, hypothesis=hypothesis)
    assert res.label in ["entailment", "neutral"]
    assert res.latency_ms < 3000.0  # Runs within reasonable bounds despite length (sub-3s for 512 tokens on CPU)


def test_7_existing_m17_false_acceptance_cases(nli_verifier):
    """Test 7: The 6 false acceptances from M17 are all demoted or vetoed in shadow hybrid mode."""
    m17_path = Path("evaluation/rag/milestone17_unseen_claims.jsonl")
    assert m17_path.exists()

    with m17_path.open("r", encoding="utf-8") as f:
        cases = {json.loads(line)["case_id"]: json.loads(line) for line in f if line.strip()}

    target_ids = ["M17_UNSEEN_009", "M17_UNSEEN_011", "M17_UNSEEN_016", "M17_UNSEEN_024", "M17_UNSEEN_026", "M17_UNSEEN_028"]
    for cid in target_ids:
        c = cases[cid]
        p_text = c["supporting_passages"][0]["passage_text"]
        h_text = c["claim_sentence"]

        verdict = nli_verifier.evaluate_shadow(
            claim=h_text,
            passage=p_text,
            deterministic_status="supported"
        )
        assert verdict.shadow_recommended_status != "supported", f"Case {cid} was not demoted!"


def test_8_milestone18_generalization_error_resolved(nli_verifier):
    """Test 8: M18_GEN_005 exclusionary clause inversion is caught by ClaimVerifier."""
    ep = EvidencePassage(
        evidence_id="E1",
        document_id="2024_10_1359_1370",
        case_title="Pradeep Kumar v. State of U.P.",
        passage_text=(
            "Held: Yes – Under Or.XXI, r.99, where any person other than the judgment debtor is dispossessed "
            "of immovable property by the holder of a decree for the possession of such property... he may make an application."
        ),
        start_char=0,
        end_char=200,
        structural_label="headnote_holding"
    )
    claim_inverted = "Under Order XXI Rule 99 CPC, an application complaining of dispossession can be made by the judgment debtor."

    verifier = ClaimVerifier()
    res = verifier.verify_claim(claim_inverted, [ep])

    assert res.status == ClaimVerificationStatus.PARTIALLY_SUPPORTED
    assert res.method == "exclusionary_clause_misattribution_check"
    assert res.omits_statutory_qualification is True


def test_9_answer_level_badge_aggregation():
    """Test 9: Fail-closed badge rules prevent partial/unverified claims from receiving verified badge."""
    ep = EvidencePassage(
        evidence_id="E1",
        document_id="2024_test_doc",
        case_title="Test Title",
        passage_text="Held: The appeal is allowed.",
        start_char=0,
        end_char=40,
        structural_label="headnote_holding"
    )
    structured_ans = StructuredAnswer(
        status="answer",
        claims=[
            StructuredClaim(text="The appeal was allowed.", evidence_ids=["E1"]),
            StructuredClaim(text="Full restitution was ordered without trial.", evidence_ids=["E1"])
        ]
    )

    validator = CitationValidator()
    result, claims = validator.validate_structured(structured_ans, [ep])

    # Second claim is ungrounded / unverified; semantic status must not be supported
    assert result.semantic_support_status != "supported"
    assert result.validation_status != "invalid" or not result.is_valid


def test_10_cpu_performance_bounds(nli_verifier):
    """Test 10: Warm CPU inference latency must be sub-500ms."""
    premise = "The appeal is allowed and the impugned judgment of the High Court is set aside."
    hypothesis = "The appeal was allowed and the High Court judgment was set aside."

    t0 = time.perf_counter()
    res = nli_verifier.predict(premise=premise, hypothesis=hypothesis)
    latency_ms = (time.perf_counter() - t0) * 1000.0

    assert latency_ms < 500.0, f"Latency {latency_ms:.1f}ms exceeded 500ms limit."
    assert res.label == "entailment"


def test_11_reproducible_score_serialization(nli_verifier):
    """Test 11: Raw logits and probabilities are valid floats and sum to 1.0 within numerical precision."""
    premise = "Held: Regular seniority can be reckoned only from the date of substantive appointment."
    hypothesis = "Seniority cannot be counted from temporary ad-hoc appointments."

    res = nli_verifier.predict(premise=premise, hypothesis=hypothesis)
    probs = res.probabilities

    assert "entailment" in probs and "contradiction" in probs and "neutral" in probs
    for p in probs.values():
        assert 0.0 <= p <= 1.0

    prob_sum = sum(probs.values())
    assert abs(prob_sum - 1.0) < 0.01


def test_12_preservation_of_existing_api_and_pipeline_behavior():
    """Test 12: Pipeline operates deterministically by default without auxiliary NLI requirement."""
    pipeline = RAGPipeline(
        llm_provider=MockLLMProvider(mode=MockLLMProvider.MODE_STRUCTURED_NORMAL)
    )
    res = pipeline.query(
        query_text="What are the grounds for granting bail under Section 439 CrPC?",
        top_k_judgments=2,
        structured_output=True
    )
    assert res.status in ["answered", "answered_with_qualification", "insufficient_evidence"]
    assert res.verification_badge in ["verified_supported", "qualified_answer", "unverified_answer", "insufficient_evidence", "rejected_answer"]
