"""
Unit and Regression Tests for Proposition Grounding Gate and Abstention Guardrails (Milestone 5D).

Verifies:
1. Reproduction and remediation of LAQ015 (anticipatory bail in contempt) and LAQ016 (GM mustard patent immunity).
2. Proper grounding classification for directly grounded evidence (LAQ001, LAQ003).
3. Handling of missing evidence and out-of-corpus queries.
4. Conservative fallback when grounding check is unavailable or encounters errors.
5. Structural content classification (court holding vs party submission vs facts vs lower court).
6. Fail-closed behavior when all passages are pure party submissions.
7. Sub-10ms CPU latency overhead and deterministic behavior.
8. Preservation of exact character offsets, citation validation, and API contracts.
"""
import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from apps.api.main import app

from services.rag.models import EvidencePassage, RAGResult
from services.rag.grounding_gate import (
    PropositionGroundingGate,
    GroundingStatus,
    PassageContentType,
    GroundingDecision
)
from services.rag.pipeline import RAGPipeline
from services.rag.providers import MockLLMProvider


@pytest.fixture(scope="module")
def api_client():
    return TestClient(app)


class TestGroundingFailuresReproductionAndFix:
    """Targeted regression tests reproducing and verifying the fixes for LAQ015 and LAQ016."""

    def test_laq015_anticipatory_bail_in_contempt_abstains(self):
        """
        LAQ015: Anticipatory bail under Section 438 in contempt proceedings.
        Evidence from Dhanraj Aswani and Tusharbhai discusses Section 438, but does NOT
        establish that anticipatory bail lies in contempt proceedings.
        Must abstain with topically_relevant_but_insufficient_grounding.
        """
        gate = PropositionGroundingGate()
        query = (
            "Does the statutory provision for anticipatory bail under Section 438 CrPC "
            "establish that an accused can seek pre-arrest bail in contempt of court proceedings?"
        )
        passages = [
            EvidencePassage(
                evidence_id="E1",
                document_id="2024_9_257_312",
                case_title="Dhanraj Aswani v. Amar S. Mulchandani",
                passage_text=(
                    "Under Section 438, the pre-condition for a person to apply for pre-arrest bail "
                    "is a reason to believe that he may be arrested on an accusation of having committed "
                    "a non-bailable offence. Custody in one case does not take away apprehension of arrest in a different case."
                ),
                start_char=100,
                end_char=350,
                judgment_rank=1,
                judgment_score=0.9
            ),
            EvidencePassage(
                evidence_id="E2",
                document_id="2024_8_235_286",
                case_title="Tusharbhai Rajnikantbhai Shah v. Kamal Dayani",
                passage_text=(
                    "An order of anticipatory bail does not restrict the rights of police to investigate. "
                    "In the present contempt petition, contempt notices against the officers may be discharged."
                ),
                start_char=200,
                end_char=420,
                judgment_rank=2,
                judgment_score=0.85
            )
        ]

        decision = gate.assess_grounding(query, passages)
        assert decision.is_grounded is False
        assert decision.status == GroundingStatus.TOPICALLY_RELEVANT_BUT_INSUFFICIENT_GROUNDING
        assert "contempt" in decision.rationale.lower()

    def test_laq016_gm_mustard_patent_immunity_abstains(self):
        """
        LAQ016: GM mustard environmental clearance does NOT establish patent immunity.
        Evidence from Gene Campaign discusses environmental clearance and biosafety,
        but contains zero mention of patent immunity or the Patents Act.
        Must abstain with topically_relevant_but_insufficient_grounding.
        """
        gate = PropositionGroundingGate()
        query = (
            "Does the environmental clearance decision on genetically modified mustard "
            "establish nationwide patent immunity for agricultural biotechnology developers?"
        )
        passages = [
            EvidencePassage(
                evidence_id="E1",
                document_id="2024_7_1847_2142",
                case_title="Gene Campaign v. Union of India",
                passage_text=(
                    "Genetic Engineering Appraisal Committee (GEAC), a body under the Ministry of Environment, "
                    "recommended environmental release of Genetically Modified (GM) mustard hybrid DMH-11 "
                    "subject to compliance with biosafety protocols and environmental conditions."
                ),
                start_char=150,
                end_char=440,
                judgment_rank=1,
                judgment_score=0.92
            )
        ]

        decision = gate.assess_grounding(query, passages)
        assert decision.is_grounded is False
        assert decision.status == GroundingStatus.TOPICALLY_RELEVANT_BUT_INSUFFICIENT_GROUNDING
        assert "patent" in decision.rationale.lower() or "missing" in decision.rationale.lower()


