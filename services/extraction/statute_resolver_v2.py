"""
Conservative Statutory Attribution Engine V2 for NyayaVarta (Milestone 11 Task 4 & Task 7).

Resolves governing statutes for statutory section references:
- Preserves explicit inline governing statutes, including direct acronyms (Section 307 IPC, Section 482 CrPC, Section 9 IBC).
- Normalizes formal Acts to official canonical titles with enactment year.
- Implements conservative, paragraph-bounded inheritance ONLY when:
  1. The section mention is within the same paragraph as the governing Act.
  2. Exactly one unambiguous Act was introduced in the preceding text of that paragraph.
  3. No intervening statute or topic shift occurred.
- Strictly guards against false inheritance:
  - Never inherits across paragraphs, sections, or document boundaries.
  - Never infers an Act from a section number alone (protects Section 5, 9, 14, 34, 100, 302 collisions).
  - Assigns 'ambiguous' when multiple candidate Acts coexist in the local scope.
  - Retains 'unresolved' (governing_statute=None) when local evidence is insufficient.
"""
import re
from typing import Dict, Any, List, Optional, Tuple, Set


class StatuteResolverV2:
    VERSION = "2.0.0"

    # Acronyms mapping to canonical titles with official year
    ACRONYM_TO_ACT = {
        "IPC": "Indian Penal Code, 1860",
        "CRPC": "Code of Criminal Procedure, 1973",
        "CPC": "Code of Civil Procedure, 1908",
        "PMLA": "Prevention of Money Laundering Act, 2002",
        "IBC": "Insolvency and Bankruptcy Code, 2016",
        "NI ACT": "Negotiable Instruments Act, 1881",
        "TPA": "Transfer of Property Act, 1882",
        "POCSO": "Protection of Children from Sexual Offences Act, 2012",
        "POCSO ACT": "Protection of Children from Sexual Offences Act, 2012",
        "SARFAESI": "Securitisation and Reconstruction of Financial Assets and Enforcement of Security Interest Act, 2002",
        "SARFAESI ACT": "Securitisation and Reconstruction of Financial Assets and Enforcement of Security Interest Act, 2002",
        "UAPA": "Unlawful Activities (Prevention) Act, 1967",
        "NDPS": "Narcotic Drugs and Psychotropic Substances Act, 1985",
        "NDPS ACT": "Narcotic Drugs and Psychotropic Substances Act, 1985",
        "CGST": "Central Goods and Services Tax Act, 2017",
        "CGST ACT": "Central Goods and Services Tax Act, 2017",
        "RTI": "Right to Information Act, 2005",
        "RTI ACT": "Right to Information Act, 2005",
        "LIMITATION ACT": "Limitation Act, 1963",
        "SPECIFIC RELIEF ACT": "Specific Relief Act, 1963",
        "ARBITRATION ACT": "Arbitration and Conciliation Act, 1996",
        "COMPANIES ACT": "Companies Act, 2013",
        "EVIDENCE ACT": "Indian Evidence Act, 1872",
        "MOTOR VEHICLES ACT": "Motor Vehicles Act, 1988",
        "LAND ACQUISITION ACT": "Land Acquisition Act, 1894",
        "MMDR ACT": "Mines and Minerals (Development and Regulation) Act, 1957",
        "CUSTOMS ACT": "Customs Act, 1962",
        "COMPETITION ACT": "Competition Act, 2002",
        "PREVENTION OF CORRUPTION ACT": "Prevention of Corruption Act, 1988",
        "COMMERCIAL COURTS ACT": "Commercial Courts Act, 2015",
        "CONSTITUTION": "Constitution of India"
    }

    # Canonical full titles and aliases mapping to official canonical title + year
    CANONICAL_ALIASES = {
        "indian penal code": "Indian Penal Code, 1860",
        "penal code 1860": "Indian Penal Code, 1860",
        "penal code": "Indian Penal Code, 1860",
        "indian evidence act 1872": "Indian Evidence Act, 1872",
        "evidence act 1872": "Indian Evidence Act, 1872",
        "evidence act": "Indian Evidence Act, 1872",
        "code of criminal procedure": "Code of Criminal Procedure, 1973",
        "code of criminal procedure 1973": "Code of Criminal Procedure, 1973",
        "code of civil procedure": "Code of Civil Procedure, 1908",
        "code of civil procedure 1908": "Code of Civil Procedure, 1908",
        "negotiable instruments act": "Negotiable Instruments Act, 1881",
        "negotiable instruments act 1881": "Negotiable Instruments Act, 1881",
        "transfer of property act": "Transfer of Property Act, 1882",
        "transfer of property act 1882": "Transfer of Property Act, 1882",
        "arbitration and conciliation act": "Arbitration and Conciliation Act, 1996",
        "arbitration and conciliation act 1996": "Arbitration and Conciliation Act, 1996",
        "arbitration act": "Arbitration and Conciliation Act, 1996",
        "limitation act": "Limitation Act, 1963",
        "limitation act 1963": "Limitation Act, 1963",
        "land acquisition act": "Land Acquisition Act, 1894",
        "land acquisition act 1894": "Land Acquisition Act, 1894",
        "companies act": "Companies Act, 2013",
        "companies act 2013": "Companies Act, 2013",
        "prevention of money laundering act": "Prevention of Money Laundering Act, 2002",
        "prevention of money laundering act 2002": "Prevention of Money Laundering Act, 2002",
        "insolvency and bankruptcy code": "Insolvency and Bankruptcy Code, 2016",
        "insolvency and bankruptcy code 2016": "Insolvency and Bankruptcy Code, 2016",
        "central goods and services tax act": "Central Goods and Services Tax Act, 2017",
        "central goods and services tax act 2017": "Central Goods and Services Tax Act, 2017",
        "motor vehicles act": "Motor Vehicles Act, 1988",
        "motor vehicles act 1988": "Motor Vehicles Act, 1988",
        "specific relief act": "Specific Relief Act, 1963",
        "specific relief act 1963": "Specific Relief Act, 1963",
        "sarfaesi act": "Securitisation and Reconstruction of Financial Assets and Enforcement of Security Interest Act, 2002",
        "prevention of corruption act": "Prevention of Corruption Act, 1988",
        "prevention of corruption act 1988": "Prevention of Corruption Act, 1988",
        "commercial courts act": "Commercial Courts Act, 2015",
        "commercial courts act 2015": "Commercial Courts Act, 2015",
        "protection of children from sexual offences act": "Protection of Children from Sexual Offences Act, 2012",
        "protection of children from sexual offences act 2012": "Protection of Children from Sexual Offences Act, 2012",
        "narcotic drugs and psychotropic substances act": "Narcotic Drugs and Psychotropic Substances Act, 1985",
        "narcotic drugs and psychotropic substances act 1985": "Narcotic Drugs and Psychotropic Substances Act, 1985",
        "unlawful activities prevention act": "Unlawful Activities (Prevention) Act, 1967",
        "unlawful activities prevention act 1967": "Unlawful Activities (Prevention) Act, 1967",
        "competition act": "Competition Act, 2002",
        "competition act 2002": "Competition Act, 2002",
        "customs act": "Customs Act, 1962",
        "customs act 1962": "Customs Act, 1962",
        "mines and minerals development and regulation act": "Mines and Minerals (Development and Regulation) Act, 1957",
        "mines and minerals development and regulation act 1957": "Mines and Minerals (Development and Regulation) Act, 1957",
        "environment protection act": "Environment (Protection) Act, 1986",
        "environment protection act 1986": "Environment (Protection) Act, 1986",
        "constitution of india": "Constitution of India"
    }

    PSEUDO_ACT_REGEX = re.compile(r'^(?:the|said|aforesaid|this|an|such)\s+(?:\d{4}\s+)?(?:act|code)$', re.IGNORECASE)
    DISALLOWED_TERMS = {
        'fact', 'charact', 'pract', 'attract', 'prescribed', 'because', 'owing to',
        'application to', 'filed', 'clause', 'section', 'read with', 'unlawful act', 'petition'
    }

    RE_FORMAL_ACT_V2 = re.compile(
        r'\b(?P<act_name>[A-Z][a-zA-Z0-9\(\)\'\-]*(?:\s+(?:of|and|for|in|the|[\(]?[A-Z][a-zA-Z0-9\(\)\'\-]*))*\s+(?:Act|Code|Procedure|Rules|Regulations|Order))\s*,\s*(?P<year>(?:18|19|20)\d{2})\b'
    )
    RE_ACRONYM_ACT_V2 = re.compile(
        r'\b(?P<acronym>IPC|CrPC|CPC|PMLA|IBC|SARFAESI(?:\s+Act)?|POCSO(?:\s+Act)?|UAPA|NDPS(?:\s+Act)?|CGST(?:\s+Act)?|NI\s+Act)\b'
    )
    RE_CONSTITUTION_V2 = re.compile(
        r'\b(?:Constitution\s+of\s+India|the\s+Constitution)\b',
        re.IGNORECASE
    )

    # Enhanced Section regex capturing direct acronyms (Section 307 IPC, Section 482 CrPC, etc.)
    RE_SECTION_V2 = re.compile(
        r'\b(?P<sec_prefix>Sections?|Sec\.|s\.|u/ss?\.?|under\s+Section)\s+'
        r'(?P<sec_num>\d+[A-Za-z]*(?:\([0-9a-zA-Z]+\))*(?:/\d+)*(?:\s*(?:,|and|read\s+with|\-)\s*\d+[A-Za-z]*(?:\([0-9a-zA-Z]+\))*)*)'
        r'(?:(?:\s+(?:of\s+the|of|in|under|,))?\s+(?P<governing_act>(?:IPC|CrPC|CPC|PMLA|IBC|NI\s+Act|[A-Z][A-Za-z0-9\s\(\)\'\-,]{0,50}?\b(?:Act|Code|Procedure)\b)))?',
        re.IGNORECASE
    )

    def clean_and_validate_act(self, raw_act: Optional[str]) -> Optional[str]:
        """Validate and normalize Act titles to canonical title with official year."""
        if not raw_act:
            return None
        cleaned = re.sub(r'\s+', ' ', raw_act).strip(' ,.-;')
        if not cleaned or len(cleaned) < 2:
            return None
        if self.PSEUDO_ACT_REGEX.match(cleaned):
            return None
        lower = cleaned.lower()
        pseudo_words = {'the act', 'said act', 'the said act', 'this act', 'an act', 'act', 'the code', 'said code', 'this code', 'code'}
        if lower in pseudo_words:
            return None
        if any(re.search(r'\b' + re.escape(t) + r'\b', lower) for t in self.DISALLOWED_TERMS):
            return None
        # Reject non-proper pseudo-captures containing words like 'without', 'any', 'arbitrary', 'illegal'
        bad_act_words = {'without', 'any', 'arbitrary', 'illegal', 'every', 'such', 'aforesaid'}
        if any(re.search(r'\b' + re.escape(w) + r'\b', lower) for w in bad_act_words):
            return None
        if cleaned.count('(') != cleaned.count(')'):
            return None

        # Clean leading prepositions
        cleaned_no_lead = re.sub(
            r'^(?:under\s+the|under|in\s+the|in|the|provisions\s+of\s+the|provisions\s+of|provisions\s+under\s+the|statutes\s+including\s+the|including\s+the|including)\s+',
            '', cleaned, flags=re.IGNORECASE
        ).strip()

        # Check acronyms
        test_str = cleaned_no_lead
        if test_str.upper() in self.ACRONYM_TO_ACT:
            return self.ACRONYM_TO_ACT[test_str.upper()]
        if cleaned.upper() in self.ACRONYM_TO_ACT:
            return self.ACRONYM_TO_ACT[cleaned.upper()]

        # Check canonical aliases
        norm_key = re.sub(r'[^\w\s]', '', test_str.lower()).strip()
        if norm_key in self.CANONICAL_ALIASES:
            return self.CANONICAL_ALIASES[norm_key]

        norm_full = re.sub(r'[^\w\s]', '', cleaned.lower()).strip()
        if norm_full in self.CANONICAL_ALIASES:
            return self.CANONICAL_ALIASES[norm_full]

        if test_str.lower().startswith('the ') and ('act' in test_str.lower() or 'code' in test_str.lower()):
            test_str = test_str[4:].strip()

        return test_str

    def extract_acts_v2(self, text: str) -> List[Dict[str, Any]]:
        """Extract all verified Act occurrences with character spans."""
        acts = []
        seen_spans = set()

        # 1. Formal Acts with year
        for m in self.RE_FORMAL_ACT_V2.finditer(text):
            span = m.span()
            raw_act_name = m.group('act_name').strip()
            year = m.group('year').strip()
            cleaned_act_name = re.sub(
                r'^(?:under\s+the|under|in\s+the|in|the|provisions\s+of\s+the|provisions\s+of|provisions\s+under\s+the|statutes\s+including\s+the|including\s+the|including)\s+',
                '', raw_act_name, flags=re.IGNORECASE
            ).strip()
            norm = f"{cleaned_act_name}, {year}"
            validated = self.clean_and_validate_act(norm)
            if validated:
                acts.append({
                    "act_title": validated,
                    "start_char": span[0],
                    "end_char": span[1],
                    "raw_text": m.group(0)
                })
                seen_spans.add(span)

        # 2. Known acronyms
        for m in self.RE_ACRONYM_ACT_V2.finditer(text):
            span = m.span()
            if any(s[0] <= span[0] and span[1] <= s[1] for s in seen_spans):
                continue
            raw_acronym = m.group('acronym').strip().upper()
            canonical = self.ACRONYM_TO_ACT.get(raw_acronym)
            if canonical:
                acts.append({
                    "act_title": canonical,
                    "start_char": span[0],
                    "end_char": span[1],
                    "raw_text": m.group(0)
                })
                seen_spans.add(span)

        # 3. Constitution
        for m in self.RE_CONSTITUTION_V2.finditer(text):
            span = m.span()
            if any(s[0] <= span[0] and span[1] <= s[1] for s in seen_spans):
                continue
            acts.append({
                "act_title": "Constitution of India",
                "start_char": span[0],
                "end_char": span[1],
                "raw_text": m.group(0)
            })
            seen_spans.add(span)

        return acts

    def extract_sections_v2(self, text: str, source_doc_id: str) -> List[Dict[str, Any]]:
        """Extract sections with enhanced support for direct acronyms (Section 307 IPC, etc.)."""
        sections = []
        for m in self.RE_SECTION_V2.finditer(text):
            span = m.span()
            raw = m.group(0).strip()
            sec_num = m.group('sec_num').strip()
            governing = m.group('governing_act')

            governing_clean = self.clean_and_validate_act(governing) if governing else None

            normalized = f"Section {sec_num}"
            if governing_clean:
                normalized += f" of {governing_clean}"

            sections.append({
                "source_doc_id": source_doc_id,
                "reference_type": "statutory_section",
                "raw_text": raw,
                "normalized_reference": normalized,
                "components": {
                    "section_numbers": sec_num,
                    "governing_statute": governing_clean
                },
                "start_char": span[0],
                "end_char": span[1],
                "extraction_method": "regex_section_v2",
                "confidence": "high" if governing_clean else "medium",
                "version": self.VERSION
            })
        return sections

    def resolve_document_statutes(
        self,
        text: str,
        source_doc_id: str,
        extracted_sections: Optional[List[Dict[str, Any]]] = None,
        extracted_acts: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """
        Assign governing statutes to extracted section references using paragraph-bounded scope.
        """
        if extracted_sections is None:
            extracted_sections = self.extract_sections_v2(text, source_doc_id)

        # Step 1: Compute paragraph boundaries
        para_spans = []
        pattern = re.compile(r'\n\s*\n')
        last_idx = 0
        for match in pattern.finditer(text):
            span_start = last_idx
            span_end = match.start()
            if span_end > span_start:
                para_spans.append((span_start, span_end))
            last_idx = match.end()
        if last_idx < len(text):
            para_spans.append((last_idx, len(text)))

        def find_para_index(offset: int) -> int:
            for idx, (p_start, p_end) in enumerate(para_spans):
                if p_start <= offset <= p_end:
                    return idx
            return -1

        # Step 2: Extract all verified Acts in the text
        all_acts = self.extract_acts_v2(text)
        acts_by_para = {}
        for act in all_acts:
            p_idx = find_para_index(act["start_char"])
            if p_idx not in acts_by_para:
                acts_by_para[p_idx] = []
            acts_by_para[p_idx].append(act)

        # Step 3: Resolve each section
        resolved_sections = []
        for sec in extracted_sections:
            sec_copy = dict(sec)
            sec_start = sec.get("start_char", 0)
            sec_comps = dict(sec_copy.get("components", {}))
            sec_copy["components"] = sec_comps
            raw_governing = sec_comps.get("governing_statute")

            # Check if section already has explicit inline governing statute
            cleaned_explicit = self.clean_and_validate_act(raw_governing)

            if cleaned_explicit:
                # Explicit attribution
                sec_comps["governing_statute"] = cleaned_explicit
                sec_copy["attribution_type"] = "explicit"
                sec_copy["attribution_source"] = "inline_mention"
                sec_copy["confidence"] = "high"
                sec_copy["normalized_reference"] = f"Section {sec_comps.get('section_numbers')} of {cleaned_explicit}"
                resolved_sections.append(sec_copy)
                continue

            # Section lacks explicit governing statute: attempt conservative paragraph inheritance
            p_idx = find_para_index(sec_start)
            if p_idx == -1 or p_idx not in acts_by_para:
                # No Act mentioned in this paragraph
                sec_comps["governing_statute"] = None
                sec_copy["attribution_type"] = "unresolved"
                sec_copy["attribution_source"] = "no_statute_in_local_paragraph"
                sec_copy["confidence"] = "medium"
                resolved_sections.append(sec_copy)
                continue

            # Look at Acts in the same paragraph appearing before sec_start
            preceding_acts = [
                a["act_title"] for a in acts_by_para[p_idx]
                if a["end_char"] <= sec_start
            ]

            unique_preceding = list(dict.fromkeys(preceding_acts))

            if len(unique_preceding) == 1:
                # Exactly one unambiguous Act in preceding paragraph context!
                inherited_act = unique_preceding[0]
                sec_comps["governing_statute"] = inherited_act
                sec_copy["attribution_type"] = "inherited"
                sec_copy["attribution_source"] = "intra_paragraph_preceding_act"
                sec_copy["confidence"] = "high"
                sec_copy["normalized_reference"] = f"Section {sec_comps.get('section_numbers')} of {inherited_act}"
            elif len(unique_preceding) > 1:
                # Multiple Acts in preceding context -> Ambiguous! Do not guess.
                sec_comps["governing_statute"] = None
                sec_copy["attribution_type"] = "ambiguous"
                sec_copy["attribution_source"] = "multiple_preceding_acts_in_paragraph"
                sec_copy["candidate_statutes"] = unique_preceding
                sec_copy["confidence"] = "low"
            else:
                # Acts exist in paragraph but AFTER this section
                sec_comps["governing_statute"] = None
                sec_copy["attribution_type"] = "unresolved"
                sec_copy["attribution_source"] = "no_preceding_act_in_paragraph"
                sec_copy["confidence"] = "medium"

            resolved_sections.append(sec_copy)

        return resolved_sections
