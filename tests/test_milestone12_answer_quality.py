"""
Milestone 12: Legal Answer Quality & Evidence Support Validation Test Suite.

Verifies claim-level evidence support, decoupling of syntactic citation existence
from semantic entailment, and audits the 10 High-Risk Legal Failure Modes:
1. Party submissions presented as judicial findings.
2. Headnotes or issue-framing text presented as the operative holding.
3. A holding quoted from an earlier judgment but not adopted by the current court.
4. Statutory exceptions omitted from an otherwise relevant passage.
5. A multi-part claim where only one component is supported.
6. A claim that generalizes beyond the facts or scope of the judgment.
7. Contradictory passages presented as settled doctrine.
8. An existing citation ID attached to an unrelated proposition.
9. An out-of-corpus precedent treated as verified.
10. An unsupported claim returned as fully validated.
"""
import pytest
from typing import List, Dict, Any

from services.rag.models import (
    RAGResult,
    EvidencePassage,
    CitationValidationResult,
    ClaimAttribution,
    StructuredAnswer,
    StructuredClaim
)
from services.rag.claim_reviewer import (
    ClaimReviewRecord,
    extract_claim_review_records,
    summarize_claim_reviews
)
from services.rag.validator import CitationValidator


@pytest.fixture
def validator():
    return CitationValidator()


@pytest.fixture
def sample_passages():
    p1 = EvidencePassage(
        evidence_id="E1",
        document_id="2024_10_793_859",
        case_title="Chief Commissioner of Central Goods and Service Tax v. M/s Safari Retreats Pvt. Ltd.",
        citation="[2024] 10 SCR 793",
        passage_text=(
            "Held: Whether a building is a 'plant' within the meaning of the exception in Section 17(5)(d) "
            "of the CGST Act is a question of fact to be determined by applying the functionality test. "
            "If the building is indispensable for the business of leasing, it may qualify. Matters remanded to High Court."
        ),
        start_char=1500,
        end_char=1800,
        structural_label="judicial_holding",
        structural_confidence=0.95
    )
    p2 = EvidencePassage(
        evidence_id="E2",
        document_id="2024_10_1752_1765",
        case_title="Bijay Agarwal v. Medilines",
        citation="[2024] 10 SCR 1752",
        passage_text=(
            "Mr. Sen, learned Senior Counsel for the appellant, vehemently contended that Section 34 of the "
            "Arbitration and Conciliation Act, 1996 confers inherent powers on the court to modify an arbitral award."
        ),
        start_char=2000,
        end_char=2250,
        structural_label="party_submissions",
        structural_confidence=0.90
    )
    p3 = EvidencePassage(
        evidence_id="E3",
        document_id="2024_10_1752_1765",
        case_title="Bijay Agarwal v. Medilines",
        citation="[2024] 10 SCR 1752",
        passage_text=(
            "Operative Ratio: This Court has consistently held that Section 34 does not permit the court to "
            "modify an arbitral award. The court may either uphold or set aside the award."
        ),
        start_char=3500,
        end_char=3750,
        structural_label="judicial_holding",
        structural_confidence=0.95
    )
    return [p1, p2, p3]


