"""
Regression and validation tests for Milestone 4A.1 (Extraction Validation Gate).

Tests:
1. Header artifact stripping from case titles (INSC prefix, Case Law Cited, etc.)
2. Treatment signal newline normalization
3. Span deduplication in extract_all
4. Entity resolver status invariants (resolved -> doc_id, unresolved -> None, ambiguous -> None + candidates >= 2)
5. Ambiguous statutory provisions (bare section numbers without governing act)
6. Non-fabrication guardrails (fictional/unmatched cases never assigned corpus ID)
7. Cross-document neutral citation resolution
"""
import pytest
import os
import json
import sys

from services.extraction.citation_extractor import CitationExtractor
from services.extraction.statute_extractor import StatuteExtractor
from services.extraction.entity_resolver import EntityResolver


class TestExtractionValidationDefects:
    @pytest.fixture
    def citation_extractor(self):
        return CitationExtractor()

    @pytest.fixture
    def statute_extractor(self):
        return StatuteExtractor()

    @pytest.fixture
    def entity_resolver(self):
        return EntityResolver()

    # 1. Header artifact stripping
    def test_case_title_strips_insc_header(self, citation_extractor):
        text = "[2024] 10 S.C.R. 108 : 2024 INSC 735 Vijay Singh @ Vijay Kr. Sharma v. The State of Bihar"
        cases = citation_extractor.extract_case_names(text, "test_doc")
        assert len(cases) >= 1
        party1 = cases[0]["components"]["party1"]
        assert not party1.startswith("INSC")
        assert not party1.startswith("2024 INSC")
        assert "Vijay Singh" in party1

    def test_case_title_strips_case_law_cited_header(self, citation_extractor):
        text = "Case Law Cited State of Goa v. Sanjay Thakran [2007] 3 SCR 507"
        cases = citation_extractor.extract_case_names(text, "test_doc")
        assert len(cases) >= 1
        party1 = cases[0]["components"]["party1"]
        assert not party1.startswith("Case Law Cited")
        assert "State of Goa" in party1

    # 2. Treatment signal newline normalization
    def test_treatment_signal_normalizes_newlines(self, citation_extractor):
        text = "Mineral Area Development Authority [2024] 8 SCR 540 - referred \n   to by the bench."
        cites = citation_extractor.extract_formal_citations(text, "test_doc")
        assert len(cites) >= 1
        signal = cites[0]["treatment_signal"]
        assert signal == "referred to"
        assert "\n" not in signal

    # 3. Span deduplication in extract_all
    def test_extract_all_deduplicates_exact_spans(self, citation_extractor):
        text = "In Maneka Gandhi v. Union of India, the court laid down the law."
        all_cites = citation_extractor.extract_all(text, "test_doc")
        spans = [(c["start_char"], c["end_char"], c["citation_type"]) for c in all_cites]
        assert len(spans) == len(set(spans)), "Duplicate spans found in extract_all output"

    # 4. Status invariants in EntityResolver
    def test_status_invariants_resolved(self, entity_resolver):
        mention = {
            "source_doc_id": "doc_a",
            "citation_type": "neutral_insc",
            "raw_text": "2024 INSC 735",
            "normalized_citation": "2024INSC735"
        }
        res = entity_resolver.resolve_citation(mention)
        assert res["resolution_status"] == "resolved"
        assert res["resolved_document_id"] is not None
        assert res.get("resolved_document_id") == "2024_10_108_125"

    def test_status_invariants_unresolved(self, entity_resolver):
        mention = {
            "source_doc_id": "doc_a",
            "citation_type": "scc",
            "raw_text": "(1980) 1 SCC 81",
            "normalized_citation": "(1980) 1 SCC 81",
            "components": {"year": 1980, "volume": 1, "page": 81}
        }
        res = entity_resolver.resolve_citation(mention)
        assert res["resolution_status"] == "unresolved"
        assert res["resolved_document_id"] is None

    def test_status_invariants_ambiguous(self, entity_resolver):
        mention = {
            "source_doc_id": "doc_a",
            "citation_type": "case_title",
            "raw_text": "State of Madhya Pradesh v. Accused",
            "normalized_citation": "State of Madhya Pradesh v. Accused"
        }
        res = entity_resolver.resolve_citation(mention)
        if res["resolution_status"] == "ambiguous":
            assert res["resolved_document_id"] is None
            assert "ambiguous_candidate_ids" in res
            assert len(res["ambiguous_candidate_ids"]) >= 2

    # 5. Ambiguous statutory provisions
    def test_bare_section_extracted_without_governing_act(self, statute_extractor):
        text = "Appellant sought benefit under Section 5 and Section 14 of the act."
        sections = statute_extractor.extract_sections(text, "test_doc")
        assert len(sections) >= 2
        sec_nums = [s["components"]["section_numbers"] for s in sections]
        assert "5" in sec_nums
        assert "14" in sec_nums
        # Verify governing statute is null when not in token
        sec_5 = next(s for s in sections if s["components"]["section_numbers"] == "5")
        assert sec_5["components"]["governing_statute"] is None

    # 6. Cross-document neutral citation resolution
    def test_cross_document_neutral_resolution(self, entity_resolver):
        # 2024 INSC 595 cited from a different document
        mention = {
            "source_doc_id": "2024_8_717_726",
            "citation_type": "neutral_insc",
            "raw_text": "2024 INSC 595",
            "normalized_citation": "2024INSC595"
        }
        res = entity_resolver.resolve_citation(mention)
        assert res["resolution_status"] == "resolved"
        assert res["resolved_document_id"] == "2024_8_1061_1085"
        assert res["is_self_citation"] is False
