"""
Automated unit and regression tests for Legal Citation and Entity Extraction (Milestone 4A).
Tests:
- Citation patterns (SCC, AIR, SCR, INSC, case titles, unanchored mentions)
- Statutory references (Acts, Sections, Articles, Orders/Rules, Schedules)
- Normalization routines
- Conservative entity resolution (resolved, ambiguous, unresolved)
- Malformed, empty, and noisy OCR text handling
"""
import pytest
import os
import json
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.extraction.citation_extractor import CitationExtractor
from services.extraction.statute_extractor import StatuteExtractor
from services.extraction.entity_resolver import EntityResolver


# --- Citation Extractor Tests ---

class TestCitationExtractor:
    @pytest.fixture
    def extractor(self):
        return CitationExtractor()

    def test_extract_neutral_insc(self, extractor):
        text = "Judgment reported as 2024 INSC 735 by the Supreme Court."
        cites = extractor.extract_formal_citations(text, "doc_test")
        assert len(cites) == 1
        assert cites[0]["citation_type"] == "neutral_insc"
        assert cites[0]["normalized_citation"] == "2024INSC735"
        assert cites[0]["confidence"] == "high"

    def test_extract_scc_standard(self, extractor):
        text = "As observed in (2019) 14 SCC 81 and also (2007) 3 SCC (Cri) 359."
        cites = extractor.extract_formal_citations(text, "doc_test")
        assert len(cites) == 2
        assert cites[0]["citation_type"] == "scc"
        assert cites[0]["normalized_citation"] == "(2019) 14 SCC 81"
        assert cites[1]["normalized_citation"] == "(2007) 3 SCC (Cri) 359"

    def test_extract_scc_online(self, extractor):
        text = "Relying upon 2024 SCC OnLine SC 1796 in subsequent appeals."
        cites = extractor.extract_formal_citations(text, "doc_test")
        assert len(cites) == 1
        assert cites[0]["citation_type"] == "scc_online"
        assert cites[0]["normalized_citation"] == "2024 SCC OnLine SC 1796"

    def test_extract_air(self, extractor):
        text = "Principles established in AIR 1978 SC 597 and AIR 1955 SC 807."
        cites = extractor.extract_formal_citations(text, "doc_test")
        assert len(cites) == 2
        assert cites[0]["normalized_citation"] == "AIR 1978 SC 597"
        assert cites[1]["normalized_citation"] == "AIR 1955 SC 807"

    def test_extract_scr(self, extractor):
        text = "Reported at [2024] 10 S.C.R. 108 and also [1978] 2 SCR 621."
        cites = extractor.extract_formal_citations(text, "doc_test")
        assert len(cites) == 2
        assert cites[0]["citation_type"] == "scr"
        assert cites[0]["normalized_citation"] == "[2024] 10 SCR 108"
        assert cites[1]["normalized_citation"] == "[1978] 2 SCR 621"

    def test_extract_case_title(self, extractor):
        text = "Maneka Gandhi v. Union of India established the doctrine of fairness."
        cases = extractor.extract_case_names(text, "doc_test")
        assert len(cases) == 1
        assert "Maneka Gandhi" in cases[0]["normalized_citation"]
        assert "Union of India" in cases[0]["normalized_citation"]
        assert cases[0]["confidence"] == "medium"

    def test_extract_unanchored_mention(self, extractor):
        text = "This principle was reaffirmed in the case of Shreya Singhal regarding freedom of speech."
        mentions = extractor.extract_unanchored_mentions(text, "doc_test")
        assert len(mentions) == 1
        assert "Shreya Singhal" in mentions[0]["normalized_citation"]
        assert mentions[0]["confidence"] == "low"

    def test_treatment_signal_detection(self, extractor):
        text = "Mineral Area Development Authority [2024] 8 SCR 540 - followed by the high court."
        cites = extractor.extract_formal_citations(text, "doc_test")
        assert len(cites) == 1
        assert cites[0]["treatment_signal"] == "followed"


# --- Statute Extractor Tests ---