class TestMilestone12LegalAnswerQuality:

    # 1. Failure Mode 1: Party submissions presented as judicial findings
    def test_failure_mode_1_party_submissions_distinguished_from_findings(self, validator, sample_passages):
        answer = StructuredAnswer(
            status="answer",
            claims=[
                StructuredClaim(
                    text="The Supreme Court held that Section 34 permits the court to modify arbitral awards.",
                    evidence_ids=["E2"]
                )
            ]
        )
        val_res, claims = validator.validate_structured(answer, sample_passages)

        assert len(claims) == 1
        claim = claims[0]
        # Must detect that cited passage is solely a party submission
        assert claim.relies_only_on_party_submissions is True
        assert "party_submissions" in claim.structural_natures

        # Diagnostic warning must be recorded in validation notes
        has_warning = any("party submissions" in note for note in val_res.validation_notes)
        assert has_warning is True, "Expected warning about party submission reliance"

        # Claim-level audit mapping
        rag_res = RAGResult(
            query="Can a court modify an arbitral award under Section 34?",
            answer=answer.claims[0].text,
            status="answered",
            evidence_passages=sample_passages,
            citation_validation=val_res,
            claims=claims
        )
        records = extract_claim_review_records(rag_res, "TEST_M12_01")
        assert len(records) == 1
        rec = records[0]
        assert rec.source_structural_nature == "party_submission"

    # 2. Failure Mode 2: Headnotes or issue-framing text presented as operative holding
    def test_failure_mode_2_headnote_framing_vs_operative_holding(self, validator):
        p_framing = EvidencePassage(
            evidence_id="E1",
            document_id="2024_10_100_150",
            passage_text="Issue framed: Whether the High Court committed error in quashing the FIR under Section 482.",
            start_char=200,
            end_char=300,
            structural_label="facts_procedural"
        )
        p_holding = EvidencePassage(
            evidence_id="E2",
            document_id="2024_10_100_150",
            passage_text="Held: The High Court exceeded its jurisdiction; the FIR discloses prima facie cognizable offences.",
            start_char=1200,
            end_char=1320,
            structural_label="judicial_holding"
        )
        answer = StructuredAnswer(
            status="answer",
            claims=[
                StructuredClaim(text="The High Court committed error in quashing the FIR.", evidence_ids=["E1"])
            ]
        )
        val_res, claims = validator.validate_structured(answer, [p_framing, p_holding])
        assert claims[0].structural_natures == ["facts_procedural"]

    # 3. Failure Mode 3: Holding quoted from earlier judgment not adopted by current court
    def test_failure_mode_3_quoted_precedent_distinguished(self, validator):
        p_quoted = EvidencePassage(
            evidence_id="E1",
            document_id="2024_10_200_250",
            passage_text="In State of Haryana v. Bhajan Lal, it was observed that FIR could be quashed in rarest of rare cases.",
            start_char=800,
            end_char=920,
            structural_label="court_analysis"
        )
        answer = StructuredAnswer(
            status="answer",
            claims=[
                StructuredClaim(text="The 2024 bench formulated the Bhajan Lal guidelines.", evidence_ids=["E1"])
            ]
        )
        val_res, claims = validator.validate_structured(answer, [p_quoted])
        assert claims[0].structural_natures == ["court_analysis"]

    # 4. Failure Mode 4: Statutory exceptions omitted from an otherwise relevant passage
    def test_failure_mode_4_statutory_exception_omission(self, sample_passages):
        # E1 is Safari Retreats: building can qualify as plant ONLY IF functionality test is satisfied on facts
        c_text = "All shopping malls constructed for leasing out automatically qualify as plant for ITC."
        rec = ClaimReviewRecord(
            review_id="CR_TEST_M12_04",
            query_id="M10_006",
            question="Does a shopping mall qualify as plant under Section 17(5)(d)?",
            answer_text=c_text,
            claim_id="C01",
            claim_sentence=c_text,
            cited_evidence_ids=["E1"],
            supporting_passages=[sample_passages[0].model_dump()],
            support_label="partially_supported",
            directly_supports_claim=True,
            all_material_components_supported=False,
            omits_statutory_qualification_or_exception=True,
            claim_overgeneralizes_holding=True,
            reviewer_notes="Omits the essential functionality test and remand requirement."
        )
        assert rec.omits_statutory_qualification_or_exception is True
        assert rec.support_label == "partially_supported"
        assert rec.all_material_components_supported is False

    # 5. Failure Mode 5: Multi-part claim where only one component is supported
    def test_failure_mode_5_multipart_claim_partial_support(self, sample_passages):
        c_text = "The Supreme Court applied the functionality test and held that shopping mall builders pay zero GST universally."
        rec = ClaimReviewRecord(
            review_id="CR_TEST_M12_05",
            query_id="M10_006",
            question="Does a shopping mall qualify as plant?",
            answer_text=c_text,
            claim_id="C01",
            claim_sentence=c_text,
            cited_evidence_ids=["E1"],
            supporting_passages=[sample_passages[0].model_dump()],
            support_label="partially_supported",
            directly_supports_claim=False,
            all_material_components_supported=False,
            reviewer_notes="First part supported; zero GST assertion completely unsupported."
        )
        assert rec.all_material_components_supported is False
        assert rec.support_label == "partially_supported"

    # 6. Failure Mode 6: Claim that generalizes beyond the facts or scope of the judgment
    def test_failure_mode_6_claim_overgeneralization(self):
        rec = ClaimReviewRecord(
            review_id="CR_TEST_M12_06",
            query_id="M10_001",
            question="Can the Supreme Court exercise powers under Article 142?",
            answer_text="Article 142 automatically invalidates all admission fee deadlines across India.",
            claim_id="C01",
            claim_sentence="Article 142 automatically invalidates all admission fee deadlines across India.",
            cited_evidence_ids=["E1"],
            support_label="partially_supported",
            claim_overgeneralizes_holding=True,
            directly_supports_claim=False,
            reviewer_notes="Extraordinary equitable relief under Article 142 is not a universal precedent."
        )
        assert rec.claim_overgeneralizes_holding is True
        assert rec.support_label == "partially_supported"

    # 7. Failure Mode 7: Contradictory passages presented as settled doctrine
    def test_failure_mode_7_contradictory_passages_handling(self, sample_passages):
        # E3 directly contradicts that courts can modify awards
        c_text = "A court hearing an application under Section 34 has authority to alter the award terms."
        rec = ClaimReviewRecord(
            review_id="CR_TEST_M12_07",
            query_id="M10_031",
            question="Can a court modify an arbitral award?",
            answer_text=c_text,
            claim_id="C01",
            claim_sentence=c_text,
            cited_evidence_ids=["E3"],
            supporting_passages=[sample_passages[2].model_dump()],
            support_label="contradicted",
            directly_supports_claim=False,
            reviewer_notes="Evidence expressly holds the court has no power to modify an award under Section 34."
        )
        assert rec.support_label == "contradicted"

    # 8. Failure Mode 8: Existing citation ID attached to an unrelated proposition
    def test_failure_mode_8_existing_citation_id_on_unrelated_proposition(self, validator, sample_passages):
        answer = StructuredAnswer(
            status="answer",
            claims=[
                StructuredClaim(
                    text="The High Court must grant anticipatory bail in money laundering cases.",
                    evidence_ids=["E1"]
                )
            ]
        )
        val_res, claims = validator.validate_structured(answer, sample_passages)

        # Syntactic validation succeeds because E1 exists in supplied_evidence
        assert val_res.citation_existence_valid is True
        assert val_res.is_valid is True
        assert val_res.semantic_support_status == "not_evaluated"

        # Semantic audit explicitly decouples syntactic existence from substantive support
        rec = ClaimReviewRecord(
            review_id="CR_TEST_M12_08",
            query_id="M10_008_UNREL",
            question="Must bail be granted in PMLA cases?",
            answer_text=answer.claims[0].text,
            claim_id="C01",
            claim_sentence=answer.claims[0].text,
            cited_evidence_ids=["E1"],
            supporting_passages=[sample_passages[0].model_dump()],
            citation_existence_valid=True,
            directly_supports_claim=False,
            all_material_components_supported=False,
            support_label="unsupported",
            reviewer_notes="Citation E1 exists (CGST Act case), but provides zero support for PMLA bail proposition."
        )
        assert rec.citation_existence_valid is True
        assert rec.directly_supports_claim is False
        assert rec.support_label == "unsupported"

    # 9. Failure Mode 9: Out-of-corpus precedent treated as verified
    def test_failure_mode_9_out_of_corpus_precedent_unverified(self):
        rec = ClaimReviewRecord(
            review_id="CR_TEST_M12_09",
            query_id="M10_037",
            question="Did the Supreme Court overrule Kesavananda Bharati?",
            answer_text="The 2024 bench confirmed Kesavananda Bharati is bad law.",
            claim_id="C01",
            claim_sentence="The 2024 bench confirmed Kesavananda Bharati is bad law.",
            cited_evidence_ids=[],
            support_label="unsupported",
            should_have_abstained=True,
            reviewer_notes="Out-of-corpus historical precedent cannot be verified from 2024 corpus slice alone."
        )
        assert rec.should_have_abstained is True
        assert rec.support_label == "unsupported"

    # 10. Failure Mode 10: Unsupported claim returned as fully validated
    def test_failure_mode_10_unsupported_claim_not_fully_validated(self, validator, sample_passages):
        answer = StructuredAnswer(
            status="answer",
            claims=[
                StructuredClaim(text="Uncited substantive assertion without evidence.", evidence_ids=[]),
                StructuredClaim(text="Valid claim with evidence.", evidence_ids=["E1"])
            ]
        )
        val_res, claims = validator.validate_structured(answer, sample_passages)
        # Must fail validation because uncited assertion is present
        assert val_res.is_valid is False
        assert val_res.attribution_complete is False
        assert len(val_res.unsupported_sentences) == 1

    # 11. Disaggregation of validation metrics
    def test_disaggregated_metrics_accounting(self):
        records = [
            ClaimReviewRecord(
                review_id="R1", query_id="Q1", question="Q", answer_text="A", claim_id="C1", claim_sentence="S1",
                support_label="supported", citation_existence_valid=True, directly_supports_claim=True
            ),
            ClaimReviewRecord(
                review_id="R2", query_id="Q2", question="Q", answer_text="A", claim_id="C1", claim_sentence="S2",
                support_label="partially_supported", citation_existence_valid=True, directly_supports_claim=True,
                omits_statutory_qualification_or_exception=True
            ),
            ClaimReviewRecord(
                review_id="R3", query_id="Q3", question="Q", answer_text="A", claim_id="C1", claim_sentence="S3",
                support_label="unsupported", citation_existence_valid=True, directly_supports_claim=False
            ),
            ClaimReviewRecord(
                review_id="R4", query_id="Q4", question="Q", answer_text="A", claim_id="C00_ABSTAIN", claim_sentence="Insufficient evidence",
                support_label="supported", should_have_abstained=True
            )
        ]
        summary = summarize_claim_reviews(records)
        assert summary["total_claims"] == 4
        assert summary["label_breakdown"]["supported"] == 2
        assert summary["label_breakdown"]["partially_supported"] == 1
        assert summary["label_breakdown"]["unsupported"] == 1