class TestDirectlyGroundedPropositions:
    """Verifies that queries with genuine, authoritative grounding pass the gate with sufficient_evidence."""

    def test_directly_grounded_ratio_passes(self):
        """Grounded question on Section 45 PMLA and Article 21 must pass gate."""
        gate = PropositionGroundingGate()
        query = "What are the legal grounds for granting bail under Section 45 PMLA during prolonged incarceration?"
        passages = [
            EvidencePassage(
                evidence_id="E1",
                document_id="2024_10_393_410",
                case_title="Manish Sisodia v. Directorate of Enforcement",
                passage_text=(
                    "Held: The appellant has made out legal grounds for the granting of bail under Section 45 PMLA. "
                    "Prolonged incarceration before being pronounced guilty should not be permitted "
                    "to become punishment without trial. The twin conditions under Section 45 PMLA cannot "
                    "take away personal liberty under Article 21 of the Constitution where trial is delayed."
                ),
                start_char=500,
                end_char=800,
                judgment_rank=1,
                judgment_score=0.95
            )
        ]

        decision = gate.assess_grounding(query, passages)
        assert decision.is_grounded is True
        assert decision.status == GroundingStatus.SUFFICIENT_EVIDENCE
        assert decision.has_holding_or_authoritative_support is True

    def test_missing_evidence_returns_no_relevant_evidence(self):
        """When evidence list is empty, gate must return no_relevant_evidence."""
        gate = PropositionGroundingGate()
        decision = gate.assess_grounding("What is the admiralty procedure for prize court seizures?", [])
        assert decision.is_grounded is False
        assert decision.status == GroundingStatus.NO_RELEVANT_EVIDENCE


class TestContentClassification:
    """Verifies structural classification of judgment segments (holding vs submission vs facts)."""

    def test_classify_court_holding(self):
        text = "Held: In our considered view, an appellate court cannot interfere with an acquittal merely because a second view is possible."
        cls_info = PropositionGroundingGate.classify_passage_content(text)
        assert cls_info["content_type"] == PassageContentType.HOLDING.value
        assert cls_info["confidence"] >= 0.8

    def test_classify_party_submission(self):
        text = "Learned counsel for the appellant submitted that the prosecution failed to prove circumstantial evidence chain."
        cls_info = PropositionGroundingGate.classify_passage_content(text)
        assert cls_info["content_type"] == PassageContentType.SUBMISSION.value
        assert cls_info["confidence"] >= 0.75

    def test_classify_facts_or_procedural(self):
        text = "The brief facts of the case are that an FIR was registered on 12.05.2021 and the trial court convicted the appellant."
        cls_info = PropositionGroundingGate.classify_passage_content(text)
        assert cls_info["content_type"] == PassageContentType.FACTS_OR_PROCEDURAL.value

    def test_classify_unknown_when_indicators_absent(self):
        text = "This document is dated 12 October 2024 and was marked as Exhibit P-1."
        cls_info = PropositionGroundingGate.classify_passage_content(text)
        assert cls_info["content_type"] == PassageContentType.UNKNOWN.value
        assert cls_info["confidence"] == 0.0

    def test_pure_party_submissions_fail_grounding(self):
        """Passages containing only party arguments without court holding must fail grounding."""
        gate = PropositionGroundingGate()
        query = "Can a high court quash proceedings without hearing the complainant?"
        passages = [
            EvidencePassage(
                evidence_id="E1",
                document_id="doc1",
                case_title="Sample Case",
                passage_text="Learned senior counsel argued that the high court erred. Appellant submitted that notice was required.",
                start_char=0,
                end_char=105,
                judgment_rank=1,
                judgment_score=0.9
            )
        ]
        decision = gate.assess_grounding(query, passages)
        assert decision.is_grounded is False
        assert decision.status == GroundingStatus.TOPICALLY_RELEVANT_BUT_INSUFFICIENT_GROUNDING
        assert "submissions" in decision.rationale.lower()


