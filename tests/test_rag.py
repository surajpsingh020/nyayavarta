"""
Automated Tests for Evidence-Grounded RAG Subsystem (Milestone 5A).

Tests cover:
1. Exact character offsets and source text integrity.
2. Citation ID validation (valid, missing, hallucinated).
3. Missing or irrelevant evidence (abstention).
4. Empty retrieval results.
5. Malformed model output.
6. Unsupported claims or references.
7. Deterministic behavior in retrieval and evidence assembly.
8. FastAPI /v1/rag/query endpoint integration.
"""
import pytest
import os
import json
from fastapi.testclient import TestClient

from apps.api.main import app
from services.rag.models import EvidencePassage
from services.rag.evidence import EvidenceAssembler, verify_evidence_offsets
from services.rag.providers import MockLLMProvider
from services.rag.validator import CitationValidator
from services.rag.pipeline import RAGPipeline


@pytest.fixture(scope="module")
def rag_pipeline():
    return RAGPipeline(llm_provider=MockLLMProvider())


@pytest.fixture(scope="module")
def api_client():
    return TestClient(app)


class TestRAGEvidenceAndOffsets:

    def test_exact_passage_offsets_and_source_integrity(self, rag_pipeline):
        """Passage character offsets must point 100% exactly to canonical judgment full_text."""
        query = "Is time of the essence of contract in agreement for sale"
        result = rag_pipeline.query(query, top_k_judgments=2, max_passages=3)

        assert len(result.evidence_passages) > 0, "No evidence passages extracted"

        # Check each passage against file system directly
        corpus_dir = "data/processed/aws_sc"
        for ep in result.evidence_passages:
            fpath = os.path.join(corpus_dir, f"{ep.document_id}.json")
            assert os.path.exists(fpath), f"Corpus document missing: {fpath}"

            with open(fpath, "r", encoding="utf-8") as f:
                doc = json.load(f)

            full_text = doc["full_text"]
            extracted_slice = full_text[ep.start_char:ep.end_char]
            assert extracted_slice == ep.passage_text, (
                f"Offset mismatch on {ep.evidence_id}: "
                f"full_text[{ep.start_char}:{ep.end_char}] does not equal passage_text!"
            )

        # Run automated offset verifier
        verified, errors = verify_evidence_offsets(result.evidence_passages, corpus_dir=corpus_dir)
        assert verified is True, f"Offset verifier reported errors: {errors}"


class TestCitationValidation:

    def test_citation_validator_valid_and_hallucinated_ids(self):
        """Validator must distinguish valid citations from hallucinated IDs."""
        validator = CitationValidator()
        mock_evidence = [
            EvidencePassage(
                evidence_id="E1",
                document_id="doc1",
                case_title="Test Case A",
                passage_text="Contract was executed.",
                start_char=0,
                end_char=21,
                judgment_rank=1,
                judgment_score=0.9
            ),
            EvidencePassage(
                evidence_id="E2",
                document_id="doc2",
                case_title="Test Case B",
                passage_text="Time was of the essence.",
                start_char=0,
                end_char=24,
                judgment_rank=2,
                judgment_score=0.8
            )
        ]

        # Case 1: Valid citations only
        good_text = "The contract was executed [E1], and time was of the essence [E2]."
        val_good, claims_good = validator.validate(good_text, mock_evidence)
        assert val_good.is_valid is True
        assert val_good.has_invalid_citations is False
        assert set(val_good.valid_source_ids) == {"E1", "E2"}
        assert len(val_good.invalid_source_ids) == 0

        # Case 2: Hallucinated citation [E99]
        bad_text = "The court relied on precedent [E1] and reversed on appeal [E99]."
        val_bad, claims_bad = validator.validate(bad_text, mock_evidence)
        assert val_bad.is_valid is False
        assert val_bad.has_invalid_citations is True
        assert "E99" in val_bad.invalid_source_ids
        assert "E1" in val_bad.valid_source_ids

    def test_unsupported_claims_detection(self):
        """Validator must detect sentences that make claims without citation tags."""
        validator = CitationValidator()
        mock_evidence = [
            EvidencePassage(
                evidence_id="E1",
                document_id="doc1",
                case_title="Case 1",
                passage_text="Bail was granted.",
                start_char=0,
                end_char=17,
                judgment_rank=1,
                judgment_score=0.9
            )
        ]

        mixed_text = "The accused was granted bail under strict conditions [E1]. The trial court also revoked passport permissions."
        val_result, claims = validator.validate(mixed_text, mock_evidence)

        assert len(val_result.unsupported_sentences) == 1
        assert "passport permissions" in val_result.unsupported_sentences[0]
        assert len(claims) == 2
        assert claims[0].is_grounded is True
        assert claims[1].is_grounded is False


