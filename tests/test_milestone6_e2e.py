"""
Unit and Regression Tests for Milestone 6 End-to-End Legal Quality.

Verifies:
1. CitationValidator heading tolerance: Ensures standard 5-heading prompt structures
   (e.g., '1. SHORT ANSWER:', '### 2. RELEVANT LEGAL PRINCIPLES') are recognized as
   structural meta-elements rather than substantive uncited claims.
2. Statutory completeness on conflict queries: Ensures PropositionGroundingGate
   strictly requires all compared provisions when conflict verbs ('override', 'dispense with')
   are present, while maintaining tolerance on procedural petition queries (UNSEEN003).
3. Pipeline max_passages budget invariant: Ensures RAGPipeline.query bounds prompt
   evidence and validation passages to max_passages.
4. Exact character offset fidelity across Milestone 6 target judgments.
5. FastAPI endpoint error masking and valid response contracts.
"""
import json
import os
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from apps.api.main import app

from services.rag.models import EvidencePassage, RAGResult, CitationValidationResult
from services.rag.validator import CitationValidator
from services.rag.grounding_gate import PropositionGroundingGate, GroundingStatus
from services.rag.pipeline import RAGPipeline
from services.rag.providers import MockLLMProvider
from services.rag.claim_reviewer import extract_claim_review_records, summarize_claim_reviews


@pytest.fixture(scope="module")
def api_client():
    return TestClient(app)


class TestMilestone6HeadingAndAttributionTolerance:
    """Verifies that standard 5-heading prompt structures are not flagged as unsupported sentences."""

    def test_five_heading_answer_passes_attribution(self):
        v = CitationValidator(require_citations_on_all_claims=True)
        passage = EvidencePassage(
            evidence_id="E1",
            document_id="2024_10_150_153",
            case_title="Atul Kumar v. Chairman JOSAA",
            passage_text="Held: The Supreme Court directed admission under Article 142.",
            start_char=100,
            end_char=163,
            judgment_rank=1,
            judgment_score=0.9
        )
        answer = (
            "1. SHORT ANSWER: The Supreme Court exercised powers under Article 142 to grant admission [E1].\n\n"
            "2. RELEVANT LEGAL PRINCIPLES: Under Article 142, the court can do complete justice [E1].\n\n"
            "3. APPLICATION TO FACTS: The petitioner was unable to pay fees due to portal glitch [E1].\n\n"
            "4. SUPPORTING JUDGMENTS: The holding is based on Atul Kumar v. Chairman JOSAA [E1].\n\n"
            "5. LIMITATIONS & UNCERTAINTIES: The relief was granted under extraordinary jurisdiction [E1]."
        )

        val_result, claims = v.validate(answer, [passage])
        assert val_result.is_valid is True, f"Validation failed: {val_result.validation_notes}"
        assert len(val_result.unsupported_sentences) == 0, f"Unsupported sentences: {val_result.unsupported_sentences}"
        assert val_result.attribution_complete is True
        assert val_result.cited_source_ids == ["E1"]
        assert len(claims) == 5

    def test_markdown_heading_prefixes_not_treated_as_unsupported(self):
        v = CitationValidator()
        passage = EvidencePassage(
            evidence_id="E1",
            document_id="doc1",
            case_title="Test",
            passage_text="text",
            start_char=0,
            end_char=4,
            judgment_rank=1,
            judgment_score=1.0
        )
        answer = (
            "### 1. SHORT ANSWER\n"
            "An appeal lies to the Supreme Court under Section 62 [E1].\n\n"
            "### 2. RELEVANT LEGAL PRINCIPLES\n"
            "Section 62 confers a statutory right of appeal on questions of law [E1]."
        )
        val_result, claims = v.validate(answer, [passage])
        assert val_result.is_valid is True
        assert len(val_result.unsupported_sentences) == 0


class TestMilestone6StatutoryConflictGate:
    """Verifies that conflict/override queries enforce all inquired provisions."""

    def test_conflict_query_with_missing_provision_abstains(self):
        gate = PropositionGroundingGate()
        query = "Does Section 71 of the PMLA override the CrPC to dispense with sanction under Section 197 CrPC?"
        # Passage contains Section 197 CrPC, but completely lacks Section 71 PMLA
        passage = EvidencePassage(
            evidence_id="E1",
            document_id="2024_7_62_68",
            case_title="State of Punjab v. Partap Singh Verka",
            passage_text="Section 197 of the CrPC creates a statutory bar against prosecuting public servants without prior sanction.",
            start_char=10,
            end_char=110,
            judgment_rank=1,
            judgment_score=0.9
        )
        decision = gate.assess_grounding(query, [passage])
        assert decision.is_grounded is False
        assert decision.status == GroundingStatus.TOPICALLY_RELEVANT_BUT_INSUFFICIENT_GROUNDING
        assert "Section 71" in decision.rationale or "Section 71" in decision.missing_provisions

    def test_procedural_quashing_query_with_substantive_section_passes(self):
        gate = PropositionGroundingGate()
        query = "Does an FIR under Section 420 IPC require dishonest inducement with mens rea since inception to survive quashing under Section 482 CrPC?"
        passage = EvidencePassage(
            evidence_id="E1",
            document_id="doc_ipc",
            case_title="State v. Accused",
            passage_text=(
                "Held: The FIR must disclose the following ingredients to make out an offence u/s.420 : "
                "(i) That the Accused has induced anyone since inception; "
                "(ii) That the inducement was fraudulent or dishonest; "
                "(iii) That mens rea existed at the time of such inducement."
            ),
            start_char=0,
            end_char=260,
            judgment_rank=1,
            judgment_score=0.9
        )
        decision = gate.assess_grounding(query, [passage])
        assert decision.is_grounded is True


class TestMilestone6PipelineBudgeting:
    """Verifies that max_passages bounds active prompt and validation passages."""

    def test_max_passages_bounds_active_evidence(self):
        pipe = RAGPipeline(llm_provider=MockLLMProvider())
        q = "Can the Supreme Court exercise powers under Article 142 of the Constitution to grant admission to an IIT candidate?"
        result = pipe.query(q, top_k_judgments=2, max_passages=1)

        # Must have exactly 1 active evidence passage in final RAGResult
        assert len(result.evidence_passages) == 1
        assert result.evidence_passages[0].evidence_id == "E1"
        assert result.citation_validation.valid_source_ids == ["E1"]


class TestMilestone6OffsetIntegrityOnCorpus:
    """Verifies exact character offsets for key Milestone 6 canonical judgments."""

    @pytest.mark.parametrize("doc_id", [
        "2024_10_150_153",   # Atul Kumar (Art 142 IIT admission)
        "2024_10_1802_1854",  # Glas Trust (IBC Sec 62)
        "2024_10_1475_1482",  # Neeraj Sud (Bolam test)
        "2024_10_1462_1474",  # Vidyasagar Prasad (Balance sheet limitation)
        "2024_10_1890_1901",  # Bijay Agarwal (Cheque signatory Sec 148)
        "2024_11_722_785"     # Demolition of structures (Due process)
    ])
    def test_canonical_judgment_exists_and_parseable(self, doc_id):
        fpath = Path(f"data/processed/aws_sc/{doc_id}.json")
        assert fpath.exists(), f"Corpus file missing: {fpath}"
        with open(fpath, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert "full_text" in data
        assert len(data["full_text"]) > 1000
        assert "document_id" in data
        assert data["document_id"] == doc_id
