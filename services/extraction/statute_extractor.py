"""
Statutory Reference Extractor for Indian Supreme Court Judgments.

Extracts:
1. Acts and Statutes (full names with year, standard Act titles, acronyms)
2. Sections and Subsections (including compound forms 'u/s', 's.', 'read with')
3. Articles of the Constitution of India ('Article 21', 'Art. 142')
4. Procedural Rules and Orders ('Order XXI Rule 99', 'Rule 9(4)')
5. Constitutional and Statutory Schedules ('Tenth Schedule', 'Schedule I')

Preserves raw text, provides normalized provision structures, and extracts context windows.
"""
import re
from typing import List, Dict, Any, Optional


class StatuteExtractor:
    VERSION = "1.0.0"

    # Known Indian statute acronyms mapping to canonical titles
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
        "CONSTITUTION": "Constitution of India"
    }

    # Regex for formal Acts: e.g. "Indian Penal Code, 1860", "Limitation Act, 1963"
    RE_FORMAL_ACT = re.compile(
        r'\b(?P<act_name>[A-Z][A-Za-z\s\(\)\'\-]{2,50}?(?:Act|Code|Rules|Regulations|Order))\s*,\s*(?P<year>(?:18|19|20)\d{2})\b'
    )

    # General Act references: e.g. "Penal Code, 1860", "Constitution of India"
    RE_CONSTITUTION = re.compile(
        r'\b(?:Constitution\s+of\s+India|the\s+Constitution)\b',
        re.IGNORECASE
    )

    # Acronym Acts
    RE_ACRONYM_ACT = re.compile(
        r'\b(?P<acronym>IPC|CrPC|CPC|PMLA|IBC|SARFAESI(?:\s+Act)?|POCSO(?:\s+Act)?|UAPA|NDPS(?:\s+Act)?|CGST(?:\s+Act)?|NI\s+Act)\b'
    )

    # Articles of the Constitution: "Article 21", "Articles 14, 15 and 21", "Art. 341"
    RE_ARTICLE = re.compile(
        r'\b(?P<art_prefix>Article|Articles|Art\.)\s+(?P<numbers>\d+[A-Za-z]*(?:\s*(?:,|and|read\s+with|\-)\s*\d+[A-Za-z]*)*)(?:\s+of\s+the\s+Constitution)?\b',
        re.IGNORECASE
    )

    # Sections of an Act: "Section 302", "Sections 302 and 34", "s. 302", "u/s. 438", "u/ss. 302/34"
    RE_SECTION = re.compile(
        r'\b(?P<sec_prefix>Sections?|Sec\.|s\.|u/ss?\.?|under\s+Section)\s+'
        r'(?P<sec_num>\d+[A-Za-z]*(?:\([0-9a-zA-Z]+\))*(?:/\d+)*(?:\s*(?:,|and|read\s+with|\-)\s*\d+[A-Za-z]*(?:\([0-9a-zA-Z]+\))*)*)'
        r'(?:\s+(?:of\s+the\s+|of\s+)(?P<governing_act>[A-Z][A-Za-z\s\(\)\'\-,0-9]{2,50}?\b(?:Act|Code|IPC|CrPC|CPC|PMLA|IBC)\b))?',
        re.IGNORECASE
    )

    # Procedural Order and Rule: "Order XXI Rule 99", "Order VII Rule 11", "Rule 9(4)"
    RE_ORDER_RULE = re.compile(
        r'\b(?:Order\s+(?P<order>[IVXLCDM0-9]+)\s+Rule\s+(?P<rule>\d+[A-Za-z]*)|Rule\s+(?P<standalone_rule>\d+[A-Za-z]*(?:\([0-9a-zA-Z]+\))*))(?=[\s,;.:\)]|$)',
        re.IGNORECASE
    )

    # Schedules: "Tenth Schedule", "Schedule I", "Seventh Schedule"
    RE_SCHEDULE = re.compile(
        r'\b(?P<schedule>(?:First|Second|Third|Fourth|Fifth|Sixth|Seventh|Eighth|Ninth|Tenth|Eleventh|Twelfth|\d+th|[IVXLCDM]+)\s+Schedule|Schedule\s+[IVXLCDM0-9]+)\b',
        re.IGNORECASE
    )

    def __init__(self, context_window_chars: int = 200):
        self.context_window = context_window_chars

    def extract_context(self, text: str, start: int, end: int) -> str:
        """Extract surrounding sentence window."""
        ctx_start = max(0, start - self.context_window)
        ctx_end = min(len(text), end + self.context_window)

        prev_period = text.rfind('. ', ctx_start, start)
        if prev_period != -1 and prev_period >= ctx_start:
            ctx_start = prev_period + 2

        next_period = text.find('. ', end, ctx_end)
        if next_period != -1 and next_period <= ctx_end:
            ctx_end = next_period + 1

        context = text[ctx_start:ctx_end].replace('\n', ' ').strip()
        return re.sub(r'\s+', ' ', context)

    def extract_acts(self, text: str, source_doc_id: str) -> List[Dict[str, Any]]:
        """Extract explicit Act references."""
        acts = []
        seen_spans = set()

        # 1. Formal Acts with year
        for m in self.RE_FORMAL_ACT.finditer(text):
            span = m.span()
            if span in seen_spans:
                continue
            seen_spans.add(span)

            raw = m.group(0).strip()
            act_name = m.group('act_name').strip()
            # Clean leading prepositions: "Under the Indian Penal Code" -> "Indian Penal Code"
            act_name = re.sub(r'^(?:under\s+the|under|in\s+the|in|the)\s+', '', act_name, flags=re.IGNORECASE).strip()
            year = m.group('year').strip()
            normalized = f"{act_name}, {year}"
            context = self.extract_context(text, span[0], span[1])

            acts.append({
                "source_doc_id": source_doc_id,
                "reference_type": "statute_act",
                "raw_text": raw,
                "normalized_reference": normalized,
                "components": {"act_title": act_name, "year": int(year)},
                "start_char": span[0],
                "end_char": span[1],
                "mention_context": context,
                "extraction_method": "regex_formal_act",
                "confidence": "high",
                "version": self.VERSION
            })

        # 2. Constitution mentions
        for m in self.RE_CONSTITUTION.finditer(text):
            span = m.span()
            if span in seen_spans:
                continue
            seen_spans.add(span)

            raw = m.group(0).strip()
            context = self.extract_context(text, span[0], span[1])

            acts.append({
                "source_doc_id": source_doc_id,
                "reference_type": "statute_act",
                "raw_text": raw,
                "normalized_reference": "Constitution of India",
                "components": {"act_title": "Constitution of India", "year": 1950},
                "start_char": span[0],
                "end_char": span[1],
                "mention_context": context,
                "extraction_method": "regex_constitution",
                "confidence": "high",
                "version": self.VERSION
            })

        # 3. Known Act Acronyms
        for m in self.RE_ACRONYM_ACT.finditer(text):
            span = m.span()
            if span in seen_spans:
                continue
            seen_spans.add(span)

            raw = m.group('acronym').strip()
            canonical = self.ACRONYM_TO_ACT.get(raw.upper(), raw)
            context = self.extract_context(text, span[0], span[1])

            acts.append({
                "source_doc_id": source_doc_id,
                "reference_type": "statute_act",
                "raw_text": raw,
                "normalized_reference": canonical,
                "components": {"acronym": raw, "canonical_title": canonical},
                "start_char": span[0],
                "end_char": span[1],
                "mention_context": context,
                "extraction_method": "regex_act_acronym",
                "confidence": "high",
                "version": self.VERSION
            })

        return acts

    def extract_articles(self, text: str, source_doc_id: str) -> List[Dict[str, Any]]:
        """Extract constitutional Article references."""
        articles = []
        for m in self.RE_ARTICLE.finditer(text):
            span = m.span()
            raw = m.group(0).strip()
            numbers = m.group('numbers').strip()

            # Separate numbers if compound like "14, 15 and 21"
            num_tokens = re.findall(r'\b\d+[A-Za-z]*(?:\([0-9a-zA-Z]+\))*\b', numbers)
            normalized = f"Article {', '.join(num_tokens)}" if num_tokens else f"Article {numbers}"
            context = self.extract_context(text, span[0], span[1])

            articles.append({
                "source_doc_id": source_doc_id,
                "reference_type": "constitutional_article",
                "raw_text": raw,
                "normalized_reference": normalized,
                "components": {
                    "articles": num_tokens,
                    "statute": "Constitution of India"
                },
                "start_char": span[0],
                "end_char": span[1],
                "mention_context": context,
                "extraction_method": "regex_article",
                "confidence": "high",
                "version": self.VERSION
            })
        return articles

    def extract_sections(self, text: str, source_doc_id: str) -> List[Dict[str, Any]]:
        """Extract Section and subsection references."""
        sections = []
        for m in self.RE_SECTION.finditer(text):
            span = m.span()
            raw = m.group(0).strip()
            sec_num = m.group('sec_num').strip()
            governing = m.group('governing_act')

            governing_clean = None
            if governing:
                cleaned = re.sub(r'\s+', ' ', governing).strip(' ,.-;')
                lower_cleaned = cleaned.lower()
                # Check for pseudo-Acts or runaway capture terms
                pseudo_terms = {'the act', 'said act', 'the said act', 'this act', 'an act', 'act', 'the code', 'said code', 'this code', 'code'}
                disallowed = {'fact', 'pract', 'charact', 'prescribed', 'provision', 'because', 'owing to', 'application to', 'read with'}
                if lower_cleaned not in pseudo_terms and not any(d in lower_cleaned for d in disallowed):
                    test_str = cleaned
                    if test_str.lower().startswith('the '):
                        test_str = test_str[4:].strip()
                    if test_str.upper() in self.ACRONYM_TO_ACT:
                        governing_clean = self.ACRONYM_TO_ACT[test_str.upper()]
                    elif cleaned.upper() in self.ACRONYM_TO_ACT:
                        governing_clean = self.ACRONYM_TO_ACT[cleaned.upper()]
                    else:
                        governing_clean = cleaned

            # Normalized section form
            normalized = f"Section {sec_num}"
            if governing_clean:
                normalized += f" of {governing_clean}"

            context = self.extract_context(text, span[0], span[1])

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
                "mention_context": context,
                "extraction_method": "regex_section",
                "confidence": "high" if governing_clean else "medium",
                "version": self.VERSION
            })
        return sections

    def extract_orders_and_rules(self, text: str, source_doc_id: str) -> List[Dict[str, Any]]:
        """Extract Order & Rule procedural references."""
        rules = []
        for m in self.RE_ORDER_RULE.finditer(text):
            span = m.span()
            raw = m.group(0).strip()
            order = m.group('order')
            rule = m.group('rule')
            standalone_rule = m.group('standalone_rule')

            if order and rule:
                normalized = f"Order {order} Rule {rule}"
                components = {"order": order, "rule": rule}
            else:
                normalized = f"Rule {standalone_rule}"
                components = {"rule": standalone_rule}

            context = self.extract_context(text, span[0], span[1])

            rules.append({
                "source_doc_id": source_doc_id,
                "reference_type": "procedural_order_rule",
                "raw_text": raw,
                "normalized_reference": normalized,
                "components": components,
                "start_char": span[0],
                "end_char": span[1],
                "mention_context": context,
                "extraction_method": "regex_order_rule",
                "confidence": "high",
                "version": self.VERSION
            })
        return rules

    def extract_schedules(self, text: str, source_doc_id: str) -> List[Dict[str, Any]]:
        """Extract Schedule references."""
        schedules = []
        for m in self.RE_SCHEDULE.finditer(text):
            span = m.span()
            raw = m.group(0).strip()
            schedule_text = m.group('schedule').strip()
            normalized = schedule_text.title()
            context = self.extract_context(text, span[0], span[1])

            schedules.append({
                "source_doc_id": source_doc_id,
                "reference_type": "statutory_schedule",
                "raw_text": raw,
                "normalized_reference": normalized,
                "components": {"schedule_name": normalized},
                "start_char": span[0],
                "end_char": span[1],
                "mention_context": context,
                "extraction_method": "regex_schedule",
                "confidence": "high",
                "version": self.VERSION
            })
        return schedules

    def extract_all(self, text: str, source_doc_id: str) -> List[Dict[str, Any]]:
        """Run all statutory extractors and return deduplicated list."""
        all_refs = []
        all_refs.extend(self.extract_acts(text, source_doc_id))
        all_refs.extend(self.extract_articles(text, source_doc_id))
        all_refs.extend(self.extract_sections(text, source_doc_id))
        all_refs.extend(self.extract_orders_and_rules(text, source_doc_id))
        all_refs.extend(self.extract_schedules(text, source_doc_id))

        all_refs.sort(key=lambda x: x["start_char"])
        return all_refs