class TestStatuteExtractor:
    @pytest.fixture
    def extractor(self):
        return StatuteExtractor()

    def test_extract_formal_act(self, extractor):
        text = "Under the Indian Penal Code, 1860 and the Limitation Act, 1963."
        acts = extractor.extract_acts(text, "doc_test")
        norm_acts = [a["normalized_reference"] for a in acts]
        assert "Indian Penal Code, 1860" in norm_acts
        assert "Limitation Act, 1963" in norm_acts

    def test_extract_act_acronyms(self, extractor):
        text = "Offences registered under PMLA, IPC, and IBC provisions."
        acts = extractor.extract_acts(text, "doc_test")
        norm_acts = [a["normalized_reference"] for a in acts]
        assert "Prevention of Money Laundering Act, 2002" in norm_acts
        assert "Indian Penal Code, 1860" in norm_acts
        assert "Insolvency and Bankruptcy Code, 2016" in norm_acts

    def test_extract_articles(self, extractor):
        text = "Violative of Article 21 and Articles 14, 15 and 19 of the Constitution."
        arts = extractor.extract_articles(text, "doc_test")
        assert len(arts) >= 2
        art_nums = [a["components"]["articles"] for a in arts]
        flat_nums = [num for sublist in art_nums for num in sublist]
        assert "21" in flat_nums
        assert "14" in flat_nums

    def test_extract_sections(self, extractor):
        text = "Charged under Section 302 of the IPC and u/s 438 of CrPC."
        secs = extractor.extract_sections(text, "doc_test")
        assert len(secs) >= 2
        sec_nums = [s["components"]["section_numbers"] for s in secs]
        assert any("302" in n for n in sec_nums)
        assert any("438" in n for n in sec_nums)

    def test_extract_orders_and_rules(self, extractor):
        text = "Application filed under Order XXI Rule 99 CPC read with Rule 9(4) of Security Interest Rules."
        rules = extractor.extract_orders_and_rules(text, "doc_test")
        assert len(rules) >= 2
        norm_rules = [r["normalized_reference"] for r in rules]
        assert any("Order XXI Rule 99" in r for r in norm_rules)
        assert any("Rule 9(4)" in r for r in norm_rules)

    def test_extract_schedules(self, extractor):
        text = "Disqualification under the Tenth Schedule of the Constitution."
        scheds = extractor.extract_schedules(text, "doc_test")
        assert len(scheds) == 1
        assert scheds[0]["normalized_reference"] == "Tenth Schedule"


# --- Entity Resolver Tests ---

class TestEntityResolver:
    @pytest.fixture
    def resolver(self):
        return EntityResolver()

    def test_resolve_exact_neutral_citation(self, resolver):
        mention = {
            "source_doc_id": "test_src",
            "citation_type": "neutral_insc",
            "raw_text": "2024 INSC 735",
            "normalized_citation": "2024INSC735"
        }
        res = resolver.resolve_citation(mention)
        assert res["resolution_status"] == "resolved"
        assert res["resolved_document_id"] == "2024_10_108_125"
        assert res["confidence_score"] == 1.0

    def test_unresolved_historical_citation(self, resolver):
        mention = {
            "source_doc_id": "test_src",
            "citation_type": "scc",
            "raw_text": "(1973) 4 SCC 225",
            "normalized_citation": "(1973) 4 SCC 225",
            "components": {"year": 1973, "volume": 4, "page": 225}
        }
        res = resolver.resolve_citation(mention)
        assert res["resolution_status"] == "unresolved"
        assert res["resolved_document_id"] is None
        assert res["match_method"] == "historical_reporter_pre_2024"

    def test_ambiguous_case_title_flagged(self, resolver):
        mention = {
            "source_doc_id": "test_src",
            "citation_type": "case_title",
            "raw_text": "State of Madhya Pradesh v. Accused",
            "normalized_citation": "State of Madhya Pradesh v. Accused"
        }
        res = resolver.resolve_citation(mention)
        # Should be ambiguous or unresolved, never arbitrarily resolved to 1 doc
        assert res["resolution_status"] in ["ambiguous", "unresolved"]
        if res["resolution_status"] == "ambiguous":
            assert len(res.get("ambiguous_candidate_ids", [])) > 1

    def test_non_fabrication_guarantee(self, resolver):
        mention = {
            "source_doc_id": "test_src",
            "citation_type": "case_title",
            "raw_text": "Fictional Party X v. Imaginary Entity Y",
            "normalized_citation": "Fictional Party X v. Imaginary Entity Y"
        }
        res = resolver.resolve_citation(mention)
        assert res["resolution_status"] == "unresolved"
        assert res["resolved_document_id"] is None


# --- Malformed & Robustness Tests ---

class TestRobustness:
    def test_empty_and_noise_text(self):
        c_ext = CitationExtractor()
        s_ext = StatuteExtractor()

        # Empty string
        assert c_ext.extract_all("", "doc_1") == []
        assert s_ext.extract_all("", "doc_1") == []

        # OCR junk / punctuation salad
        noise = "^%#@! &*( )__+ === |||| \x00\x01\x02 ??? ~~~~"
        assert c_ext.extract_all(noise, "doc_1") == []
        assert s_ext.extract_all(noise, "doc_1") == []

    def test_broken_citation_brackets(self):
        c_ext = CitationExtractor()
        broken = "In [2024 10 SCR and (2019 SCC missing page"
        cites = c_ext.extract_all(broken, "doc_1")
        # Should not crash and should not generate corrupt tokens
        assert isinstance(cites, list)