class TestRAGPipelineEdgeCases:

    def test_missing_or_irrelevant_evidence_abstention(self, rag_pipeline):
        """When evidence is insufficient or irrelevant, pipeline must explicitly abstain."""
        abstain_provider = MockLLMProvider(mode=MockLLMProvider.MODE_FORCE_ABSTAIN)
        result = rag_pipeline.query(
            "What is the tax rate on intergalactic mineral transports?",
            provider=abstain_provider
        )

        assert result.status == "insufficient_evidence"
        assert "INSUFFICIENT EVIDENCE" in result.answer

    def test_empty_retrieval_results_handling(self):
        """Pipeline must handle empty retriever gracefully without crashing."""
        class EmptyRetriever:
            def retrieve(self, *args, **kwargs):
                return []

        pipeline = RAGPipeline(retriever=EmptyRetriever())
        result = pipeline.query("Some arbitrary legal question")

        assert result.status == "empty_retrieval"
        assert len(result.evidence_passages) == 0
        assert "No relevant judgments" in result.answer

    def test_malformed_model_output_handling(self, rag_pipeline):
        """Pipeline must flag error when model returns empty or malformed text."""
        malformed_provider = MockLLMProvider(mode=MockLLMProvider.MODE_MALFORMED)
        result = rag_pipeline.query(
            "Is bail available under PMLA section 45?",
            provider=malformed_provider
        )

        assert result.status == "error"

    def test_deterministic_behavior_in_retrieval_and_evidence_assembly(self, rag_pipeline):
        """Repeated identical queries must produce deterministic passages and answers."""
        query = "grounds for granting bail under PMLA section 45"
        res1 = rag_pipeline.query(query, top_k_judgments=2, max_passages=3)
        res2 = rag_pipeline.query(query, top_k_judgments=2, max_passages=3)

        assert res1.answer == res2.answer
        assert [ep.evidence_id for ep in res1.evidence_passages] == [ep.evidence_id for ep in res2.evidence_passages]
        assert [ep.start_char for ep in res1.evidence_passages] == [ep.start_char for ep in res2.evidence_passages]


