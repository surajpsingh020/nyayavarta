"""Milestone 17 Regression Test Suite: Verifier Error Analysis & Unseen Benchmark.

Tests:
1. Root-cause resolution of Milestone 16 false acceptances (M16_UNSEEN_007, 008, 020).
2. Preservation of Milestone 16 true supported claims (M16_UNSEEN_001 to 005).
3. Milestone 17 unseen claims dataset integrity (>= 30 distinct unstudied judgments).
4. Error analysis and frozen baseline provenance artifact integrity.
5. Verification results artifact integrity and explicit PENDING_EXTERNAL_REVIEW declaration.
6. Safe answer presentation contract enforcement under tightened verifier.
"""

import json
import pytest
from pathlib import Path

from services.rag.models import (
    EvidencePassage,
    StructuredAnswer,
    StructuredClaim,
)
from services.rag.claim_verifier import (
    ClaimVerifier,
    ClaimVerificationStatus,
)
from services.rag.validator import CitationValidator


@pytest.fixture
def verifier():
    return ClaimVerifier()


@pytest.fixture
def validator():
    return CitationValidator()


@pytest.fixture
def m17_unseen_path():
    return Path("evaluation/rag/milestone17_unseen_claims.jsonl")


@pytest.fixture
def m17_results_path():
    return Path("evaluation/rag/milestone17_verification_results.json")


@pytest.fixture
def m17_error_analysis_path():
    return Path("evaluation/rag/milestone17_error_analysis.jsonl")


# ---------------------------------------------------------------------------
# Test 1: Root-Cause Resolution of M16 False Acceptances
# ---------------------------------------------------------------------------
def test_m16_false_acceptances_resolved(verifier):
    """Verify that M16_UNSEEN_007, 008, and 020 are never accepted as supported."""
    # Case 1: M16_UNSEEN_007 (Rohini Sudarshan Gangurde - S. 306 IPC without proof of instigation)
    p_007 = EvidencePassage(
        evidence_id="E1",
        document_id="2024_7_1031_1039",
        case_title="ROHINI SUDARSHAN GANGURDE versus THE STATE OF MAHARASHTRA & ANR.",
        passage_text=(
            "Held: S.306 IPC must be read with s.107 IPC that explains the meaning of 'abetment' – "
            "s.107 IPC lays down three criteria for abetment: there must be either an instigation, or "
            "an engagement or intentional aid. In the absence of positive action proximate to time of death, no conviction."
        ),
        start_char=1587,
        end_char=1887,
        structural_label="headnote_holding",
    )
    res_007 = verifier.verify_claim(
        "A person may be convicted under Section 306 IPC for abetment of suicide without proof of active instigation if harassment is established.",
        [p_007]
    )
    assert res_007.status != ClaimVerificationStatus.SUPPORTED
    assert res_007.status == ClaimVerificationStatus.PARTIALLY_SUPPORTED
    assert res_007.omits_statutory_qualification is True

    # Case 2: M16_UNSEEN_008 (UOI v. Barakathullah - UAPA bail without detailed analysis)
    p_008 = EvidencePassage(
        evidence_id="E1",
        document_id="2024_5_1011_1037",
        case_title="UNION OF INDIA versus BARAKATHULLAH ETC.",
        passage_text=(
            "Held: It is quite well settled position of law that the chargesheet need not contain detailed "
            "analysis of the evidence – It is for the concerned court considering the application for bail to "
            "assess whether a prima facie case exists under Section 43D(5)..."
        ),
        start_char=1639,
        end_char=1939,
        structural_label="headnote_holding",
    )
    res_008 = verifier.verify_claim(
        "The court considering bail under UAPA may assess whether the accusations are prima facie true without detailed analysis.",
        [p_008]
    )
    assert res_008.status != ClaimVerificationStatus.SUPPORTED
    assert res_008.status == ClaimVerificationStatus.PARTIALLY_SUPPORTED

    # Case 3: M16_UNSEEN_020 (Ramachandran v. Vijayan - Female coparcenary partition exclusion)
    p_020 = EvidencePassage(
        evidence_id="E1",
        document_id="2024_11_1013_1041",
        case_title="RAMACHANDRAN & ORS. versus VIJAYAN & ORS.",
        passage_text=(
            "Held: The minority opinion of the Full Bench of Kerala High Court in Mary Cheriyan case correctly holds "
            "that if at the time of partition the female is single, she continues to hold the property as her own... "
            "Claim of male coparceners to exclude sisters rejected..."
        ),
        start_char=1381,
        end_char=1681,
        structural_label="headnote_holding",
    )
    res_020 = verifier.verify_claim(
        "Female heirs cannot claim equal partition rights in ancestral property if a preliminary partition occurred before 2005.",
        [p_020]
    )
    assert res_020.status != ClaimVerificationStatus.SUPPORTED


# ---------------------------------------------------------------------------
# Test 2: Preservation of Truly Supported Claims
# ---------------------------------------------------------------------------
def test_m16_true_supported_claims_preserved(verifier):
    """Verify that M16_UNSEEN_001 through 005 remain correctly identified as supported."""
    m16_path = Path("evaluation/rag/milestone16_unseen_claims.jsonl")
    lines = [json.loads(l) for l in m16_path.read_text(encoding="utf-8").splitlines() if l.strip()]

    supported_cases = [c for c in lines if c["case_id"] in ["M16_UNSEEN_001", "M16_UNSEEN_002", "M16_UNSEEN_003", "M16_UNSEEN_004", "M16_UNSEEN_005"]]
    assert len(supported_cases) == 5

    for c in supported_cases:
        sp = c["supporting_passages"][0]
        ep = EvidencePassage(
            evidence_id=sp["evidence_id"],
            document_id=sp["document_id"],
            case_title=sp["case_title"],
            passage_text=sp["passage_text"],
            start_char=sp["start_char"],
            end_char=sp["end_char"],
            structural_label=sp["structural_label"],
        )
        res = verifier.verify_claim(c["claim_sentence"], [ep], query=c["question"])
        assert res.status == ClaimVerificationStatus.SUPPORTED, f"Case {c['case_id']} regressed from supported to {res.status}"


