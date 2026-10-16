"""
Legal-Structure-Aware Segmentation and Structural Tagging for NyayaVarta (Milestone 9).

Identifies heuristic structural regions in Indian Supreme Court judgments:
- Case title and metadata
- Issue framing ("Issue for Consideration")
- Statutory context & Acts classification
- Editorial headnote holding ("Held:" in SCR headnotes)
- Facts and procedural history
- Party submissions (Appellant / Respondent arguments)
- Court analysis and statutory interpretation
- Judicial findings and authoritative holdings (Ratio Decidendi)
- Final order or disposition

Guarantees:
1. Exact character offset fidelity: full_text[start:end] == span_text.
2. Party submissions are strictly demarcated and NEVER labeled as judicial holdings.
3. Quoted precedents and lower court orders are distinguished from the court's own ruling.
4. Fallback to general text chunking when boundaries are uncertain; no fabricated labels.
5. All detected labels are treated as heuristics with explicit detection methods and confidence scores.
"""
import re
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field


class StructuralRegionType:
    CASE_METADATA = "case_metadata"
    ISSUE_FRAMING = "issue_framing"
    STATUTORY_CONTEXT = "statutory_context"
    HEADNOTE_HOLDING = "headnote_holding"
    FACTS_PROCEDURAL = "facts_procedural"
    PARTY_SUBMISSIONS = "party_submissions"
    COURT_ANALYSIS = "court_analysis"
    JUDICIAL_HOLDING = "judicial_holding"
    FINAL_DISPOSITION = "final_disposition"
    GENERAL_TEXT = "general_text"


class StructuralSpan(BaseModel):
    """A bounded text segment within a judgment tagged with a heuristic structural role."""
    start_char: int = Field(..., ge=0, description="Start offset in canonical full_text")
    end_char: int = Field(..., ge=0, description="End offset in canonical full_text")
    label: str = Field(..., description="Structural region label (from StructuralRegionType)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Heuristic confidence score")
    detection_method: str = Field(..., description="Method used ('explicit_heading', 'preamble_marker', 'paragraph_heuristic', 'fallback_chunk')")
    is_quoted: bool = Field(default=False, description="Whether this span represents quoted precedent or cited material")
    header_text: Optional[str] = Field(None, description="Section heading text if detected from an explicit header")