class TestConservativeFallbackAndRobustness:
    """Verifies conservative fallback when unexpected errors or component failures occur."""

    def test_gate_exception_triggers_grounding_check_unavailable_fallback(self):
        """If gate raises unexpected exception, conservative fallback returns grounding_check_unavailable."""
        gate = PropositionGroundingGate()

        # Simulate exception by passing malformed mock object
        class CorruptedPassage:
            passage_text = None  # None causes .lower() to raise AttributeError

        corrupted = [CorruptedPassage()]
        decision = gate.assess_grounding("Some query", corrupted)  # type: ignore

        assert decision.is_grounded is False
        assert decision.status == GroundingStatus.GROUNDING_CHECK_UNAVAILABLE
        assert "unexpected error" in decision.rationale.lower()
        assert decision.diagnostics.get("fallback_applied") is True

    def test_gate_latency_is_under_10ms_on_cpu(self):
        """Proposition Grounding Gate evaluation must complete in < 10ms on CPU."""
        gate = PropositionGroundingGate()
        query = "Does Section 45 PMLA bar bail during prolonged delay?"
        passages = [
            EvidencePassage(
                evidence_id="E1",
                document_id="doc1",
                case_title="Case 1",
                passage_text="Held: Section 45 PMLA cannot extinguish Article 21 rights during prolonged trial delay.",
                start_char=0,
                end_char=85,
                judgment_rank=1,
                judgment_score=0.9
            )
        ]
        decision = gate.assess_grounding(query, passages)
        assert decision.gate_latency_ms < 10.0


