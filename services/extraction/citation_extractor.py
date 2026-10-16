"""
Legal Citation Extractor for Indian Supreme Court Judgments.

Extracts:
1. Formal Reporter Citations:
   - Supreme Court Cases (SCC, SCC OnLine, SCC Cri, SCC L&S)
   - All India Reporter (AIR SC)
   - Supreme Court Reports (SCR, S.C.R.)
   - Neutral Citations (INSC)
2. Case Names & Party Patterns (Party A v. Party B, In re: Party)
3. Combined Case Name + Reporter Citations
4. Unanchored Precedent References ('in the case of X', 'decision in Y')
5. Observational treatment flags ('referred to', 'followed', 'distinguished')

Extracts surrounding context, normalizes citation keys, and assigns confidence levels.
"""
import re
from typing import List, Dict, Any, Optional


class CitationExtractor:
    VERSION = "1.0.0"

    # Regex definitions for formal reporters
    RE_INSC = re.compile(
        r'\b(?P<year>(?:19|20)\d{2})\s*INSC\s*(?P<num>\d+)\b',
        re.IGNORECASE
    )

    RE_SCR = re.compile(
        r'\[?(?P<year>(?:19|20)\d{2})\]?\s*(?:\((?P<part>\d+)\)\s*)?(?P<vol>\d+)?\s*S\.?C\.?R\.?\s*(?P<page>\d+)\b',
        re.IGNORECASE
    )

    RE_SCC = re.compile(
        r'(?:\((?P<year>(?:19|20)\d{2})\)|\[(?P<year_sq>(?:19|20)\d{2})\]|(?P<year_plain>(?:19|20)\d{2}))\s+'
        r'(?:(?P<vol>\d+)\s+)?'
        r'SCC(?:\s*\((?P<subpart>Cri|L&S|Civ)\))?\s+'
        r'(?P<page>\d+)\b',
        re.IGNORECASE
    )

    RE_SCC_ONLINE = re.compile(
        r'\b(?P<year>(?:19|20)\d{2})\s+SCC\s+OnLine\s+(?P<court>[A-Za-z]+)\s+(?P<num>\d+)\b',
        re.IGNORECASE
    )

    RE_AIR = re.compile(
        r'\bAIR\s+(?P<year>(?:19|20)\d{2})\s+(?P<court>SC|Supreme\s+Court)\s+(?:\(Supp\)\s+)?(?P<page>\d+)\b',
        re.IGNORECASE
    )

    # Party-versus-party pattern
    RE_CASE_NAME = re.compile(
        r'\b(?P<party1>[A-Z][A-Za-z0-9\.\,\'\s\(\)\@\-\&]{2,60}?)\s+'
        r'(?P<v>v\.|vs\.?|versus)\s+'
        r'(?P<party2>[A-Z][A-Za-z0-9\.\,\'\s\(\)\@\-\&]{2,60}?)(?=[,;:.\n\[(]|\s*[-–—]|\s+(?:reported|decided|held|referred|stated)|$)',
        re.MULTILINE
    )

    # Unanchored references: "in the case of X", "decision in X"
    RE_UNANCHORED = re.compile(
        r'\b(?:in\s+the\s+case\s+of|as\s+held\s+in|decision\s+in|judgment\s+in|view\s+taken\s+in|ratio\s+in)\s+'
        r'(?P<case_name>[A-Z][A-Za-z0-9\.\,\'\s\(\)\@\-]{3,60}?)(?=[,;.:\n]|\s*\()',
        re.IGNORECASE
    )

    # Treatment/mention signals
    RE_TREATMENT = re.compile(
        r'[-–—]?\s*(?P<treatment>referred\s+to|followed|relied\s+upon|distinguished|held\s+inapplicable|overruled|approved|cited)\b',
        re.IGNORECASE
    )

    def __init__(self, context_window_chars: int = 200):
        self.context_window = context_window_chars

    def extract_context(self, text: str, start: int, end: int) -> str:
        """Extract a bounded sentence-like window surrounding the match."""
        ctx_start = max(0, start - self.context_window)
        ctx_end = min(len(text), end + self.context_window)

        # Expand to sentence boundaries if nearby
        prev_period = text.rfind('. ', ctx_start, start)
        if prev_period != -1 and prev_period >= ctx_start:
            ctx_start = prev_period + 2

        next_period = text.find('. ', end, ctx_end)
        if next_period != -1 and next_period <= ctx_end:
            ctx_end = next_period + 1

        context = text[ctx_start:ctx_end].replace('\n', ' ').strip()
        # Collapse multiple spaces
        return re.sub(r'\s+', ' ', context)

    def extract_formal_citations(self, text: str, source_doc_id: str) -> List[Dict[str, Any]]:
        """Extract SCC, AIR, SCR, and Neutral citations."""
        citations = []
        seen_spans = set()

        # 1. Neutral INSC Citations
        for m in self.RE_INSC.finditer(text):
            span = m.span()
            if span in seen_spans:
                continue
            seen_spans.add(span)

            raw = m.group(0).strip()
            year = m.group('year')
            num = m.group('num')
            normalized = f"{year}INSC{num}"

            treatment = self._find_treatment_nearby(text, span[1])
            context = self.extract_context(text, span[0], span[1])

            citations.append({
                "source_doc_id": source_doc_id,
                "citation_type": "neutral_insc",
                "raw_text": raw,
                "normalized_citation": normalized,
                "components": {"year": int(year), "number": int(num)},
                "start_char": span[0],
                "end_char": span[1],
                "mention_context": context,
                "treatment_signal": treatment,
                "extraction_method": "regex_neutral_insc",
                "confidence": "high",
                "version": self.VERSION
            })

        # 2. SCC OnLine Citations
        for m in self.RE_SCC_ONLINE.finditer(text):
            span = m.span()
            if span in seen_spans:
                continue
            seen_spans.add(span)

            raw = m.group(0).strip()
            year = m.group('year')
            court = m.group('court').upper()
            num = m.group('num')
            normalized = f"{year} SCC OnLine {court} {num}"

            treatment = self._find_treatment_nearby(text, span[1])
            context = self.extract_context(text, span[0], span[1])

            citations.append({
                "source_doc_id": source_doc_id,
                "citation_type": "scc_online",
                "raw_text": raw,
                "normalized_citation": normalized,
                "components": {"year": int(year), "court": court, "number": int(num)},
                "start_char": span[0],
                "end_char": span[1],
                "mention_context": context,
                "treatment_signal": treatment,
                "extraction_method": "regex_scc_online",
                "confidence": "high",
                "version": self.VERSION
            })

        # 3. SCC Volume/Page Citations
        for m in self.RE_SCC.finditer(text):
            span = m.span()
            if span in seen_spans:
                continue
            seen_spans.add(span)

            raw = m.group(0).strip()
            year = m.group('year') or m.group('year_sq') or m.group('year_plain')
            vol = m.group('vol') or "1"
            subpart = m.group('subpart')
            page = m.group('page')

            subpart_str = f" ({subpart})" if subpart else ""
            normalized = f"({year}) {vol} SCC{subpart_str} {page}"

            treatment = self._find_treatment_nearby(text, span[1])
            context = self.extract_context(text, span[0], span[1])

            citations.append({
                "source_doc_id": source_doc_id,
                "citation_type": "scc",
                "raw_text": raw,
                "normalized_citation": normalized,
                "components": {"year": int(year), "volume": int(vol), "page": int(page), "subpart": subpart},
                "start_char": span[0],
                "end_char": span[1],
                "mention_context": context,
                "treatment_signal": treatment,
                "extraction_method": "regex_scc",
                "confidence": "high",
                "version": self.VERSION
            })

        # 4. SCR Citations
        for m in self.RE_SCR.finditer(text):
            span = m.span()
            if span in seen_spans:
                continue
            seen_spans.add(span)

            raw = m.group(0).strip()
            year = m.group('year')
            vol = m.group('vol') or m.group('part') or "1"
            page = m.group('page')
            normalized = f"[{year}] {vol} SCR {page}"

            treatment = self._find_treatment_nearby(text, span[1])
            context = self.extract_context(text, span[0], span[1])

            citations.append({
                "source_doc_id": source_doc_id,
                "citation_type": "scr",
                "raw_text": raw,
                "normalized_citation": normalized,
                "components": {"year": int(year), "volume": int(vol), "page": int(page)},
                "start_char": span[0],
                "end_char": span[1],
                "mention_context": context,
                "treatment_signal": treatment,
                "extraction_method": "regex_scr",
                "confidence": "high",
                "version": self.VERSION
            })

        # 5. AIR Citations
        for m in self.RE_AIR.finditer(text):
            span = m.span()
            if span in seen_spans:
                continue
            seen_spans.add(span)

            raw = m.group(0).strip()
            year = m.group('year')
            page = m.group('page')
            normalized = f"AIR {year} SC {page}"

            treatment = self._find_treatment_nearby(text, span[1])
            context = self.extract_context(text, span[0], span[1])

            citations.append({
                "source_doc_id": source_doc_id,
                "citation_type": "air",
                "raw_text": raw,
                "normalized_citation": normalized,
                "components": {"year": int(year), "court": "SC", "page": int(page)},
                "start_char": span[0],
                "end_char": span[1],
                "mention_context": context,
                "treatment_signal": treatment,
                "extraction_method": "regex_air",
                "confidence": "high",
                "version": self.VERSION
            })

        return citations

    def extract_case_names(self, text: str, source_doc_id: str) -> List[Dict[str, Any]]:
        """Extract party-versus-party case title patterns."""
        names = []
        for m in self.RE_CASE_NAME.finditer(text):
            raw = m.group(0).strip()
            p1 = self._clean_party(m.group('party1'))
            p2 = self._clean_party(m.group('party2'))

            # Filter false positives (e.g. section numbers, single letters)
            if not self._is_valid_case_title(p1, p2):
                continue

            normalized_title = f"{p1} v. {p2}"
            span = m.span()
            context = self.extract_context(text, span[0], span[1])
            treatment = self._find_treatment_nearby(text, span[1])

            names.append({
                "source_doc_id": source_doc_id,
                "citation_type": "case_title",
                "raw_text": raw,
                "normalized_citation": normalized_title,
                "components": {"party1": p1, "party2": p2},
                "start_char": span[0],
                "end_char": span[1],
                "mention_context": context,
                "treatment_signal": treatment,
                "extraction_method": "regex_case_name",
                "confidence": "medium",
                "version": self.VERSION
            })
        return names

    def extract_unanchored_mentions(self, text: str, source_doc_id: str) -> List[Dict[str, Any]]:
        """Extract mentions like 'as held in Maneka Gandhi'."""
        mentions = []
        for m in self.RE_UNANCHORED.finditer(text):
            raw = m.group(0).strip()
            case_name = m.group('case_name').strip()
            if len(case_name) < 4 or any(w in case_name.lower() for w in ['section', 'article', 'paragraph', 'court', 'appeal']):
                continue

            span = m.span()
            context = self.extract_context(text, span[0], span[1])
            treatment = self._find_treatment_nearby(text, span[1])

            mentions.append({
                "source_doc_id": source_doc_id,
                "citation_type": "unanchored_mention",
                "raw_text": raw,
                "normalized_citation": case_name,
                "components": {"reference_phrase": raw, "case_name": case_name},
                "start_char": span[0],
                "end_char": span[1],
                "mention_context": context,
                "treatment_signal": treatment,
                "extraction_method": "regex_unanchored",
                "confidence": "low",
                "version": self.VERSION
            })
        return mentions

    def extract_all(self, text: str, source_doc_id: str) -> List[Dict[str, Any]]:
        """Run all citation extraction methods and return deduplicated list."""
        all_citations = []
        all_citations.extend(self.extract_formal_citations(text, source_doc_id))
        all_citations.extend(self.extract_case_names(text, source_doc_id))
        all_citations.extend(self.extract_unanchored_mentions(text, source_doc_id))

        # Deduplicate exact duplicate spans:
        seen_spans = set()
        deduped = []
        for c in all_citations:
            span_key = (c["start_char"], c["end_char"], c["citation_type"])
            if span_key not in seen_spans:
                seen_spans.add(span_key)
                deduped.append(c)

        # Sort by appearance in document
        deduped.sort(key=lambda x: x["start_char"])
        return deduped

    def _find_treatment_nearby(self, text: str, end_pos: int, lookahead: int = 60) -> Optional[str]:
        """Check if treatment signal ('referred to', 'followed', etc.) occurs right after citation."""
        window = text[end_pos:end_pos + lookahead]
        m = self.RE_TREATMENT.search(window)
        if m:
            return re.sub(r'\s+', ' ', m.group('treatment').strip().lower())
        return None

    @staticmethod
    def _clean_party(party: str) -> str:
        """Clean party name tokens, stripping document header prefixes."""
        # Strip header artifacts if at start of party
        party = re.sub(r'^(?:(?:Case\s+(?:Details|Law\s+Cited|Arising\s+From))\s*)+', '', party, flags=re.IGNORECASE)
        party = re.sub(r'^(?:(?:(?:19|20)\d{2}\s*)?INSC\s*\d+\s*)+', '', party, flags=re.IGNORECASE)
        cleaned = party.strip(' .,;:\t\n-\'')
        # Remove multiple spaces
        cleaned = re.sub(r'\s+', ' ', cleaned)
        return cleaned

    @staticmethod
    def _is_valid_case_title(p1: str, p2: str) -> bool:
        """Filter out non-case false positives (e.g., statute numbers, headers)."""
        if len(p1) < 2 or len(p2) < 2:
            return False
        # False positive words
        invalid_words = {'sub', 'section', 'order', 'rule', 'schedule', 'clause', 'paragraph', 'para', 'page'}
        if p1.lower() in invalid_words or p2.lower() in invalid_words:
            return False
        if p1.isdigit() or p2.isdigit():
            return False
        # Must contain at least one alpha char in each party
        if not re.search(r'[A-Za-z]', p1) or not re.search(r'[A-Za-z]', p2):
            return False
        return True
