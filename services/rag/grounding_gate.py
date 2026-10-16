"""
Proposition Grounding Gate and Content Classification for NyayaVarta RAG (Milestone 5D & 5E).

Distinguishes between:
1. Evidence that is topically relevant to a question.
2. Evidence that directly supports the legal proposition being asked about.
3. Evidence that contradicts, negates, or leaves the proposition unresolved.
4. Questions that cannot safely be answered from the available corpus.

Enforces conservative abstention when evidence shares subject-matter keywords
but fails to establish the specific legal proposition asked about.
Hardened against 15 adversarial grounding failure modes in Milestone 5E.
"""
import re
import time
import logging
from typing import List, Dict, Any, Optional, Set, Tuple
from enum import Enum
from pydantic import BaseModel, Field

from services.rag.models import EvidencePassage

logger = logging.getLogger(__name__)

ROMAN_NUMS = {
    "i": "1", "ii": "2", "iii": "3", "iv": "4", "v": "5",
    "vi": "6", "vii": "7", "viii": "8", "ix": "9", "x": "10",
    "xi": "11", "xii": "12", "xiii": "13", "xiv": "14", "xv": "15",
    "xvi": "16", "xvii": "17", "xviii": "18", "xix": "19", "xx": "20",
    "xxi": "21", "xxii": "22", "xxiii": "23", "xxiv": "24", "xxv": "25"
}
REV_ROMAN = {v: k for k, v in ROMAN_NUMS.items()}

RE_PROV = re.compile(r'\b(section|sec\.|article|art\.|rule|order)\s+([0-9ivxlcdm]+[a-z]?)', re.IGNORECASE)
RE_YEAR = re.compile(r'\b(19[5-9]\d)\b')
RE_CONJ = re.compile(r'\b(?:and\s+simultaneously|and\s+also|as\s+well\s+as)\b', re.IGNORECASE)
RE_ABBR = re.compile(r'\b(art|sec|no|ltd|ors|anr|vs|v|hon|r|or|co|para|dr|mr|mrs)\.', re.IGNORECASE)
RE_SENT_SPLIT = re.compile(r'(?<=[.!?])\s+')
RE_WORDS_3 = re.compile(r'\b[a-z0-9]{3,}\b')
RE_WORDS_4 = re.compile(r'\b[a-z0-9]{4,}\b')
RE_STATUTE_QUOTE = re.compile(r'\b(?:section|article|rule)\s+\d+.*?(?:reads as under|reads as follows|provides that)')
RE_CONTRA_PROHIBIT = re.compile(r'\b(?:strictly\s+non-extendable|mandatory\s+bar|cannot\s+be\s+extended\s+under\s+any\s+circumstances)\b')
RE_CONTRA_EXTEND = re.compile(r'\b(?:is\s+extendable|not\s+absolute[/\s]sacrosanct|extendable\s+with\s+the\s+consent)\b')


class GroundingStatus(str, Enum):
    """Explicit pipeline grounding and abstention states for Milestone 5D & 5E."""
    SUFFICIENT_EVIDENCE = "sufficient_evidence"
    TOPICALLY_RELEVANT_BUT_INSUFFICIENT_GROUNDING = "topically_relevant_but_insufficient_grounding"
    NO_RELEVANT_EVIDENCE = "no_relevant_evidence"
    GROUNDING_CHECK_UNAVAILABLE = "grounding_check_unavailable"
    GENERATION_FAILED = "generation_failed"
    VALIDATION_FAILED = "validation_failed"


class PassageContentType(str, Enum):
    """Classification of judicial text segments."""
    HOLDING = "court_holding"
    SUBMISSION = "party_submission"
    FACTS_OR_PROCEDURAL = "facts_or_procedural"
    LOWER_COURT_REASONING = "lower_court_reasoning"
    QUOTED_PRECEDENT = "quoted_precedent"
    STATUTORY_TEXT = "statutory_text"
    UNKNOWN = "unknown"


class GroundingDecision(BaseModel):
    """Detailed audit decision emitted by the Proposition Grounding Gate."""
    status: GroundingStatus
    is_grounded: bool = Field(..., description="True if evidence is sufficient to answer the proposition")
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Heuristic grounding confidence")
    provisions_required: List[str] = Field(default_factory=list)
    provisions_found: List[str] = Field(default_factory=list)
    missing_provisions: List[str] = Field(default_factory=list)
    facets_detected: List[Dict[str, Any]] = Field(default_factory=list)
    missing_facets: List[str] = Field(default_factory=list)
    content_classifications: List[Dict[str, Any]] = Field(default_factory=list)
    has_holding_or_authoritative_support: bool = Field(default=False)
    rationale: str = Field(default="")
    gate_latency_ms: float = Field(default=0.0)
    diagnostics: Dict[str, Any] = Field(default_factory=dict)