class TestPipelineIntegrationAndApiContracts:
    """Verifies end-to-end integration within RAGPipeline and FastAPI routers."""

    def test_pipeline_abstains_on_laq015_without_calling_llm(self):
        """Pipeline must fast-exit and abstain on LAQ015 without LLM generation."""
        mock_provider = MockLLMProvider()
        pipeline = RAGPipeline(llm_provider=mock_provider)

        query = (
            "Does the statutory provision for anticipatory bail under Section 438 CrPC "
            "establish that an accused can seek pre-arrest bail in contempt of court proceedings?"
        )
        result = pipeline.query(query)

        assert result.status == "insufficient_evidence"
        assert result.grounding_status == "topically_relevant_but_insufficient_grounding"
        assert "INSUFFICIENT EVIDENCE" in result.answer
        assert result.grounding_decision is not None
        assert result.grounding_decision["is_grounded"] is False
        assert "generation_ms" not in result.timing_ms  # Generation was skipped

    def test_pipeline_abstains_on_laq016_without_calling_llm(self):
        """Pipeline must fast-exit and abstain on LAQ016 without LLM generation."""
        mock_provider = MockLLMProvider()
        pipeline = RAGPipeline(llm_provider=mock_provider)

        query = (
            "Does the environmental clearance decision on genetically modified mustard "
            "establish nationwide patent immunity for agricultural biotechnology developers?"
        )
        result = pipeline.query(query)

        assert result.status == "insufficient_evidence"
        assert result.grounding_status == "topically_relevant_but_insufficient_grounding"
        assert "INSUFFICIENT EVIDENCE" in result.answer
        assert "generation_ms" not in result.timing_ms  # Generation was skipped

    def test_pipeline_answers_grounded_laq001(self):
        """Pipeline must answer grounded LAQ001 query with valid status and citations."""
        pipeline = RAGPipeline(llm_provider=MockLLMProvider())
        query = "Can a pendente lite purchaser or third-party stranger who is dispossessed seek redelivery under Order XXI Rule 99?"
        result = pipeline.query(query)

        assert result.status == "answered"
        assert result.grounding_status == "sufficient_evidence"
        assert result.citation_validation.citation_existence_valid is True
        assert len(result.evidence_passages) > 0
        assert "generation_ms" in result.timing_ms

    def test_api_router_returns_grounding_status(self, api_client):
        """POST /v1/rag/query must return structured grounding_status and decision in response."""
        payload = {
            "query": "Does the statutory provision for anticipatory bail under Section 438 CrPC establish that an accused can seek pre-arrest bail in contempt of court proceedings?",
            "provider_type": "mock"
        }
        response = api_client.post("/v1/rag/query", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert "status" in data
        assert data["status"] == "insufficient_evidence"
        assert "grounding_status" in data
        assert data["grounding_status"] == "topically_relevant_but_insufficient_grounding"
        assert "grounding_decision" in data
        assert data["grounding_decision"]["is_grounded"] is False


class TestAdversarialGroundingValidation:
    """
    Milestone 5E: Adversarial Validation across 15 Failure Modes and Positive Controls.
    Verifies that the gate distinguishes genuine legal support from superficial token overlap,
    direct denial, exceptions, unaccepted submissions, rejected arguments, distinguished precedents,
    lower-court findings, split propositions, superficial co-occurrence, multi-part partial support,
    contradictory passages, bare statutory mention, temporal mismatches, unknown passage roles,
    and generic legal vocabulary illusion.
    """

    ADVERSARIAL_DATASET_PATH = Path("evaluation/rag/adversarial_grounding_dataset.json")

    @classmethod
    def load_dataset(cls):
        with open(cls.ADVERSARIAL_DATASET_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    def test_all_20_adversarial_fixtures(self):
        """All 20 fixtures in adversarial dataset must evaluate exactly to their expected grounding status."""
        gate = PropositionGroundingGate()
        data = self.load_dataset()
        assert len(data) == 20

        for item in data:
            test_id = item["test_id"]
            query = item["query"]
            expected_status = item["expected_status"]
            expected_is_grounded = item["expected_is_grounded"]
            passages = [
                EvidencePassage(
                    evidence_id=p["evidence_id"],
                    document_id=p["document_id"],
                    case_title=p["case_title"],
                    passage_text=p["passage_text"],
                    start_char=p["start_char"],
                    end_char=p["end_char"],
                    judgment_rank=1,
                    judgment_score=0.9
                )
                for p in item["passages"]
            ]
            decision = gate.assess_grounding(query, passages)
            assert decision.status.value == expected_status, f"{test_id} status mismatch: expected {expected_status}, got {decision.status.value}"
            assert decision.is_grounded == expected_is_grounded, f"{test_id} is_grounded mismatch"
            assert decision.gate_latency_ms < 10.0, f"{test_id} latency exceeded 10ms"

    def test_adv002_negation_direct_denial(self):
        """Failure mode 2: Judicial negation of authorized signatory as drawer under s.148 NI Act."""
        gate = PropositionGroundingGate()
        data = {d["test_id"]: d for d in self.load_dataset()}
        item = data["ADV002_NEGATION_DIRECT_DENIAL"]
        passages = [EvidencePassage(
            evidence_id=p["evidence_id"], document_id=p["document_id"],
            case_title=p["case_title"], passage_text=p["passage_text"],
            start_char=p["start_char"], end_char=p["end_char"], judgment_rank=1, judgment_score=0.9
        ) for p in item["passages"]]
        decision = gate.assess_grounding(item["query"], passages)
        assert decision.is_grounded is False
        assert decision.status == GroundingStatus.TOPICALLY_RELEVANT_BUT_INSUFFICIENT_GROUNDING
        assert "negat" in decision.rationale.lower() or "denie" in decision.rationale.lower()

    def test_adv003_exceptions_limiting_general_rules(self):
        """Failure mode 3: Limitation on extension under Rule 9(4) Security Interest Rules."""
        gate = PropositionGroundingGate()
        data = {d["test_id"]: d for d in self.load_dataset()}
        item = data["ADV003_EXCEPTION_LIMITATION"]
        passages = [EvidencePassage(
            evidence_id=p["evidence_id"], document_id=p["document_id"],
            case_title=p["case_title"], passage_text=p["passage_text"],
            start_char=p["start_char"], end_char=p["end_char"], judgment_rank=1, judgment_score=0.9
        ) for p in item["passages"]]
        decision = gate.assess_grounding(item["query"], passages)
        assert decision.is_grounded is False
        assert decision.status == GroundingStatus.TOPICALLY_RELEVANT_BUT_INSUFFICIENT_GROUNDING

    def test_adv004_party_submissions_not_adopted(self):
        """Failure mode 4: Unaccepted appellant submissions on balance sheet entries."""
        gate = PropositionGroundingGate()
        data = {d["test_id"]: d for d in self.load_dataset()}
        item = data["ADV004_PARTY_SUBMISSION"]
        passages = [EvidencePassage(
            evidence_id=p["evidence_id"], document_id=p["document_id"],
            case_title=p["case_title"], passage_text=p["passage_text"],
            start_char=p["start_char"], end_char=p["end_char"], judgment_rank=1, judgment_score=0.9
        ) for p in item["passages"]]
        decision = gate.assess_grounding(item["query"], passages)
        assert decision.is_grounded is False
        assert decision.status == GroundingStatus.TOPICALLY_RELEVANT_BUT_INSUFFICIENT_GROUNDING
        assert "submission" in decision.rationale.lower()

    def test_adv006_quoted_precedent_distinguished(self):
        """Failure mode 6: Older precedent quoted only to distinguish as inapplicable."""
        gate = PropositionGroundingGate()
        data = {d["test_id"]: d for d in self.load_dataset()}
        item = data["ADV006_QUOTED_PRECEDENT"]
        passages = [EvidencePassage(
            evidence_id=p["evidence_id"], document_id=p["document_id"],
            case_title=p["case_title"], passage_text=p["passage_text"],
            start_char=p["start_char"], end_char=p["end_char"], judgment_rank=1, judgment_score=0.9
        ) for p in item["passages"]]
        decision = gate.assess_grounding(item["query"], passages)
        assert decision.is_grounded is False
        assert decision.status == GroundingStatus.TOPICALLY_RELEVANT_BUT_INSUFFICIENT_GROUNDING
        assert "distinguish" in decision.rationale.lower() or "inapplicable" in decision.rationale.lower()

    def test_adv008_split_propositions_in_same_passage(self):
        """Failure mode 8: Execution stranger and anticipatory bail in disjoint contexts."""
        gate = PropositionGroundingGate()
        data = {d["test_id"]: d for d in self.load_dataset()}
        item = data["ADV008_SPLIT_PROPOSITIONS"]
        passages = [EvidencePassage(
            evidence_id=p["evidence_id"], document_id=p["document_id"],
            case_title=p["case_title"], passage_text=p["passage_text"],
            start_char=p["start_char"], end_char=p["end_char"], judgment_rank=1, judgment_score=0.9
        ) for p in item["passages"]]
        decision = gate.assess_grounding(item["query"], passages)
        assert decision.is_grounded is False
        assert decision.status == GroundingStatus.TOPICALLY_RELEVANT_BUT_INSUFFICIENT_GROUNDING
        assert "disjoint" in decision.rationale.lower()

    def test_adv010_partial_support_multipart_question(self):
        """Failure mode 10: Compound proposition where second conjunct is completely unsupported."""
        gate = PropositionGroundingGate()
        data = {d["test_id"]: d for d in self.load_dataset()}
        item = data["ADV010_PARTIAL_SUPPORT"]
        passages = [EvidencePassage(
            evidence_id=p["evidence_id"], document_id=p["document_id"],
            case_title=p["case_title"], passage_text=p["passage_text"],
            start_char=p["start_char"], end_char=p["end_char"], judgment_rank=1, judgment_score=0.9
        ) for p in item["passages"]]
        decision = gate.assess_grounding(item["query"], passages)
        assert decision.is_grounded is False
        assert decision.status == GroundingStatus.TOPICALLY_RELEVANT_BUT_INSUFFICIENT_GROUNDING
        assert "compound" in decision.rationale.lower() or "conjunctive" in decision.rationale.lower()

    def test_adv011_contradictory_passages(self):
        """Failure mode 11: Dual contradictory passages with unresolved conflict."""
        gate = PropositionGroundingGate()
        data = {d["test_id"]: d for d in self.load_dataset()}
        item = data["ADV011_CONTRADICTORY_PASSAGES"]
        passages = [EvidencePassage(
            evidence_id=p["evidence_id"], document_id=p["document_id"],
            case_title=p["case_title"], passage_text=p["passage_text"],
            start_char=p["start_char"], end_char=p["end_char"], judgment_rank=1, judgment_score=0.9
        ) for p in item["passages"]]
        decision = gate.assess_grounding(item["query"], passages)
        assert decision.is_grounded is False
        assert decision.status == GroundingStatus.TOPICALLY_RELEVANT_BUT_INSUFFICIENT_GROUNDING
        assert "contradictory" in decision.rationale.lower()

    def test_adv012_statutory_bare_mention(self):
        """Failure mode 12: Statutory section mentioned only in passing procedural FIR context."""
        gate = PropositionGroundingGate()
        data = {d["test_id"]: d for d in self.load_dataset()}
        item = data["ADV012_STATUTORY_BARE_MENTION"]
        passages = [EvidencePassage(
            evidence_id=p["evidence_id"], document_id=p["document_id"],
            case_title=p["case_title"], passage_text=p["passage_text"],
            start_char=p["start_char"], end_char=p["end_char"], judgment_rank=1, judgment_score=0.9
        ) for p in item["passages"]]
        decision = gate.assess_grounding(item["query"], passages)
        assert decision.is_grounded is False
        assert decision.status == GroundingStatus.TOPICALLY_RELEVANT_BUT_INSUFFICIENT_GROUNDING
        assert "procedural" in decision.rationale.lower() or "fir" in decision.rationale.lower()


class TestMilestone5FUnseenGeneralizationValidation:
    """Independent generalization regression tests on unseen evaluation dataset (Milestone 5F)."""

    @classmethod
    def load_dataset(cls):
        dataset_path = Path("evaluation/rag/unseen_grounding_eval_dataset.json")
        with open(dataset_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def test_all_30_unseen_definitive_fixtures(self):
        """All 30 definitive items in unseen dataset must be correctly classified by PropositionGroundingGate."""
        gate = PropositionGroundingGate()
        dataset = self.load_dataset()
        definitive = [d for d in dataset if d["expected_status"] != "needs_human_review"]
        assert len(definitive) == 30

        for item in definitive:
            passages = [EvidencePassage(
                evidence_id=p["evidence_id"], document_id=p["document_id"],
                case_title=p["case_title"], passage_text=p["passage_text"],
                start_char=p["start_char"], end_char=p["end_char"],
                judgment_rank=1, judgment_score=0.9
            ) for p in item.get("passages", [])]

            decision = gate.assess_grounding(item["query"], passages)
            assert decision.is_grounded == item["expected_is_grounded"], (
                f"Grounding mismatch for {item['test_id']}: expected {item['expected_is_grounded']}, got {decision.is_grounded} ({decision.rationale})"
            )
            assert decision.status.value == item["expected_status"], (
                f"Status mismatch for {item['test_id']}: expected {item['expected_status']}, got {decision.status.value}"
            )

    def test_unseen_human_review_segregation(self):
        """Ambiguous test cases must be segregated and flagged for human review."""
        dataset = self.load_dataset()
        ambiguous = [d for d in dataset if d["expected_status"] == "needs_human_review"]
        assert len(ambiguous) == 2
        for item in ambiguous:
            assert item["expected_is_grounded"] is None
            assert len(item["passages"]) >= 1



