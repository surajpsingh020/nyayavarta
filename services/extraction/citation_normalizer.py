"""
Canonical Case-Citation Normalizer for NyayaVarta (Milestone 11 Task 2).

Provides deterministic, idempotent normalization for Indian legal citation formats:
- Supreme Court Cases (SCC, SCC Cri, SCC L&S, SCC Civ, SCC Supp)
- SCC OnLine (Supreme Court and High Courts)
- Supreme Court Reports (SCR, S.C.R., SCR Supp)
- All India Reporter (AIR SC, AIR Supreme Court, AIR Supp)
- Indian Neutral Citations (INSC)

Guarantees:
- Deterministic: Same input always produces identical output.
- Idempotent: Normalizing an already normalized citation produces the exact same representation.
- Format-specific: Does not conflate volume, page, year, or sequential numbers.
- Fail-safe: Incomplete, ambiguous, or malformed citations are assigned explicit parsing_status
  and status_reason without inventing missing fields.
"""
import re
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, asdict


@dataclass
class NormalizedCitation:
    original_text: str
    normalized_citation: str
    citation_scheme: str  # 'scc', 'scc_online', 'scr', 'air', 'neutral_insc', 'unknown'
    year: Optional[int] = None
    volume: Optional[str] = None
    reporter: Optional[str] = None
    court: Optional[str] = None
    page_or_number: Optional[str] = None
    supplement: bool = False
    subpart: Optional[str] = None
    parsing_status: str = "valid"  # 'valid', 'partial', 'malformed', 'unsupported'
    status_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class CitationNormalizer:
    VERSION = "2.0.0"

    # --- Pre-compiled Patterns ---

    # 1. Neutral INSC: e.g. "2024 INSC 735", "2024INSC735", "INSC 2024 735"
    RE_INSC = re.compile(
        r'^(?:(?P<year>(?:19|20)\d{2})\s*INSC\s*(?P<num>\d+)|INSC\s*(?P<year_alt>(?:19|20)\d{2})\s*(?P<num_alt>\d+))$',
        re.IGNORECASE
    )

    # 2. SCC OnLine: e.g. "2024 SCC OnLine SC 1796", "2021 SCC OnLine Del 456"
    RE_SCC_ONLINE = re.compile(
        r'^(?P<year>(?:19|20)\d{2})\s+SCC\s*On\s*Line\s+(?P<court>[A-Za-z]+(?:\s+[A-Za-z]+)?)\s+(?P<num>\d+)$',
        re.IGNORECASE
    )

    # 3. SCR: e.g. "[2024] 10 S.C.R. 108", "[1978] 2 SCR 621", "(1978) 2 SCR 621", "[1997] Supp. SCR 12", "[1997] Supp 1 SCR 12"
    RE_SCR = re.compile(
        r'^[\[\(]?(?P<year>(?:19|20)\d{2})[\]\)]?\s*'
        r'(?:(?P<supp>Supp(?:l|\.|\s*\(?\d*\)?)?)\s*)?'
        r'(?:(?P<vol>\d+)\s+)?'
        r'S\.?\s*C\.?\s*R\.?\s*'
        r'(?P<page>\d+)$',
        re.IGNORECASE
    )

    # 4. SCC: e.g. "(2019) 14 SCC 81", "[2024] 2 SCC 1", "2024 (2) SCC 1", "(2007) 3 SCC (Cri) 359", "(1995) Supp (2) SCC 187"
    RE_SCC = re.compile(
        r'^[\[\(]?(?P<year>(?:19|20)\d{2})[\]\)]?\s*'
        r'(?:(?P<supp>Supp(?:\s*\((?P<supp_vol>\d+)\)|\s+(?P<supp_vol_alt>\d+))?)\s+)?'
        r'(?:(?:\((?P<vol_paren>\d+)\)|(?P<vol_plain>\d+))\s+)?'
        r'SCC(?:\s*\((?P<subpart>Cri|L&S|Civ|Cri\.|L\s*&\s*S)\))?\s+'
        r'(?P<page>\d+)$',
        re.IGNORECASE
    )

    # 5. AIR: e.g. "AIR 1978 SC 597", "AIR 1955 SC 807", "AIR 2024 Supreme Court 123", "AIR 1978 SC (Supp) 12"
    RE_AIR = re.compile(
        r'^AIR\s+(?P<year>(?:19|20)\d{2})\s+'
        r'(?P<court>SC|Supreme\s+Court|[A-Za-z]+)\s+'
        r'(?:(?P<supp>\(?Supp\)?)\s+)?'
        r'(?P<page>\d+)$',
        re.IGNORECASE
    )

    # Incomplete / Malformed indicators
    RE_INCOMPLETE = re.compile(
        r'^(?:(?:\(\d{4}\)|\[\d{4}\]|\d{4})\s+(?:SCC|SCR|AIR|INSC)|SCC|SCR|AIR|INSC)$',
        re.IGNORECASE
    )

    def normalize(self, raw_citation: str) -> NormalizedCitation:
        """
        Normalize a raw citation string deterministically.
        Idempotent: normalize(normalize(text).normalized_citation) == normalize(text)
        """
        if not raw_citation or not isinstance(raw_citation, str):
            return NormalizedCitation(
                original_text=str(raw_citation or ""),
                normalized_citation="",
                citation_scheme="unknown",
                parsing_status="malformed",
                status_reason="empty_or_non_string_citation"
            )

        cleaned = raw_citation.strip()
        # Normalize whitespace inside and around brackets/parentheses
        cleaned = re.sub(r'\(\s+', '(', cleaned)
        cleaned = re.sub(r'\s+\)', ')', cleaned)
        cleaned = re.sub(r'\[\s+', '[', cleaned)
        cleaned = re.sub(r'\s+\]', ']', cleaned)
        # Collapse excessive internal whitespace
        cleaned_single_spaced = re.sub(r'\s+', ' ', cleaned)

        # 1. Test INSC (Neutral Citation)
        m = self.RE_INSC.match(cleaned_single_spaced)
        if m:
            year = int(m.group('year') or m.group('year_alt'))
            num = int(m.group('num') or m.group('num_alt'))
            canonical = f"{year} INSC {num}"
            return NormalizedCitation(
                original_text=cleaned,
                normalized_citation=canonical,
                citation_scheme="neutral_insc",
                year=year,
                reporter="INSC",
                court="SC",
                page_or_number=str(num),
                parsing_status="valid"
            )

        # 2. Test SCC OnLine
        m = self.RE_SCC_ONLINE.match(cleaned_single_spaced)
        if m:
            year = int(m.group('year'))
            court_raw = m.group('court').strip()
            # Normalize court: "sc" -> "SC", "Supreme Court" -> "SC", "del" -> "Del"
            court = "SC" if court_raw.upper() in {"SC", "SUPREME COURT"} else court_raw.capitalize()
            num = int(m.group('num'))
            canonical = f"{year} SCC OnLine {court} {num}"
            return NormalizedCitation(
                original_text=cleaned,
                normalized_citation=canonical,
                citation_scheme="scc_online",
                year=year,
                reporter="SCC OnLine",
                court=court,
                page_or_number=str(num),
                parsing_status="valid"
            )

        # 3. Test SCR
        m = self.RE_SCR.match(cleaned_single_spaced)
        if m:
            year = int(m.group('year'))
            supp = m.group('supp')
            vol = m.group('vol')
            page = m.group('page')

            vol_str = f" {vol}" if vol else ""
            supp_str = " Supp." if supp else ""
            if supp and not vol:
                canonical = f"[{year}]{supp_str} SCR {page}"
            elif supp and vol:
                canonical = f"[{year}]{supp_str}{vol_str} SCR {page}"
            else:
                canonical = f"[{year}]{vol_str} SCR {page}"

            return NormalizedCitation(
                original_text=cleaned,
                normalized_citation=canonical,
                citation_scheme="scr",
                year=year,
                volume=vol,
                reporter="SCR",
                court="SC",
                page_or_number=str(page),
                supplement=bool(supp),
                parsing_status="valid"
            )

        # 4. Test SCC
        m = self.RE_SCC.match(cleaned_single_spaced)
        if m:
            year = int(m.group('year'))
            supp = m.group('supp')
            supp_vol = m.group('supp_vol') or m.group('supp_vol_alt')
            vol = m.group('vol_paren') or m.group('vol_plain')
            subpart_raw = m.group('subpart')
            page = m.group('page')

            subpart = None
            if subpart_raw:
                s_clean = re.sub(r'[\s\.]', '', subpart_raw).upper()
                if "CRI" in s_clean:
                    subpart = "Cri"
                elif "L&S" in s_clean or "LS" in s_clean:
                    subpart = "L&S"
                elif "CIV" in s_clean:
                    subpart = "Civ"

            # Construct canonical string: e.g. (2019) 14 SCC 81, (2007) 3 SCC (Cri) 359, (1995) Supp (2) SCC 187
            subpart_str = f" ({subpart})" if subpart else ""
            if supp:
                s_vol = f" ({supp_vol})" if supp_vol else ""
                canonical = f"({year}) Supp{s_vol} SCC{subpart_str} {page}"
                volume_str = f"Supp{s_vol}"
            else:
                vol_str = f" {vol}" if vol else ""
                canonical = f"({year}){vol_str} SCC{subpart_str} {page}"
                volume_str = vol

            return NormalizedCitation(
                original_text=cleaned,
                normalized_citation=canonical,
                citation_scheme="scc",
                year=year,
                volume=volume_str,
                reporter=f"SCC{subpart_str}" if subpart else "SCC",
                court="SC",
                page_or_number=str(page),
                supplement=bool(supp),
                subpart=subpart,
                parsing_status="valid"
            )

        # 5. Test AIR
        m = self.RE_AIR.match(cleaned_single_spaced)
        if m:
            year = int(m.group('year'))
            court_raw = m.group('court').strip()
            court = "SC" if court_raw.upper() in {"SC", "SUPREME COURT"} else court_raw.capitalize()
            supp = m.group('supp')
            page = m.group('page')
            supp_str = " (Supp)" if supp else ""
            canonical = f"AIR {year} {court}{supp_str} {page}"
            return NormalizedCitation(
                original_text=cleaned,
                normalized_citation=canonical,
                citation_scheme="air",
                year=year,
                reporter="AIR",
                court=court,
                page_or_number=str(page),
                supplement=bool(supp),
                parsing_status="valid"
            )

        # 6. Check for incomplete or partial citation
        # E.g. "2024 SCC", "(2019) 14 SCC", "SCR 108"
        if any(rep in cleaned_single_spaced.upper() for rep in ["SCC", "SCR", "AIR", "INSC"]):
            year_match = re.search(r'\b(19\d{2}|20\d{2})\b', cleaned_single_spaced)
            year_val = int(year_match.group(1)) if year_match else None
            return NormalizedCitation(
                original_text=cleaned,
                normalized_citation=cleaned_single_spaced,
                citation_scheme=self._guess_scheme(cleaned_single_spaced),
                year=year_val,
                parsing_status="partial",
                status_reason="missing_volume_or_page"
            )

        # 7. Unsupported / Malformed
        return NormalizedCitation(
            original_text=cleaned,
            normalized_citation=cleaned_single_spaced,
            citation_scheme="unknown",
            parsing_status="unsupported",
            status_reason="unrecognized_citation_format"
        )

    def _guess_scheme(self, text: str) -> str:
        u = text.upper()
        if "INSC" in u:
            return "neutral_insc"
        if "SCC ONLINE" in u:
            return "scc_online"
        if "SCC" in u:
            return "scc"
        if "SCR" in u or "S.C.R." in u:
            return "scr"
        if "AIR" in u:
            return "air"
        return "unknown"

    def split_parallel_citations(self, text: str) -> List[str]:
        """
        Split strings that join parallel citations via semicolon, colon, or 'also reported in'.
        E.g. '[2024] 10 SCR 154 : 2024 SCC OnLine SC 123' -> ['[2024] 10 SCR 154', '2024 SCC OnLine SC 123']
        """
        if not text:
            return []
        parts = re.split(r'\s*(?:;|:\s*(?=[\[\(]|\d{4}|AIR|INSC)|also reported (?:at|in)\s*)\s*', text, flags=re.IGNORECASE)
        return [p.strip() for p in parts if p.strip()]