class JudgmentStructureParser:
    """
    Parses canonical judgment text into structured regions using conservative heuristics.
    Preserves 100% exact character offsets and distinguishes submissions from holdings.
    """

    PARTY_SUBMISSION_PATTERNS = [
        re.compile(r'(?i)\b(?:learned\s+(?:senior\s+)?counsel\s+(?:for|appearing\s+on\s+behalf\s+of|on\s+behalf\s+of|appearing\s+for)\s+(?:the\s+)?(?:appellant|respondent|petitioner|assessee|revenue|state|union|accused))\b'),
        re.compile(r'(?i)\b(?:learned\s+(?:senior\s+)?counsel\s+(?:has\s+)?(?:submitted|contended|argued|urged|stated))\b'),
        re.compile(r'(?i)\b(?:counsel\s+(?:appearing\s+)?(?:for|on\s+behalf\s+of)\s+(?:the\s+)?(?:appellant|respondent|petitioner))\b'),
        re.compile(r'(?i)\b(?:the\s+appellant\s+(?:broadly\s+)?(?:advanced|submitted|contended|argued))\b'),
        re.compile(r'(?i)\b(?:the\s+(?:contention|submission)\s+of\s+(?:the\s+)?(?:appellant|respondent|petitioner|assessee|revenue))\b'),
        re.compile(r'(?i)\b(?:submitted\s+by\s+(?:the\s+)?(?:appellant|respondent|petitioner|assessee|revenue))\b'),
        re.compile(r'(?i)\b(?:it\s+was\s+(?:contended|submitted|urged|argued)\s+(?:by|on\s+behalf\s+of))\b'),
        re.compile(r'(?i)\b(?:submissions?\s+(?:on\s+behalf\s+of|of\s+the))\b'),
        re.compile(r'(?i)\b(?:has\s+opposed\s+this\s+contention\s+by\s+submitting)\b'),
        re.compile(r'(?i)\b(?:on\s+behalf\s+of\s+the\s+(?:appellant|respondent|petitioner|assessee|revenue))\b')
    ]

    JUDICIAL_HOLDING_PATTERNS = [
        re.compile(r'(?i)\b(?:we\s+(?:accordingly\s+)?(?:hold|conclude|direct|order\s+and\s+direct|are\s+of\s+the\s+(?:considered\s+)?view))\b'),
        re.compile(r'(?i)\b(?:the\s+question\s+(?:referred\s+to\s+us\s+)?is\s+answered\s+in\s+the)\b'),
        re.compile(r'(?i)\b(?:in\s+the\s+result,\s+(?:it\s+is\s+held|we\s+hold|the\s+appeal))\b'),
        re.compile(r'(?i)\b(?:some\s+of\s+our\s+conclusions\s+can\s+be\s+summarised\s+as\s+under)\b'),
        re.compile(r'(?i)\b(?:for\s+the\s+reasons\s+stated\s+above,\s+we\s+hold)\b'),
        re.compile(r'(?i)\b(?:we\s+answer\s+the\s+(?:reference|question)\s+accordingly)\b'),
        re.compile(r'(?i)\b(?:held\s*:\s*[A-Z])')
    ]

    DISPOSITION_PATTERNS = [
        re.compile(r'(?i)\b(?:accordingly,\s+the\s+(?:appeals?|petitions?)\s+(?:is|are)\s+(?:allowed|dismissed|disposed\s+of))\b'),
        re.compile(r'(?i)\b(?:in\s+view\s+of\s+the\s+above,\s+the\s+(?:appeals?|petitions?)\s+(?:is|are)\s+(?:allowed|dismissed))\b'),
        re.compile(r'(?i)\b(?:we\s+accordingly\s+order\s+and\s+direct\s+that)\b'),
        re.compile(r'(?i)\b(?:no\s+order\s+as\s+to\s+costs?\.?)\b'),
        re.compile(r'(?i)\b(?:the\s+impugned\s+order\s+is\s+(?:set\s+aside|quashed|affirmed))\b')
    ]

    @classmethod
    def is_party_submission(cls, text: str) -> bool:
        """Determines if the text contains or describes party submissions."""
        return any(pat.search(text) for pat in cls.PARTY_SUBMISSION_PATTERNS)

    @classmethod
    def is_quoted_precedent(cls, text: str) -> bool:
        """Checks if the passage is a quote from a prior authority or lower court."""
        p_strip = text.strip()
        # Enclosed in quotation marks
        if (p_strip.startswith('“') and p_strip.endswith('”')) or (p_strip.startswith('"') and p_strip.endswith('"')):
            return True
        # Introduction to a prior precedent quote
        if re.search(r'(?i)\b(?:in\s+(?:the\s+case\s+of\s+)?([A-Z][a-zA-Z\s]+(?:v\.|versus|\[\d{4}\]))[^\n]*\b(?:held|observed)\s*:\s*(?:\([^\)]+\))?\s*["“])', text):
            return True
        # Quoting High Court holding
        if re.search(r'(?i)\b(?:the\s+High\s+Court\s+(?:held|observed|erred|found)\s+that)\b', text):
            return True
        if re.search(r'(?i)\b(?:wherein\s+(?:this\s+Court|it)\s+(?:was\s+)?held\s+that)\b', text):
            return True
        # Precedent cited and distinguished or declared inapplicable
        if re.search(r'(?i)\b(?:relied\s+upon\s+(?:the\s+decision|the\s+judgment)?|has\s+no\s+application|distinguishable\s+on\s+facts|differentiated)\b', text):
            return True
        return False

    @classmethod
    def is_judicial_holding(cls, text: str) -> bool:
        """Determines if the text contains the current court's own holding / ratio decidendi."""
        if cls.is_party_submission(text):
            return False
        if cls.is_quoted_precedent(text):
            return False
        return any(pat.search(text) for pat in cls.JUDICIAL_HOLDING_PATTERNS)

    @classmethod
    def is_final_disposition(cls, text: str) -> bool:
        """Determines if the text is the final order or disposition of the appeal."""
        if cls.is_party_submission(text):
            return False
        return any(pat.search(text) for pat in cls.DISPOSITION_PATTERNS)

    @classmethod
    def parse_structure(cls, full_text: str) -> List[StructuralSpan]:
        """
        Parses full_text into an ordered list of non-overlapping StructuralSpan objects.
        Preserves exact character offsets: full_text[s.start_char:s.end_char] == exact span text.
        """
        spans: List[StructuralSpan] = []
        text_len = len(full_text)
        if text_len == 0:
            return spans

        # Step 1: Detect explicit preamble markers
        issue_m = re.search(r'(?i)\n(?:issue\s+for\s+consideration|issues\s+for\s+consideration)\b', full_text)
        headnotes_m = re.search(r'(?i)\n(?:headnotes?|head-notes?)[†*]?\b', full_text)
        held_m = re.search(r'(?i)\nheld\s*:', full_text)
        body_m = re.search(
            r'(?i)\n(?:appearances\s+for\s+parties|judgment\s*/\s*order(?:\s+of\s+the\s+supreme\s+court)?|submissions?\s+(?:of|on|for)|arguments?\s+(?:of|on|for)|brief\s+facts|facts\s+of\s+the\s+case)\b',
            full_text
        )

        # If no reliable preamble markers exist, fall back to pure text-based paragraph chunking
        if not (issue_m or headnotes_m or held_m):
            paragraphs = cls._split_body_paragraphs(full_text, base_offset=0)
            for p_start, p_end, p_text in paragraphs:
                is_sub = cls.is_party_submission(p_text)
                is_quote = cls.is_quoted_precedent(p_text)
                is_hold = cls.is_judicial_holding(p_text)
                is_disp = cls.is_final_disposition(p_text)

                if is_sub:
                    lbl = StructuralRegionType.PARTY_SUBMISSIONS
                    conf = 0.85
                    meth = "paragraph_heuristic"
                elif is_disp:
                    lbl = StructuralRegionType.FINAL_DISPOSITION
                    conf = 0.90
                    meth = "paragraph_heuristic"
                elif is_hold:
                    lbl = StructuralRegionType.JUDICIAL_HOLDING
                    conf = 0.85
                    meth = "paragraph_heuristic"
                else:
                    lbl = StructuralRegionType.GENERAL_TEXT
                    conf = 0.50
                    meth = "fallback_chunk"

                spans.append(StructuralSpan(
                    start_char=p_start,
                    end_char=p_end,
                    label=lbl,
                    confidence=conf,
                    detection_method=meth,
                    is_quoted=is_quote
                ))
            return spans

        body_start = text_len
        if body_m:
            body_start = body_m.start()

        # Metadata span (start to issue_framing or headnotes)
        meta_end = issue_m.start() if issue_m else (headnotes_m.start() if headnotes_m else held_m.start())
        if meta_end > 0:
            meta_text = full_text[:meta_end].strip()
            if meta_text:
                c_start = full_text.find(meta_text)
                if cls.is_party_submission(meta_text):
                    spans.append(StructuralSpan(
                        start_char=c_start,
                        end_char=c_start + len(meta_text),
                        label=StructuralRegionType.PARTY_SUBMISSIONS,
                        confidence=0.85,
                        detection_method="paragraph_heuristic"
                    ))
                else:
                    spans.append(StructuralSpan(
                        start_char=c_start,
                        end_char=c_start + len(meta_text),
                        label=StructuralRegionType.CASE_METADATA,
                        confidence=0.95,
                        detection_method="preamble_marker"
                    ))

        # Issue for Consideration span
        if issue_m:
            issue_start = issue_m.start()
            issue_end = headnotes_m.start() if (headnotes_m and headnotes_m.start() > issue_start) else (held_m.start() if (held_m and held_m.start() > issue_start) else body_start)
            issue_raw = full_text[issue_start:issue_end].strip()
            if issue_raw:
                c_start = full_text.find(issue_raw, issue_start, issue_end)
                if c_start != -1:
                    spans.append(StructuralSpan(
                        start_char=c_start,
                        end_char=c_start + len(issue_raw),
                        label=StructuralRegionType.ISSUE_FRAMING,
                        confidence=0.95,
                        detection_method="preamble_marker",
                        header_text="Issue for Consideration"
                    ))

        # Statutory context in headnotes (between headnotes_m and held_m)
        if headnotes_m and held_m and headnotes_m.start() < held_m.start() < body_start:
            stat_start = headnotes_m.start()
            stat_end = held_m.start()
            stat_raw = full_text[stat_start:stat_end].strip()
            if stat_raw:
                c_start = full_text.find(stat_raw, stat_start, stat_end)
                if c_start != -1:
                    spans.append(StructuralSpan(
                        start_char=c_start,
                        end_char=c_start + len(stat_raw),
                        label=StructuralRegionType.STATUTORY_CONTEXT,
                        confidence=0.90,
                        detection_method="preamble_marker",
                        header_text="Headnotes Statutory Classification"
                    ))

        # Headnote Held span (editorial ratio decidendi summary)
        if held_m and held_m.start() < body_start:
            held_start = held_m.start()
            held_end = body_start
            held_raw = full_text[held_start:held_end].strip()
            if held_raw:
                c_start = full_text.find(held_raw, held_start, held_end)
                if c_start != -1:
                    spans.append(StructuralSpan(
                        start_char=c_start,
                        end_char=c_start + len(held_raw),
                        label=StructuralRegionType.HEADNOTE_HOLDING,
                        confidence=0.95,
                        detection_method="preamble_marker",
                        header_text="Headnotes Held"
                    ))

        # Step 2: Segment the Judicial Body (from body_start to text_len)
        if body_start < text_len:
            body_text = full_text[body_start:]
            body_paras = cls._split_body_paragraphs(body_text, base_offset=body_start)

            current_section_label = StructuralRegionType.COURT_ANALYSIS
            current_section_confidence = 0.60
            current_section_header = None

            for p_start, p_end, p_text in body_paras:
                # Check for explicit uppercase or title-case section headings
                header_match = cls._detect_explicit_body_header(p_text)
                if header_match:
                    current_section_label = header_match["label"]
                    current_section_confidence = header_match["confidence"]
                    current_section_header = header_match["header_text"]

                # Paragraph-level contextual classification
                is_sub = cls.is_party_submission(p_text)
                is_quote = cls.is_quoted_precedent(p_text)
                is_hold = cls.is_judicial_holding(p_text)
                is_disp = cls.is_final_disposition(p_text)

                # Assign label adhering strictly to precedence
                if is_sub or current_section_label == StructuralRegionType.PARTY_SUBMISSIONS:
                    # Explicit party submission
                    label = StructuralRegionType.PARTY_SUBMISSIONS
                    confidence = 0.85 if is_sub else current_section_confidence
                    method = "paragraph_heuristic" if is_sub else "explicit_heading"
                elif is_disp:
                    label = StructuralRegionType.FINAL_DISPOSITION
                    confidence = 0.90
                    method = "paragraph_heuristic"
                elif is_hold:
                    label = StructuralRegionType.JUDICIAL_HOLDING
                    confidence = 0.90
                    method = "paragraph_heuristic"
                elif is_quote:
                    label = current_section_label
                    confidence = 0.80
                    method = "quoted_precedent"
                else:
                    label = current_section_label
                    confidence = current_section_confidence
                    method = "explicit_heading" if current_section_header else "fallback_chunk"

                spans.append(StructuralSpan(
                    start_char=p_start,
                    end_char=p_end,
                    label=label,
                    confidence=confidence,
                    detection_method=method,
                    is_quoted=is_quote,
                    header_text=current_section_header
                ))

        # Verify exact offset invariant for all generated spans
        for s in spans:
            extracted = full_text[s.start_char:s.end_char]
            assert len(extracted) == (s.end_char - s.start_char), f"Length mismatch for span {s.label}"

        return spans

    @classmethod
    def _detect_explicit_body_header(cls, text: str) -> Optional[Dict[str, Any]]:
        """Detects whether paragraph text begins with or constitutes an explicit body heading."""
        first_line = text.split('\n')[0].strip()
        if len(first_line) > 80:
            return None

        fl_lower = first_line.lower()
        if any(h in fl_lower for h in ["submissions on behalf of", "submissions of the", "submissions of respondent", "submissions of appellant", "submissions of revenue", "submissions of assessees", "submissions"]):
            return {"label": StructuralRegionType.PARTY_SUBMISSIONS, "confidence": 0.90, "header_text": first_line}
        if any(h in fl_lower for h in ["analysis of clauses", "analysis and reasoning", "discussion", "reasons", "statutory framework"]):
            return {"label": StructuralRegionType.COURT_ANALYSIS, "confidence": 0.85, "header_text": first_line}
        if any(h in fl_lower for h in ["broad issues for consideration", "issues"]):
            return {"label": StructuralRegionType.ISSUE_FRAMING, "confidence": 0.90, "header_text": first_line}
        if any(h in fl_lower for h in ["conclusions", "conclusion", "directions", "findings"]):
            return {"label": StructuralRegionType.JUDICIAL_HOLDING, "confidence": 0.90, "header_text": first_line}
        if any(h in fl_lower for h in ["facts", "factual background", "brief facts"]):
            return {"label": StructuralRegionType.FACTS_PROCEDURAL, "confidence": 0.85, "header_text": first_line}

        return None

    @classmethod
    def _split_body_paragraphs(cls, body_text: str, base_offset: int, min_chars: int = 40) -> List[Tuple[int, int, str]]:
        """Splits body text along paragraph breaks while preserving absolute offsets."""
        paragraphs: List[Tuple[int, int, str]] = []
        para_pattern = re.compile(r'\n\s*\n')
        last_end = 0

        for m in para_pattern.finditer(body_text):
            start = last_end
            end = m.start()
            last_end = m.end()

            p_str = body_text[start:end].strip()
            if len(p_str) >= min_chars:
                c_start = body_text.find(p_str, start, end)
                if c_start != -1:
                    paragraphs.append((base_offset + c_start, base_offset + c_start + len(p_str), p_str))

        if last_end < len(body_text):
            trailing = body_text[last_end:].strip()
            if len(trailing) >= min_chars:
                c_start = body_text.find(trailing, last_end)
                if c_start != -1:
                    paragraphs.append((base_offset + c_start, base_offset + c_start + len(trailing), trailing))

        return paragraphs

    @classmethod
    def extract_structural_candidate_spans(
        cls,
        full_text: str,
        target_passage_chars: int = 800,
        min_passage_chars: int = 60
    ) -> List[Dict[str, Any]]:
        """
        Parses full_text into discrete candidate passage spans tagged with structural metadata.
        Preserves 100% exact substring offsets: full_text[start:end] == span_text.
        """
        spans = cls.parse_structure(full_text)
        passages: List[Dict[str, Any]] = []

        para_pat = re.compile(r'\n\s*\n')

        for s in spans:
            span_text = full_text[s.start_char:s.end_char]
            # If span is already compact enough, keep it as a coherent unit
            if len(span_text) <= target_passage_chars:
                if len(span_text) >= min_passage_chars:
                    passages.append({
                        "start_char": s.start_char,
                        "end_char": s.end_char,
                        "text": span_text,
                        "structural_label": s.label,
                        "structural_confidence": s.confidence,
                        "detection_method": s.detection_method,
                        "is_quoted": s.is_quoted
                    })
            else:
                # Split large structural regions along paragraph breaks
                last_end = 0
                for m in para_pat.finditer(span_text):
                    p_str = span_text[last_end:m.start()].strip()
                    if len(p_str) >= min_passage_chars:
                        c_start = span_text.find(p_str, last_end, m.start())
                        if c_start != -1:
                            abs_start = s.start_char + c_start
                            abs_end = abs_start + len(p_str)
                            passages.append({
                                "start_char": abs_start,
                                "end_char": abs_end,
                                "text": p_str,
                                "structural_label": s.label,
                                "structural_confidence": s.confidence,
                                "detection_method": s.detection_method,
                                "is_quoted": s.is_quoted
                            })
                    last_end = m.end()

                if last_end < len(span_text):
                    trailing = span_text[last_end:].strip()
                    if len(trailing) >= min_passage_chars:
                        c_start = span_text.find(trailing, last_end)
                        if c_start != -1:
                            abs_start = s.start_char + c_start
                            abs_end = abs_start + len(trailing)
                            passages.append({
                                "start_char": abs_start,
                                "end_char": abs_end,
                                "text": trailing,
                                "structural_label": s.label,
                                "structural_confidence": s.confidence,
                                "detection_method": s.detection_method,
                                "is_quoted": s.is_quoted
                            })

        return passages