# ---------------------------------------------------------------------------
# Test 3: Milestone 17 Unseen Claims Dataset Integrity
# ---------------------------------------------------------------------------
def test_milestone17_unseen_claims_dataset_integrity(m17_unseen_path):
    """Verify that the M17 evaluation dataset contains at least 30 cases from distinct unstudied judgments."""
    assert m17_unseen_path.exists(), "Milestone 17 unseen claims JSONL must exist"

    records = [json.loads(l) for l in m17_unseen_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(records) >= 30, f"Expected at least 30 claims, found {len(records)}"

    doc_ids = {r["supporting_passages"][0]["document_id"] for r in records}
    assert len(doc_ids) == len(records), "Each claim must be drawn from a distinct judgment"

    labels = {r["gold_support_label"] for r in records}
    assert "supported" in labels
    assert "partially_supported" in labels
    assert "unsupported" in labels
    assert "contradicted" in labels

    for r in records:
        assert r["case_id"].startswith("M17_UNSEEN_")
        assert len(r["claim_sentence"].strip()) >= 15
        assert len(r["supporting_passages"][0]["passage_text"].strip()) >= 50
        assert r["annotation_provenance"] == "developer_curated_frozen_pre_evaluation"


# ---------------------------------------------------------------------------
# Test 4: Error Analysis and Baseline Provenance Artifact Integrity
# ---------------------------------------------------------------------------
def test_milestone17_error_analysis_artifact_integrity(m17_error_analysis_path):
    """Verify that milestone17_error_analysis.jsonl documents root causes and baseline provenance."""
    assert m17_error_analysis_path.exists(), "Error analysis JSONL must exist"

    records = [json.loads(l) for l in m17_error_analysis_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(records) == 20

    diag_cases = {r["case_id"]: r for r in records if "error_diagnosis" in r}
    assert "M16_UNSEEN_007" in diag_cases
    assert "M16_UNSEEN_008" in diag_cases
    assert "M16_UNSEEN_020" in diag_cases

    for cid in ["M16_UNSEEN_007", "M16_UNSEEN_008", "M16_UNSEEN_020"]:
        diag = diag_cases[cid]["error_diagnosis"]
        assert "failure_mode" in diag
        assert "causative_rule" in diag
        assert "remediation_strategy" in diag


# ---------------------------------------------------------------------------
# Test 5: Verification Results Artifact and External Review Declaration
# ---------------------------------------------------------------------------
def test_milestone17_verification_results_integrity(m17_results_path):
    """Verify that results file explicitly declares PENDING_EXTERNAL_REVIEW and has zero fabricated annotations."""
    assert m17_results_path.exists(), "Verification results JSON must exist"

    data = json.loads(m17_results_path.read_text(encoding="utf-8"))
    assert data["independent_legal_review_status"] == "PENDING_EXTERNAL_REVIEW"
    assert "zero annotations fabricated" in data["external_review_notes"].lower()

    # Regression baseline must have resolved all 3 false acceptances
    resolved = data["m16_regression_baseline_evaluation"]["original_false_acceptances_resolved"]
    assert resolved["M16_UNSEEN_007"]["resolved"] is True
    assert resolved["M16_UNSEEN_008"]["resolved"] is True
    assert resolved["M16_UNSEEN_020"]["resolved"] is True


# ---------------------------------------------------------------------------
# Test 6: Complete Safe Presentation Contract
# ---------------------------------------------------------------------------
def test_safe_presentation_contract_fail_closed(validator):
    """Verify that answers containing non-supported claims are never promoted to fully supported."""
    p_holding = EvidencePassage(
        evidence_id="E1",
        document_id="doc1",
        case_title="Case 1",
        passage_text="Section 118(e) provides a clear presumption regarding indorsements.",
        start_char=0,
        end_char=80,
        structural_label="headnote_holding",
    )
    p_unrelated = EvidencePassage(
        evidence_id="E2",
        document_id="doc2",
        case_title="Case 2",
        passage_text="The matter requires detailed appreciation of complex evidence regarding company affairs.",
        start_char=0,
        end_char=90,
        structural_label="general_text",
    )

    # 1. Answer with a partially supported claim
    sa_partial = StructuredAnswer(
        status="answer",
        claims=[
            StructuredClaim(text="Presumption applies to indorsements under Section 118(e).", evidence_ids=["E1"]),
            StructuredClaim(text="Anticipatory bail can be granted under SC/ST Act without examining prima facie case.", evidence_ids=["E1"]),
        ]
    )
    val_res, claims_attr = validator.validate_structured(sa_partial, [p_holding])
    policy = ClaimVerifier.evaluate_acceptance_policy(val_res, claims_attr)
    assert policy["action"] != "accept_fully_supported"
    assert policy["action"] == "accept_with_qualification"

    # 2. Answer with an unverified (not_evaluated) claim
    sa_unverified = StructuredAnswer(
        status="answer",
        claims=[
            StructuredClaim(text="Company directors bear distinct fiduciary accountability regarding company affairs.", evidence_ids=["E2"])
        ]
    )
    val_res_unv, claims_attr_unv = validator.validate_structured(sa_unverified, [p_unrelated])
    policy_unv = ClaimVerifier.evaluate_acceptance_policy(val_res_unv, claims_attr_unv)
    assert policy_unv["action"] != "accept_fully_supported"
    assert policy_unv["action"] == "accept_unverified"