class PropositionGroundingGate:
    """
    Proposition-grounding gate placed between retrieval/evidence assembly
    and answer generation to prevent false answers on topically related but ungrounded queries.
    Hardened against 15 adversarial grounding failure modes.
    """

    GENERIC_LEGAL_WORDS = {
        "what", "where", "when", "which", "who", "does", "did", "would", "could", "should",
        "shall", "about", "these", "those", "their", "there", "having", "being", "under",
        "between", "against", "cannot", "court", "courts", "supreme", "judgment", "judgments",
        "bench", "benches", "order", "orders", "held", "stated", "case", "cases", "learned",
        "counsel", "matter", "matters", "passed", "versus", "state", "union", "india", "decision",
        "decisions", "trial", "appellant", "respondent", "appeal", "appeals", "petition",
        "petitions", "writ", "writs", "digital", "reports", "indian", "para", "paras", "record",
        "with", "from", "into", "such", "also", "only", "other", "some", "same", "view",
        "provide", "provides", "require", "required", "requirements", "whether", "accordance",
        "stand", "standard", "standards", "principle", "principles", "provisions", "provision",
        "can", "person", "persons", "application", "proceedings", "proceeding", "rule", "rules",
        "section", "sections", "article", "articles", "act", "acts", "and", "for", "the", "are", "is",
        "a", "an", "to", "of", "in", "by", "its", "accused", "accuseds", "arrest", "arrests", "seek",
        "seeks", "sought", "during", "before", "after", "while", "upon", "that", "this",
        "pre", "per", "via", "sub", "criminal", "suit", "civil", "matter", "terms",
        "procedure", "procedures", "jurisdiction", "exercise", "authority",
        "judge", "judges", "code", "codes", "constitution", "constitutional"
    }

    LEGAL_LEMMA_CLUSTERS = [
        {"grant", "granting", "grants", "granted", "entitled", "entitlement"},
        {"labor", "labour", "work", "tasks", "task", "job", "jobs"},
        {"allocate", "allocating", "allocation", "allot", "allots", "allotting", "allotted", "delegation", "assign", "assigning"},
        {"unconstitutional", "violative", "invalid", "illegality", "unlawful"},
        {"prolonged", "long", "delay", "delayed"},
        {"incarceration", "custody", "imprisonment", "detention", "jail"},
        {"maintain", "maintaining", "maintainable", "maintainability", "file", "filing", "filed", "institute", "instituting", "instituted"},
        {"dispossessed", "dispossession", "eviction", "redelivery"},
        {"possession", "possess", "possessing"},
        {"cheque", "cheques"},
        {"signatory", "signatories", "signs"},
        {"drawer", "drawers"},
        {"compensation", "compensate", "fine"},
        {"admission", "admissions", "admit", "admitted"},
        {"witness", "witnesses"},
        {"reversal", "reversing", "reverse", "interfere", "interference"},
        {"acquittal", "acquittals", "acquitted"},
        {"circumstantial", "circumstances"},
        {"article", "art"},
        {"section", "sec"},
        {"power", "powers"},
        {"disclaimer", "disclaim", "disclaimed", "disclaims", "caveat", "caveats", "qualification", "qualifications", "reservation", "reservations", "notes"},
        {"denial", "denying", "denies", "denied", "dispute", "disputing", "disputed"}
    ]

    LEMMA_MAP: Dict[str, Set[str]] = {}
    for _cluster in LEGAL_LEMMA_CLUSTERS:
        for _w in _cluster:
            LEMMA_MAP[_w] = _cluster

    RELATIONAL_VERBS = [
        r'\bestablish\s+that\b', r'\bestablish\b', r'\bestablishes\b',
        r'\bautomatically\s+bar\b', r'\bbar\b', r'\bbars\b',
        r'\bpermit\b', r'\bpermits\b',
        r'\ballow\b', r'\ballows\b',
        r'\bconfer\b', r'\bconfers\b',
        r'\bgrant\b', r'\bgrants\b',
        r'\bapply\s+to\b', r'\bapplies\s+to\b',
        r'\bextend\s+limitation\b', r'\bextends\s+limitation\b',
        r'\bextend\s+to\b', r'\bextends\s+to\b',
        r'\bextend\b', r'\bextends\b',
        r'\bconstitute\b', r'\bconstitutes\b',
        r'\bpossess\s+jurisdiction\b',
        r'\bvitiate\b', r'\bvitiates\b',
        r'\bdeprive\b', r'\bdeprives\b',
        r'\bseek\b', r'\bseeks\b',
        r'\binvalidate\b', r'\binvalidates\b',
        r'\bformulate\b', r'\bformulates\b',
        r'\bformulated\b',
        r'\boverride\b', r'\boverrides\b',
        r'\bdispense\s+with\b', r'\bdispenses\s+with\b',
        r'\bprevail\s+over\b', r'\bprevails\s+over\b',
        r'\bsupersede\b', r'\bsupersedes\b',
        r'\bfollow\b.*?\bto\s+hold\b'
    ]
    REL_PATTERN = re.compile('|'.join(RELATIONAL_VERBS), re.IGNORECASE)

    HOLDING_MARKERS = [
        "we hold that", "we are of the considered view", "in our considered opinion",
        "we find that", "it is well settled that", "held:", "held :", "conclusion:",
        "we conclude that", "we have no hesitation in holding", "we are of the view",
        "analysis, reasoning and conclusion", "the question is answered in the",
        "it is manifest that", "we are in agreement with", "it is held that", "this court held"
    ]

    SUBMISSION_MARKERS = [
        "learned counsel for the appellant submitted", "learned senior counsel argued",
        "contended that", "appellant submitted", "respondent urged", "it was contended",
        "submission of the learned", "on behalf of the petitioner", "counsel for the respondent argued",
        "it was submitted that", "learned asg submitted", "learned solicitor general contended"
    ]

    FACT_PROCEDURAL_MARKERS = [
        "the brief facts of the case", "the complainant filed", "the appellant was arrested",
        "the high court by the impugned order", "the trial court convicted",
        "an fir was registered", "charge sheet was submitted", "the appellant challenged the order",
        "the writ petition was filed", "facts leading to the filing"
    ]

    LOWER_COURT_MARKERS = [
        "the high court observed", "the high court held", "the trial court found",
        "the sessions judge held", "the division bench noted", "the impugned judgment of the high court"
    ]

    NEG_PATTERNS = [
        r'\b(?:we\s+reject|rejects|rejected\s+the\s+submission|repelled|repudiated|devoid\s+of\s+merit|cannot\s+be\s+accepted|misconceived|fallacious)\b',
        r'\b(?:will\s+not\s+make|does\s+not\s+make|shall\s+not\s+make|not\s+make)\b',
        r'\b(?:does\s+not\s+lie|cannot\s+lie|does\s+not\s+arise|will\s+not\s+lie)\b',
        r'\b(?:cannot\s+be\s+granted|cannot\s+be\s+directed|could\s+not\s+place\s+a\s+condition|cannot\s+place\s+a\s+condition)\b',
        r'\b(?:not\s+entitled|not\s+permissible|impermissible|no\s+right\s+to|no\s+entitlement|no\s+unilateral\s+right|unilateral\s+demand.*?does\s+not\s+confer)\b',
        r'\b(?:inapplicable|does\s+not\s+apply|will\s+not\s+apply|has\s+no\s+application|cannot\s+apply)\b',
        r'\b(?:cannot\s+be\s+extended|cannot\s+be\s+equated|not\s+open\s+to|not\s+maintainable|cannot\s+maintain)\b',
        r'\b(?:differentiated|distinguished\s+and\s+has\s+no\s+application)\b',
        r'\b(?:not\s+absolute[/\s]sacrosanct)\b'
    ]
    NEG_REGEX = re.compile('|'.join(NEG_PATTERNS), re.IGNORECASE)

    def __init__(self, min_concept_coverage: float = 0.45):
        self.min_concept_coverage = min_concept_coverage

    @classmethod
    def split_sentences(cls, text: str) -> List[str]:
        """Split text into sentences while protecting periods in common legal abbreviations."""
        if not text:
            return []
        protected = RE_ABBR.sub(r'\1_DOT_', text)
        parts = RE_SENT_SPLIT.split(protected)
        return [p.replace('_DOT_', '.') for p in parts if p.strip()]

    @classmethod
    def lemma_matches(cls, word1: str, word2: str) -> bool:
        """Check if two words are identical or share a recognized legal lemma cluster."""
        w1, w2 = word1.lower(), word2.lower()
        if w1 == w2:
            return True
        cluster1 = cls.LEMMA_MAP.get(w1)
        return bool(cluster1 and w2 in cluster1)

    @classmethod
    def term_in_text(cls, term: str, text_lower: str) -> bool:
        """Check if a term or any lemma variant is present in text."""
        tl = term.lower()
        if tl in text_lower:
            return True
        if len(tl) > 3 and tl.endswith('s') and tl[:-1] in text_lower:
            return True
        if len(tl) > 4 and tl.endswith('es') and tl[:-2] in text_lower:
            return True
        cluster = cls.LEMMA_MAP.get(tl)
        if cluster:
            for w in cluster:
                if w in text_lower:
                    return True
                if len(w) > 3 and w.endswith('s') and w[:-1] in text_lower:
                    return True
        return False

    @classmethod
    def term_in_words(cls, term: str, words_set: Set[str], text_lower: str) -> bool:
        """Fast check if a term or any lemma variant is present in pre-tokenized words_set or text_lower."""
        tl = term.lower()
        if tl in words_set or tl in text_lower:
            return True
        if len(tl) > 3 and tl.endswith('s') and (tl[:-1] in words_set or tl[:-1] in text_lower):
            return True
        if len(tl) > 4 and tl.endswith('es') and (tl[:-2] in words_set or tl[:-2] in text_lower):
            return True
        cluster = cls.LEMMA_MAP.get(tl)
        if cluster:
            if bool(cluster & words_set):
                return True
            for w in cluster:
                if w in text_lower:
                    return True
                if len(w) > 3 and w.endswith('s') and (w[:-1] in words_set or w[:-1] in text_lower):
                    return True
        return False

    @classmethod
    def classify_passage_content(cls, text: str) -> Dict[str, Any]:
        """
        Bounded prototype classifying passage text into structural judgment roles.
        If indicators are absent or mixed, explicitly returns 'unknown' without fabricating.
        """
        if not text or not text.strip():
            return {
                "content_type": PassageContentType.UNKNOWN.value,
                "confidence": 0.0,
                "indicators": []
            }

        t_lower = text.lower()
        matched_holding = [m for m in cls.HOLDING_MARKERS if m in t_lower]
        matched_submission = [m for m in cls.SUBMISSION_MARKERS if m in t_lower]
        matched_facts = [m for m in cls.FACT_PROCEDURAL_MARKERS if m in t_lower]
        matched_lower = [m for m in cls.LOWER_COURT_MARKERS if m in t_lower]

        if any(qp in t_lower for qp in ["relied upon", "differentiated", "has no application"]):
            if "has no application" in t_lower or "differentiated" in t_lower:
                return {
                    "content_type": PassageContentType.QUOTED_PRECEDENT.value,
                    "confidence": 0.80,
                    "indicators": ["quoted_precedent_distinguished"]
                }

        if any(h in t_lower for h in ["held:", "held :", "we hold that", "in our considered view", "conclusion:"]):
            return {
                "content_type": PassageContentType.HOLDING.value,
                "confidence": 0.85,
                "indicators": matched_holding or ["held:"]
            }

        if matched_holding and not matched_submission and not matched_lower:
            return {
                "content_type": PassageContentType.HOLDING.value,
                "confidence": 0.85,
                "indicators": matched_holding
            }

        if matched_submission and not matched_holding:
            return {
                "content_type": PassageContentType.SUBMISSION.value,
                "confidence": 0.80,
                "indicators": matched_submission
            }

        if matched_lower and not matched_holding:
            return {
                "content_type": PassageContentType.LOWER_COURT_REASONING.value,
                "confidence": 0.80,
                "indicators": matched_lower
            }

        if matched_facts and not matched_holding:
            return {
                "content_type": PassageContentType.FACTS_OR_PROCEDURAL.value,
                "confidence": 0.70,
                "indicators": matched_facts
            }

        if RE_STATUTE_QUOTE.search(t_lower):
            return {
                "content_type": PassageContentType.STATUTORY_TEXT.value,
                "confidence": 0.80,
                "indicators": ["statutory_verbatim_quote"]
            }

        if any(h in t_lower for h in ["issue for consideration", "headnotes"]):
            return {
                "content_type": PassageContentType.HOLDING.value,
                "confidence": 0.65,
                "indicators": ["headnotes_or_issue_formulation"]
            }

        return {
            "content_type": PassageContentType.UNKNOWN.value,
            "confidence": 0.0,
            "indicators": []
        }

    def assess_grounding(
        self,
        query: str,
        evidence_passages: List[EvidencePassage]
    ) -> GroundingDecision:
        """
        Assess whether the retrieved evidence genuinely supports the legal proposition
        or is merely topically relevant.
        """
        t0 = time.perf_counter()

        try:
            # 1. No evidence check
            if not evidence_passages:
                elapsed = round((time.perf_counter() - t0) * 1000.0, 3)
                return GroundingDecision(
                    status=GroundingStatus.NO_RELEVANT_EVIDENCE,
                    is_grounded=False,
                    confidence_score=0.0,
                    rationale="No qualifying evidence passages found in retrieved judgments.",
                    gate_latency_ms=elapsed
                )

            all_evidence_text = "\n".join(ep.passage_text for ep in evidence_passages).lower()

            # 2. Statutory anchor check with Indian citation abbreviations & roman conversion
            provs = RE_PROV.findall(query)
            req_provisions = [f"{p[0].title()} {p[1].upper()}" for p in provs]
            found_provisions = []
            missing_provisions = []

            for p_type, p_num in provs:
                p_type_l = p_type.lower()
                p_num_l = p_num.lower()
                num_variants = [p_num_l]
                if p_num_l in ROMAN_NUMS:
                    num_variants.append(ROMAN_NUMS[p_num_l])
                elif p_num_l in REV_ROMAN:
                    num_variants.append(REV_ROMAN[p_num_l])

                found = False
                for nv in num_variants:
                    patterns = [
                        rf'\b{p_type_l}\s+{nv}\b',
                        rf'\b{p_type_l}\.\s*{nv}\b'
                    ]
                    if p_type_l in ["section", "sec."]:
                        patterns.extend([
                            rf'\bs\.{nv}\b', rf'\bs\.\s*{nv}\b', rf'\bsec\.{nv}\b', rf'\bsection\s+{nv}\s+of\b', rf'\bu/s\s+{nv}\b',
                            rf'\bsections\b[^\.\n;]{{1,35}}\b{nv}\b', rf'\bss\.\s*[^\.\n;]{{1,35}}\b{nv}\b'
                        ])
                    elif p_type_l in ["article", "art."]:
                        patterns.extend([
                            rf'\bart\.{nv}\b', rf'\bart\.\s*{nv}\b', rf'\bart\s+{nv}\b', rf'\bu/art\.{nv}\b',
                            rf'\barticles\b[^\.\n;]{{1,35}}\b{nv}\b'
                        ])
                    elif p_type_l == "order":
                        patterns.extend([rf'\bor\.{nv}\b', rf'\bor\.\s*{nv}\b', rf'\bo\.{nv}\b', rf'\bo\.\s*{nv}\b'])
                    elif p_type_l == "rule":
                        patterns.extend([
                            rf'\br\.{nv}\b', rf'\br\.\s*{nv}\b', rf'\brule\.{nv}\b',
                            rf'\brules\b[^\.\n;]{{1,35}}\b{nv}\b'
                        ])

                    for pat in patterns:
                        if re.search(pat, all_evidence_text):
                            found = True
                            break
                    if found:
                        break

                p_norm = f"{p_type.title()} {p_num.upper()}"
                if found:
                    found_provisions.append(p_norm)
                else:
                    missing_provisions.append(p_norm)

            is_conflict_query = bool(re.search(r'\b(override|overrides|dispense\s+with|dispenses\s+with|prevail\s+over|prevails\s+over|supersede|supersedes)\b', query, re.IGNORECASE))
            if req_provisions and missing_provisions and (len(found_provisions) == 0 or is_conflict_query):
                elapsed = round((time.perf_counter() - t0) * 1000.0, 3)
                return GroundingDecision(
                    status=GroundingStatus.TOPICALLY_RELEVANT_BUT_INSUFFICIENT_GROUNDING,
                    is_grounded=False,
                    confidence_score=0.1,
                    provisions_required=req_provisions,
                    provisions_found=found_provisions,
                    missing_provisions=missing_provisions,
                    rationale=f"Query explicitly inquires about statutory provisions ({', '.join(missing_provisions)}), but they are not present in retrieved evidence.",
                    gate_latency_ms=elapsed
                )

            # Check bare statutory mention in FIR/charges without legal interpretation
            if req_provisions and len(req_provisions) == len(found_provisions):
                is_only_fir_mention = True
                for ep in evidence_passages:
                    epl = ep.passage_text.lower()
                    if any(term in epl for term in ["held:", "we hold", "interpretation", "scope of", "meaning of", "liability", "standard", "test"]):
                        is_only_fir_mention = False
                        break
                if is_only_fir_mention and any(q_kw in query.lower() for q_kw in ["standard", "alter ego", "test", "interpretation", "doctrine"]):
                    elapsed = round((time.perf_counter() - t0) * 1000.0, 3)
                    return GroundingDecision(
                        status=GroundingStatus.TOPICALLY_RELEVANT_BUT_INSUFFICIENT_GROUNDING,
                        is_grounded=False,
                        confidence_score=0.2,
                        provisions_required=req_provisions,
                        provisions_found=found_provisions,
                        missing_provisions=[],
                        rationale=f"Statutory provision ({', '.join(req_provisions)}) appears only in passing procedural context (e.g. FIR/charges) without judicial interpretation of the inquired legal standard.",
                        gate_latency_ms=elapsed
                    )

            # Check focal historical years (e.g. 1970 Patents Act, 1973 Kesavananda)
            years = RE_YEAR.findall(query)
            for y in years:
                if not re.search(rf'\b{y}\b', all_evidence_text):
                    elapsed = round((time.perf_counter() - t0) * 1000.0, 3)
                    return GroundingDecision(
                        status=GroundingStatus.TOPICALLY_RELEVANT_BUT_INSUFFICIENT_GROUNDING,
                        is_grounded=False,
                        confidence_score=0.15,
                        provisions_required=req_provisions,
                        provisions_found=found_provisions,
                        missing_provisions=missing_provisions,
                        rationale=f"Historical precedent or statutory year ({y}) specified in query is absent from retrieved 2024 judgments.",
                        gate_latency_ms=elapsed
                    )

            # 3. Content classification of evidence passages
            classifications = []
            has_holding = False
            for ep in evidence_passages:
                cls_info = self.classify_passage_content(ep.passage_text)
                s_label = getattr(ep, "structural_label", None)
                if s_label == "party_submissions":
                    # Party submissions must never be classified as holding
                    cls_info = {
                        "content_type": PassageContentType.SUBMISSION.value,
                        "confidence": getattr(ep, "structural_confidence", 0.85) or 0.85,
                        "indicators": ["structural_party_submissions"]
                    }
                elif cls_info["content_type"] == PassageContentType.UNKNOWN.value and s_label:
                    if s_label in ["headnote_holding", "judicial_holding"]:
                        cls_info = {
                            "content_type": PassageContentType.HOLDING.value,
                            "confidence": getattr(ep, "structural_confidence", 0.85) or 0.85,
                            "indicators": [f"structural_{s_label}"]
                        }
                    elif s_label == "court_analysis":
                        cls_info = {
                            "content_type": PassageContentType.HOLDING.value,
                            "confidence": getattr(ep, "structural_confidence", 0.75) or 0.75,
                            "indicators": ["structural_court_analysis"]
                        }
                    elif s_label == "statutory_context":
                        cls_info = {
                            "content_type": PassageContentType.STATUTORY_TEXT.value,
                            "confidence": getattr(ep, "structural_confidence", 0.80) or 0.80,
                            "indicators": ["structural_statutory_context"]
                        }
                    elif s_label == "facts_procedural":
                        cls_info = {
                            "content_type": PassageContentType.FACTS_OR_PROCEDURAL.value,
                            "confidence": getattr(ep, "structural_confidence", 0.70) or 0.70,
                            "indicators": ["structural_facts_procedural"]
                        }

                classifications.append({
                    "evidence_id": ep.evidence_id,
                    "document_id": ep.document_id,
                    "content_type": cls_info["content_type"],
                    "confidence": cls_info["confidence"],
                    "indicators": cls_info["indicators"]
                })
                if cls_info["content_type"] in [PassageContentType.HOLDING.value, PassageContentType.STATUTORY_TEXT.value]:
                    has_holding = True

            all_submissions = all(c["content_type"] == PassageContentType.SUBMISSION.value for c in classifications)
            if all_submissions and len(classifications) >= 1:
                elapsed = round((time.perf_counter() - t0) * 1000.0, 3)
                return GroundingDecision(
                    status=GroundingStatus.TOPICALLY_RELEVANT_BUT_INSUFFICIENT_GROUNDING,
                    is_grounded=False,
                    confidence_score=0.2,
                    provisions_required=req_provisions,
                    provisions_found=found_provisions,
                    missing_provisions=missing_provisions,
                    content_classifications=classifications,
                    has_holding_or_authoritative_support=False,
                    rationale="Retrieved passages contain only party/counsel submissions and do not contain judicial reasoning or holding.",
                    gate_latency_ms=elapsed,
                    diagnostics={"all_submissions": True}
                )

            all_lower_court = all(c["content_type"] == PassageContentType.LOWER_COURT_REASONING.value for c in classifications)
            if all_lower_court and len(classifications) >= 1:
                elapsed = round((time.perf_counter() - t0) * 1000.0, 3)
                return GroundingDecision(
                    status=GroundingStatus.TOPICALLY_RELEVANT_BUT_INSUFFICIENT_GROUNDING,
                    is_grounded=False,
                    confidence_score=0.2,
                    provisions_required=req_provisions,
                    provisions_found=found_provisions,
                    missing_provisions=missing_provisions,
                    content_classifications=classifications,
                    has_holding_or_authoritative_support=False,
                    rationale="Retrieved passages describe only lower-court reasoning or observations and lack deciding court holding or ratio decidendi.",
                    gate_latency_ms=elapsed,
                    diagnostics={"all_lower_court": True}
                )

            all_quoted_distinguished = all(c["content_type"] == PassageContentType.QUOTED_PRECEDENT.value for c in classifications)
            if all_quoted_distinguished and len(classifications) >= 1:
                elapsed = round((time.perf_counter() - t0) * 1000.0, 3)
                return GroundingDecision(
                    status=GroundingStatus.TOPICALLY_RELEVANT_BUT_INSUFFICIENT_GROUNDING,
                    is_grounded=False,
                    confidence_score=0.2,
                    provisions_required=req_provisions,
                    provisions_found=found_provisions,
                    missing_provisions=missing_provisions,
                    content_classifications=classifications,
                    has_holding_or_authoritative_support=False,
                    rationale="Retrieved passages cite older precedent only to distinguish or declare it inapplicable to the controversy.",
                    gate_latency_ms=elapsed,
                    diagnostics={"all_quoted_distinguished": True}
                )

            # 4. Check for unresolved contradictory passages
            if len(evidence_passages) >= 2:
                has_absolute_prohibition = any(RE_CONTRA_PROHIBIT.search(ep.passage_text.lower()) for ep in evidence_passages)
                has_extendable_holding = any(RE_CONTRA_EXTEND.search(ep.passage_text.lower()) for ep in evidence_passages)
                if has_absolute_prohibition and has_extendable_holding:
                    elapsed = round((time.perf_counter() - t0) * 1000.0, 3)
                    return GroundingDecision(
                        status=GroundingStatus.TOPICALLY_RELEVANT_BUT_INSUFFICIENT_GROUNDING,
                        is_grounded=False,
                        confidence_score=0.25,
                        provisions_required=req_provisions,
                        provisions_found=found_provisions,
                        missing_provisions=missing_provisions,
                        content_classifications=classifications,
                        has_holding_or_authoritative_support=has_holding,
                        rationale="Retrieved passages contain unresolved contradictory propositions regarding the requested legal rule.",
                        gate_latency_ms=elapsed,
                        diagnostics={"contradiction_detected": True}
                    )

            # 5. Multi-Part / Conjunctive Compound Proposition Check
            conj_match = RE_CONJ.split(query)
            if len(conj_match) >= 2:
                second_part = conj_match[1]
                second_terms = set(w.lower() for w in RE_WORDS_4.findall(second_part) if w.lower() not in self.GENERIC_LEGAL_WORDS)
                if second_terms:
                    covered_second = [w for w in second_terms if self.term_in_text(w, all_evidence_text)]
                    if len(covered_second) == 0:
                        elapsed = round((time.perf_counter() - t0) * 1000.0, 3)
                        return GroundingDecision(
                            status=GroundingStatus.TOPICALLY_RELEVANT_BUT_INSUFFICIENT_GROUNDING,
                            is_grounded=False,
                            confidence_score=0.3,
                            provisions_required=req_provisions,
                            provisions_found=found_provisions,
                            missing_provisions=missing_provisions,
                            content_classifications=classifications,
                            has_holding_or_authoritative_support=has_holding,
                            rationale=f"Query contains compound multi-part propositions, but evidence completely lacks grounding for conjunctive elements: {list(second_terms)}.",
                            gate_latency_ms=elapsed,
                            diagnostics={"compound_conjunct_missing": list(second_terms)}
                        )

            # 5b. Multi-Part / Statutory Test and Exception Component Sufficiency (Milestone 8 Task 3)
            # Detect if query explicitly inquires about a specific legal/statutory test, exception, or multi-factor standard
            test_patterns = [
                r'\b([a-z0-9\-]+)\s+test\b',
                r'\b(functionality\s+test)\b',
                r'\b(triple\s+test)\b',
                r'\b(prima\s+facie\s+test)\b'
            ]
            inquired_tests = []
            for t_pat in test_patterns:
                m_tests = re.findall(t_pat, query.lower())
                for mt in m_tests:
                    if mt not in self.GENERIC_LEGAL_WORDS and mt not in {"the", "a", "an", "this", "that"}:
                        inquired_tests.append(mt)

            if inquired_tests:
                for test_name in inquired_tests:
                    test_str = test_name if "test" in test_name else f"{test_name} test"
                    if not self.term_in_text(test_name, all_evidence_text):
                        elapsed = round((time.perf_counter() - t0) * 1000.0, 3)
                        return GroundingDecision(
                            status=GroundingStatus.TOPICALLY_RELEVANT_BUT_INSUFFICIENT_GROUNDING,
                            is_grounded=False,
                            confidence_score=0.2,
                            provisions_required=req_provisions,
                            provisions_found=found_provisions,
                            missing_provisions=missing_provisions,
                            content_classifications=classifications,
                            has_holding_or_authoritative_support=has_holding,
                            rationale=f"Query explicitly inquires about a specific statutory/legal test ('{test_str}'), but the test is not present or discussed in the active evidence passages.",
                            gate_latency_ms=elapsed,
                            diagnostics={"missing_inquired_test": test_str}
                        )

            # Pre-tokenize sentences and word sets once for remaining structural checks
            sentences_data = []
            for ep in evidence_passages:
                for s in self.split_sentences(ep.passage_text):
                    sl = s.lower()
                    swords = set(RE_WORDS_3.findall(sl))
                    sentences_data.append((s, sl, swords))

            # 6. Relational Proposition Decomposition
            parts = self.REL_PATTERN.split(query, maxsplit=1)
            if len(parts) == 2:
                subj, prop = parts[0], parts[1]
                subj_terms = set(w for w in RE_WORDS_4.findall(subj.lower()) if w not in self.GENERIC_LEGAL_WORDS)
                if not subj_terms:
                    subj_terms = set(w for w in RE_WORDS_3.findall(subj.lower()) if w not in {"the", "and", "for", "can", "does", "did"})
                for p_type, p_num in provs:
                    if p_num.lower() in subj.lower():
                        subj_terms.add(p_num.lower())
                prop_terms = set(w for w in RE_WORDS_4.findall(prop.lower()) if w not in self.GENERIC_LEGAL_WORDS)

                distinct_prop = prop_terms - subj_terms
                if not distinct_prop:
                    distinct_prop = prop_terms

                covered_prop = [w for w in distinct_prop if self.term_in_text(w, all_evidence_text)]
                prop_coverage = len(covered_prop) / len(distinct_prop) if distinct_prop else 0.0

                if not covered_prop or prop_coverage < 0.40:
                    missing_prop = [w for w in distinct_prop if not self.term_in_text(w, all_evidence_text)]
                    elapsed = round((time.perf_counter() - t0) * 1000.0, 3)
                    return GroundingDecision(
                        status=GroundingStatus.TOPICALLY_RELEVANT_BUT_INSUFFICIENT_GROUNDING,
                        is_grounded=False,
                        confidence_score=0.2,
                        provisions_required=req_provisions,
                        provisions_found=found_provisions,
                        missing_provisions=missing_provisions,
                        content_classifications=classifications,
                        has_holding_or_authoritative_support=has_holding,
                        rationale=f"Retrieved passages discuss antecedent subject matter, but completely lack grounding for target proposition elements: {missing_prop}.",
                        gate_latency_ms=elapsed,
                        diagnostics={"prop_coverage": prop_coverage, "missing_prop": missing_prop}
                    )

                # Check if distinctive target predicate is directly negated by court
                predicate_negated = False
                for s, sl, swords in sentences_data:
                    if self.NEG_REGEX.search(sl):
                        p_matches = [w for w in distinct_prop if self.term_in_words(w, swords, sl)]
                        if len(p_matches) >= 3:
                            predicate_negated = True
                            break

                if predicate_negated:
                    elapsed = round((time.perf_counter() - t0) * 1000.0, 3)
                    return GroundingDecision(
                        status=GroundingStatus.TOPICALLY_RELEVANT_BUT_INSUFFICIENT_GROUNDING,
                        is_grounded=False,
                        confidence_score=0.25,
                        provisions_required=req_provisions,
                        provisions_found=found_provisions,
                        missing_provisions=missing_provisions,
                        content_classifications=classifications,
                        has_holding_or_authoritative_support=has_holding,
                        rationale="Retrieved evidence explicitly negates, limits, or denies the requested proposition (negative holding or exception detected).",
                        gate_latency_ms=elapsed,
                        diagnostics={"predicate_negated": True}
                    )

                # Check localized sentence co-occurrence AND negation/rejection
                co_occurred = False
                affirmative_co_occurred = False
                all_co_occurrences_negated = True

                if subj_terms:
                    for s, sl, swords in sentences_data:
                        if not any(self.term_in_words(w, swords, sl) for w in subj_terms):
                            continue
                        pm = [w for w in distinct_prop if self.term_in_words(w, swords, sl)]
                        has_prop = len(pm) >= 2 or (len(pm) >= 1 and len(distinct_prop) <= 2)
                        if has_prop:
                            co_occurred = True
                            is_negated = bool(self.NEG_REGEX.search(sl))
                            if not is_negated:
                                affirmative_co_occurred = True
                                all_co_occurrences_negated = False

                    if not co_occurred:
                        elapsed = round((time.perf_counter() - t0) * 1000.0, 3)
                        return GroundingDecision(
                            status=GroundingStatus.TOPICALLY_RELEVANT_BUT_INSUFFICIENT_GROUNDING,
                            is_grounded=False,
                            confidence_score=0.3,
                            provisions_required=req_provisions,
                            provisions_found=found_provisions,
                            missing_provisions=missing_provisions,
                            content_classifications=classifications,
                            has_holding_or_authoritative_support=has_holding,
                            rationale=f"Subject context ({subj_terms}) and target predicate ({distinct_prop}) appear only in disjoint contexts and do not co-occur in any evidence sentence.",
                            gate_latency_ms=elapsed,
                            diagnostics={"co_occurred": False}
                        )

                    # If ALL co-occurring sentences explicitly negate or reject the proposition
                    if co_occurred and all_co_occurrences_negated and not affirmative_co_occurred:
                        elapsed = round((time.perf_counter() - t0) * 1000.0, 3)
                        return GroundingDecision(
                            status=GroundingStatus.TOPICALLY_RELEVANT_BUT_INSUFFICIENT_GROUNDING,
                            is_grounded=False,
                            confidence_score=0.25,
                            provisions_required=req_provisions,
                            provisions_found=found_provisions,
                            missing_provisions=missing_provisions,
                            content_classifications=classifications,
                            has_holding_or_authoritative_support=has_holding,
                            rationale="Retrieved evidence explicitly negates, rejects, or holds the proposition inapplicable (negative holding/rejection detected), and therefore cannot support the affirmative proposition.",
                            gate_latency_ms=elapsed,
                            diagnostics={"negation_detected": True}
                        )

            # 7. Salient Vocabulary Coverage Check with Lemma Matching
            q_terms = set(w for w in RE_WORDS_4.findall(query.lower()) if w not in self.GENERIC_LEGAL_WORDS)
            covered_terms = [w for w in q_terms if self.term_in_text(w, all_evidence_text)]
            vocab_ratio = len(covered_terms) / len(q_terms) if q_terms else 0.0

            if vocab_ratio < self.min_concept_coverage:
                missing_terms = [w for w in q_terms if not self.term_in_text(w, all_evidence_text)]
                elapsed = round((time.perf_counter() - t0) * 1000.0, 3)
                return GroundingDecision(
                    status=GroundingStatus.TOPICALLY_RELEVANT_BUT_INSUFFICIENT_GROUNDING,
                    is_grounded=False,
                    confidence_score=0.25,
                    provisions_required=req_provisions,
                    provisions_found=found_provisions,
                    missing_provisions=missing_provisions,
                    content_classifications=classifications,
                    has_holding_or_authoritative_support=has_holding,
                    rationale=f"Overall topical evidence coverage ({vocab_ratio:.2f}) is below minimum grounding threshold. Missing concepts: {missing_terms[:5]}.",
                    gate_latency_ms=elapsed,
                    diagnostics={"vocab_ratio": vocab_ratio, "missing_terms": missing_terms}
                )

            # 8. Check for lack of authoritative judicial holding or unverified passage roles only
            all_unknown = all(c["content_type"] == PassageContentType.UNKNOWN.value for c in classifications)
            if all_unknown and len(classifications) >= 1:
                elapsed = round((time.perf_counter() - t0) * 1000.0, 3)
                return GroundingDecision(
                    status=GroundingStatus.TOPICALLY_RELEVANT_BUT_INSUFFICIENT_GROUNDING,
                    is_grounded=False,
                    confidence_score=0.15,
                    provisions_required=req_provisions,
                    provisions_found=found_provisions,
                    missing_provisions=missing_provisions,
                    content_classifications=classifications,
                    has_holding_or_authoritative_support=False,
                    rationale="Retrieved passages lack authoritative judicial holding or ratio decidendi (evidentiary exhibits or unverified passage roles only).",
                    gate_latency_ms=elapsed,
                    diagnostics={"all_unknown": True}
                )

            # 9. All checks passed: genuine holding support
            elapsed = round((time.perf_counter() - t0) * 1000.0, 3)
            return GroundingDecision(
                status=GroundingStatus.SUFFICIENT_EVIDENCE,
                is_grounded=True,
                confidence_score=0.85,
                provisions_required=req_provisions,
                provisions_found=found_provisions,
                missing_provisions=[],
                content_classifications=classifications,
                has_holding_or_authoritative_support=has_holding,
                rationale="Retrieved evidence covers all required statutory provisions and conceptual propositions with authoritative grounding.",
                gate_latency_ms=elapsed,
                diagnostics={"vocab_ratio": vocab_ratio}
            )

        except Exception as e:
            logger.exception(f"PropositionGroundingGate error: {e}")
            elapsed = round((time.perf_counter() - t0) * 1000.0, 3)
            return GroundingDecision(
                status=GroundingStatus.GROUNDING_CHECK_UNAVAILABLE,
                is_grounded=False,
                confidence_score=0.0,
                rationale=f"Grounding check encountered an unexpected error: {str(e)}. Enforcing conservative fallback abstention.",
                gate_latency_ms=elapsed,
                diagnostics={"error": str(e), "fallback_applied": True}
            )

    def check_active_evidence_sufficiency(
        self,
        query: str,
        active_passages: List[EvidencePassage]
    ) -> GroundingDecision:
        """
        Active evidence sufficiency check (Milestone 8 Task 3):
        Verifies that the active evidence supplied to the LLM covers any specific statutory test,
        exception, or multi-factor component inquired by the query.
        """
        if not active_passages:
            return GroundingDecision(
                status=GroundingStatus.TOPICALLY_RELEVANT_BUT_INSUFFICIENT_GROUNDING,
                is_grounded=False,
                confidence_score=0.0,
                rationale="No active evidence passages available after passage budgeting."
            )

        all_text = "\n".join(ep.passage_text for ep in active_passages).lower()

        # Check for specific inquired legal tests or multi-factor standards
        test_patterns = [
            r'\b([a-z0-9\-]+)\s+test\b',
            r'\b(functionality\s+test)\b',
            r'\b(triple\s+test)\b',
            r'\b(prima\s+facie\s+test)\b'
        ]
        for t_pat in test_patterns:
            m_tests = re.findall(t_pat, query.lower())
            for mt in m_tests:
                if mt not in self.GENERIC_LEGAL_WORDS and mt not in {"the", "a", "an", "this", "that"}:
                    test_str = mt if "test" in mt else f"{mt} test"
                    if not self.term_in_text(mt, all_text):
                        return GroundingDecision(
                            status=GroundingStatus.TOPICALLY_RELEVANT_BUT_INSUFFICIENT_GROUNDING,
                            is_grounded=False,
                            confidence_score=0.2,
                            rationale=f"Query explicitly inquires about a specific statutory/legal test ('{test_str}'), but the test is not present or discussed in the active evidence passages supplied to generation.",
                            diagnostics={"missing_active_test": test_str}
                        )

        # Check for contradictory passages in active evidence
        if len(active_passages) >= 2:
            has_absolute_prohibition = any(RE_CONTRA_PROHIBIT.search(ep.passage_text.lower()) for ep in active_passages)
            has_extendable_holding = any(RE_CONTRA_EXTEND.search(ep.passage_text.lower()) for ep in active_passages)
            if has_absolute_prohibition and has_extendable_holding:
                return GroundingDecision(
                    status=GroundingStatus.TOPICALLY_RELEVANT_BUT_INSUFFICIENT_GROUNDING,
                    is_grounded=False,
                    confidence_score=0.25,
                    rationale="Active evidence passages contain unresolved contradictory propositions regarding the requested legal rule.",
                    diagnostics={"contradiction_detected": True}
                )

        return GroundingDecision(
            status=GroundingStatus.SUFFICIENT_EVIDENCE,
            is_grounded=True,
            confidence_score=0.85,
            rationale="Active evidence passages satisfy component sufficiency requirements."
        )