class TestRAGApiEndpoint:

    def test_fastapi_rag_query_endpoint_success(self, api_client):
        """Endpoint POST /v1/rag/query must return structured 200 response."""
        payload = {
            "query": "Can an appellate court reverse an acquittal?",
            "top_k_judgments": 2,
            "max_passages": 3,
            "enable_graph": False,
            "provider_type": "mock"
        }
        response = api_client.post("/v1/rag/query", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert "answer" in data
        assert "status" in data
        assert data["status"] in ["answered", "insufficient_evidence"]
        assert "evidence_passages" in data
        assert "citation_validation" in data
        assert "claims" in data
        assert "timing_ms" in data
        assert "legal_disclaimer" in data

    def test_fastapi_rag_query_endpoint_validation_error(self, api_client):
        """Invalid query string (< 3 chars) must return 422 Unprocessable Entity."""
        payload = {"query": "a"}
        response = api_client.post("/v1/rag/query", json=payload)
        assert response.status_code == 422

    def test_fastapi_invalid_provider_returns_400(self, api_client):
        """Invalid provider_type must return 400 Bad Request."""
        payload = {
            "query": "Is time of the essence?",
            "provider_type": "unsupported_provider"
        }
        response = api_client.post("/v1/rag/query", json=payload)
        assert response.status_code == 400
        assert "Invalid provider_type" in response.json()["detail"]


class TestEvidenceIntegrityFailClosed:

    def test_incorrect_offsets_and_text_mismatch_excluded(self):
        """Passages with offset drift or tampered text must be excluded from generation."""
        from services.rag.evidence import verify_and_filter_evidence
        corpus_dir = "data/processed/aws_sc"

        # Valid passage
        p_valid = EvidencePassage(
            evidence_id="E1",
            document_id="2024_10_393_410",
            case_title="V. Senthil Balaji v. ED",
            passage_text="[Abhay S. Oka* and Augustine George Masih, JJ.]",
            start_char=161,
            end_char=208,
            judgment_rank=1,
            judgment_score=1.0
        )
        # Invalid: wrong offsets
        p_wrong_offset = EvidencePassage(
            evidence_id="E2",
            document_id="2024_10_393_410",
            case_title="V. Senthil Balaji v. ED",
            passage_text="[Abhay S. Oka* and Augustine George Masih, JJ.]",
            start_char=10,
            end_char=57,
            judgment_rank=2,
            judgment_score=0.9
        )
        # Invalid: tampered text
        p_tampered = EvidencePassage(
            evidence_id="E3",
            document_id="2024_10_393_410",
            case_title="V. Senthil Balaji v. ED",
            passage_text="Fabricated text not matching canonical full_text",
            start_char=187,
            end_char=234,
            judgment_rank=3,
            judgment_score=0.8
        )
        # Invalid: out of boundary
        p_out_of_bound = EvidencePassage(
            evidence_id="E4",
            document_id="2024_10_393_410",
            case_title="V. Senthil Balaji v. ED",
            passage_text="Text",
            start_char=9999999,
            end_char=10000003,
            judgment_rank=4,
            judgment_score=0.7
        )

        valid_passages, diagnostics = verify_and_filter_evidence(
            [p_valid, p_wrong_offset, p_tampered, p_out_of_bound],
            corpus_dir=corpus_dir
        )

        assert len(valid_passages) == 1
        assert valid_passages[0].passage_text == p_valid.passage_text
        assert len(diagnostics) == 3
        reasons = [d["reason"] for d in diagnostics]
        assert "exact_slice_text_mismatch" in reasons
        assert "offset_exceeds_full_text_length" in reasons

    def test_all_invalid_passages_fail_closed_and_abstain(self):
        """When every candidate passage fails offset verification, pipeline must fail closed and abstain."""
        class TamperedEvidenceAssembler:
            def assemble_evidence(self, *args, **kwargs):
                return [
                    EvidencePassage(
                        evidence_id="E1",
                        document_id="2024_10_393_410",
                        case_title="Test Case",
                        passage_text="Invalid text not matching canonical slice",
                        start_char=50,
                        end_char=91,
                        judgment_rank=1,
                        judgment_score=0.9
                    )
                ]

        pipeline = RAGPipeline(
            evidence_assembler=TamperedEvidenceAssembler(),
            llm_provider=MockLLMProvider()
        )
        result = pipeline.query("What are the grounds for bail?")

        assert result.status == "insufficient_evidence"
        assert len(result.evidence_passages) == 0
        assert "INSUFFICIENT EVIDENCE" in result.answer
        assert result.retrieval_metadata.get("offsets_verified") is False
        assert len(result.retrieval_metadata.get("offset_diagnostics", [])) == 1


class TestStrengthenedCitationValidator:

    def test_malformed_citation_markers_flagged(self):
        """Malformed citation tags like [E], [Eabc] must be flagged and invalidate response."""
        validator = CitationValidator()
        mock_evidence = [
            EvidencePassage(
                evidence_id="E1",
                document_id="doc1",
                case_title="Case 1",
                passage_text="Valid excerpt.",
                start_char=0,
                end_char=14,
                judgment_rank=1,
                judgment_score=1.0
            )
        ]

        text = "Under the statute, bail is restricted [Eabc] and conditions apply [E]."
        val, claims = validator.validate(text, mock_evidence)

        assert val.citation_syntax_valid is False
        assert val.is_valid is False

    def test_semantic_support_explicitly_not_evaluated(self):
        """Validator must explicitly report semantic support as not_evaluated."""
        validator = CitationValidator()
        mock_evidence = [
            EvidencePassage(
                evidence_id="E1",
                document_id="doc1",
                case_title="Case 1",
                passage_text="Valid excerpt.",
                start_char=0,
                end_char=14,
                judgment_rank=1,
                judgment_score=1.0
            )
        ]
        text = "Accused was released on bail [E1]."
        val, claims = validator.validate(text, mock_evidence)

        assert val.semantic_support_status == "not_evaluated"
        assert claims[0].semantic_support_status == "not_evaluated"
        assert any("not_evaluated" in note for note in val.validation_notes)

    def test_explicit_abstention_handling(self):
        """Explicit abstention must pass cleanly, while phrase in substantive text requires citations."""
        validator = CitationValidator()
        mock_evidence = [
            EvidencePassage(
                evidence_id="E1",
                document_id="doc1",
                case_title="Case 1",
                passage_text="Valid excerpt.",
                start_char=0,
                end_char=14,
                judgment_rank=1,
                judgment_score=1.0
            )
        ]

        # Case 1: Pure abstention response
        pure_abstain = "INSUFFICIENT EVIDENCE: The retrieved judicial passages do not provide sufficient evidence to answer this question."
        val1, claims1 = validator.validate(pure_abstain, mock_evidence)
        assert val1.is_valid is True
        assert len(val1.unsupported_sentences) == 0

        # Case 2: Substantive sentence mentioning the phrase without citation
        substantive_mention = "The high court noted insufficient evidence was adduced by the prosecution."
        val2, claims2 = validator.validate(substantive_mention, mock_evidence)
        assert val2.is_valid is False
        assert len(val2.unsupported_sentences) == 1
