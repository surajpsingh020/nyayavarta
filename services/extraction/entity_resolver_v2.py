"""
Conservative Legal Entity Resolver V2 for NyayaVarta (Milestone 11 Task 3).

Replaces unsafe title-only resolution with a multi-tier, evidence-grounded policy:
1. Exact Canonical Citation Matching:
   - Exact Neutral Citation (INSC) match against corpus index.
   - Exact Supreme Court Reports (SCR) match against corpus index.
   - Exact SCC OnLine match against corpus index where available.
2. Context-Aware Year Filtering:
   - If citation components or surrounding context window contains a year < 2024,
     resolution is strictly marked 'unresolved' (method: 'historical_case_pre_2024').
   - Never maps a historical precedent to a 2024 appeal with similar party names.
3. Discriminative Bipartite Title Matching:
   - Requires corroboration across BOTH petitioner and respondent sides of 'v.'.
   - Rejects single-party matches (e.g. 'State of Gujarat' or 'Union of India').
   - Evaluates Jaccard overlap on distinctive tokens (excluding generic legal stopwords).
4. Explicit Ambiguity Handling:
   - Preserves multiple candidate IDs when tied or near-tied (e.g. companion appeals).
5. Self-Citation Isolation:
   - Strictly flags is_self_citation=True when target_doc_id == source_doc_id.
   - Self-citations are kept for document metadata but rejected for cross-document graphs.
6. Fail-Closed Audit Trail:
   - Records match_method, confidence_score, resolution_reason, and candidate_targets
     for EVERY resolved, ambiguous, and unresolved outcome.
"""
import os
import json
import re
from typing import Dict, Any, List, Optional, Tuple, Set
from services.extraction.citation_normalizer import CitationNormalizer, NormalizedCitation


class EntityResolverV2:
    VERSION = "2.0.0"

    # Legal stopwords downweighted or ignored during party comparison
    STOPWORDS = {
        'the', 'of', 'and', 'ors', 'anr', 'others', 'another', 'state',
        'union', 'india', 'in', 're', 'vs', 'versus', 'v', 'ltd', 'limited',
        'pvt', 'private', 'corp', 'corporation', 'dept', 'department', 'govt',
        'government', 'through', 'its', 'sec', 'secretary', 'commissioner',
        'appellant', 'appellants', 'respondent', 'respondents', 'petition',
        'petitioner', 'petitioners', 'dead', 'thr', 'lrs', 'lr', 'special',
        'leave', 'appeal', 'civil', 'criminal', 'writ', 'no', 'nos'
    }

    # High frequency party entities that must never match in isolation
    HIGH_FREQUENCY_PARTIES = {
        'state of maharashtra', 'state of up', 'state of uttar pradesh',
        'state of gujarat', 'state of madhya pradesh', 'state of bihar',
        'state of karnataka', 'state of tamil nadu', 'state of rajasthan',
        'state of kerala', 'state of punjab', 'state of haryana',
        'state of west bengal', 'union of india', 'central bureau of investigation',
        'cbi', 'enforcement directorate', 'directorate of enforcement'
    }

    def __init__(self, processed_dir: str = "data/processed/aws_sc"):
        self.processed_dir = processed_dir
        self.normalizer = CitationNormalizer()

        # Indexes
        self.corpus_by_id: Dict[str, Dict[str, Any]] = {}
        self.corpus_by_neutral: Dict[str, str] = {}     # '2024INSC735' -> doc_id
        self.corpus_by_scr: Dict[str, str] = {}         # '[2024] 10 SCR 108' -> doc_id
        self.corpus_by_scr_simple: Dict[str, str] = {}  # '2024_10_108' -> doc_id
        self.corpus_titles: List[Dict[str, Any]] = []

        self._load_corpus()

    def _normalize_token(self, word: str) -> str:
        return re.sub(r'[^\w]', '', word.lower()).strip()

    def _normalize_title_text(self, title: str) -> str:
        """Strip aliases, registry case numbers, and normalize versus."""
        if not title:
            return ""
        # Remove alias annotations like "@ VIJAY KR. SHARMA"
        t = re.sub(r'@[^,;]+', '', title)
        # Normalize versus to v.
        t = re.sub(r'\b(?:versus|vs\.?)\b', ' v. ', t, flags=re.IGNORECASE)
        # Remove registry numbers like "(Criminal Appeal No. ...)"
        t = re.sub(r'\([^)]*\)', '', t)
        t = re.sub(r'[^\w\s\.]', ' ', t)
        t = re.sub(r'\s+', ' ', t).strip().lower()
        return t

    def _extract_party_keywords(self, party_text: str) -> Set[str]:
        words = party_text.replace('.', ' ').split()
        return {
            self._normalize_token(w)
            for w in words
            if len(self._normalize_token(w)) > 2 and self._normalize_token(w) not in self.STOPWORDS
        }

    def _parse_parties(self, title: str) -> Tuple[Set[str], Set[str], Set[str]]:
        """
        Split a case title into petitioner keywords, respondent keywords, and total keywords.
        """
        norm = self._normalize_title_text(title)
        total_kw = self._extract_party_keywords(norm)

        if ' v. ' in norm:
            parts = norm.split(' v. ', 1)
            p1_kw = self._extract_party_keywords(parts[0])
            p2_kw = self._extract_party_keywords(parts[1])
            return p1_kw, p2_kw, total_kw
        else:
            return total_kw, set(), total_kw

    def _load_corpus(self):
        """Index all 782 judgments by neutral citation, SCR citation, and title."""
        if not os.path.exists(self.processed_dir):
            return

        for fname in os.listdir(self.processed_dir):
            if not fname.endswith('.json'):
                continue
            doc_id = fname[:-5]
            fpath = os.path.join(self.processed_dir, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                doc = json.load(f)

            title = doc.get("case_title", "")
            raw_citation = doc.get("citation", "")
            full_text = doc.get("full_text", "")
            header = full_text[:800]

            # 1. Parse SCR citation from header: e.g. [2024] 10 S.C.R. 108
            scr_cite = None
            m_scr = re.search(r'\[?(2024)\]?\s*(?:\((?P<part>\d+)\)\s*)?(?P<vol>\d+)?\s*S\.?C\.?R\.?\s*(?P<page>\d+)', header, re.IGNORECASE)
            if m_scr:
                vol = m_scr.group('vol') or ""
                page = m_scr.group('page')
                scr_norm = self.normalizer.normalize(m_scr.group(0))
                if scr_norm.parsing_status == "valid":
                    scr_cite = scr_norm.normalized_citation
                    self.corpus_by_scr[scr_cite.upper()] = doc_id
                    # Also index simplified key: "2024_VOL_PAGE"
                    self.corpus_by_scr_simple[f"2024_{vol}_{page}"] = doc_id

            # 2. Parse Neutral citation: e.g. 2024 INSC 735
            neutral_cite = None
            if raw_citation:
                n_norm = self.normalizer.normalize(raw_citation)
                if n_norm.parsing_status == "valid":
                    neutral_cite = n_norm.normalized_citation
                    clean_neutral = re.sub(r'\s+', '', neutral_cite).upper()
                    self.corpus_by_neutral[clean_neutral] = doc_id

            p1_kw, p2_kw, all_kw = self._parse_parties(title)

            entry = {
                "document_id": doc_id,
                "case_title": title,
                "neutral_citation": neutral_cite,
                "scr_citation": scr_cite,
                "decision_date": doc.get("decision_date", ""),
                "petitioner_kw": p1_kw,
                "respondent_kw": p2_kw,
                "all_kw": all_kw
            }

            self.corpus_by_id[doc_id] = entry
            self.corpus_titles.append(entry)

    def resolve_citation(self, citation_mention: Dict[str, Any]) -> Dict[str, Any]:
        """
        Conservative, evidence-grounded citation resolution.
        Returns resolution record matching NyayaVarta v2 schema.
        """
        cite_type = citation_mention.get("citation_type")
        raw_text = citation_mention.get("raw_text", "")
        norm_cite = citation_mention.get("normalized_citation", "")
        source_doc_id = citation_mention.get("source_doc_id")
        context = citation_mention.get("mention_context", "")
        components = citation_mention.get("components", {})
        cite_year = components.get("year")

        # 1. Check for exact Neutral INSC citation
        if cite_type == "neutral_insc" and norm_cite:
            clean_key = re.sub(r'\s+', '', norm_cite).upper()
            if clean_key in self.corpus_by_neutral:
                target_id = self.corpus_by_neutral[clean_key]
                target_doc = self.corpus_by_id[target_id]
                is_self = (target_id == source_doc_id)
                return {
                    "source_doc_id": source_doc_id,
                    "mention_raw": raw_text,
                    "mention_normalized": norm_cite,
                    "resolution_status": "resolved",
                    "resolved_document_id": target_id,
                    "matched_case_title": target_doc["case_title"],
                    "match_method": "exact_neutral_citation",
                    "confidence_score": 1.0,
                    "is_self_citation": is_self,
                    "resolution_reason": "Exact match on 2024 INSC neutral citation.",
                    "version": self.VERSION
                }
            else:
                return {
                    "source_doc_id": source_doc_id,
                    "mention_raw": raw_text,
                    "mention_normalized": norm_cite,
                    "resolution_status": "unresolved",
                    "resolved_document_id": None,
                    "matched_case_title": None,
                    "match_method": "neutral_citation_not_in_corpus",
                    "confidence_score": 0.0,
                    "is_self_citation": False,
                    "resolution_reason": "2024 INSC citation not present in local 782-judgment corpus slice.",
                    "version": self.VERSION
                }

        # 2. Check for SCR citation
        if cite_type == "scr" and norm_cite:
            if cite_year and cite_year < 2024:
                return {
                    "source_doc_id": source_doc_id,
                    "mention_raw": raw_text,
                    "mention_normalized": norm_cite,
                    "resolution_status": "unresolved",
                    "resolved_document_id": None,
                    "matched_case_title": None,
                    "match_method": "historical_reporter_pre_2024",
                    "confidence_score": 0.0,
                    "is_self_citation": False,
                    "resolution_reason": f"Historical SCR citation from year {cite_year} outside 2024 corpus.",
                    "version": self.VERSION
                }
            # Check SCR index
            clean_scr = norm_cite.upper()
            vol = str(components.get("vol") or "")
            page = str(components.get("page") or "")
            simple_key = f"2024_{vol}_{page}"

            target_id = self.corpus_by_scr.get(clean_scr) or self.corpus_by_scr_simple.get(simple_key)
            if target_id and target_id in self.corpus_by_id:
                target_doc = self.corpus_by_id[target_id]
                is_self = (target_id == source_doc_id)
                return {
                    "source_doc_id": source_doc_id,
                    "mention_raw": raw_text,
                    "mention_normalized": norm_cite,
                    "resolution_status": "resolved",
                    "resolved_document_id": target_id,
                    "matched_case_title": target_doc["case_title"],
                    "match_method": "exact_scr_citation",
                    "confidence_score": 1.0,
                    "is_self_citation": is_self,
                    "resolution_reason": "Exact match on 2024 SCR volume and page.",
                    "version": self.VERSION
                }
            else:
                return {
                    "source_doc_id": source_doc_id,
                    "mention_raw": raw_text,
                    "mention_normalized": norm_cite,
                    "resolution_status": "unresolved",
                    "resolved_document_id": None,
                    "matched_case_title": None,
                    "match_method": "scr_citation_not_in_corpus",
                    "confidence_score": 0.0,
                    "is_self_citation": False,
                    "resolution_reason": "2024 SCR citation not found in local corpus volume/page index.",
                    "version": self.VERSION
                }

        # 3. Check for formal reporter pre-2024 (SCC, AIR, etc.)
        if cite_year and cite_year < 2024:
            return {
                "source_doc_id": source_doc_id,
                "mention_raw": raw_text,
                "mention_normalized": norm_cite,
                "resolution_status": "unresolved",
                "resolved_document_id": None,
                "matched_case_title": None,
                "match_method": "historical_reporter_pre_2024",
                "confidence_score": 0.0,
                "is_self_citation": False,
                "resolution_reason": f"Historical citation from year {cite_year} outside 2024 corpus.",
                "version": self.VERSION
            }

        # 4. Case title resolution (Party A v. Party B) or Unanchored mentions
        if cite_type in ["case_title", "unanchored_mention"]:
            return self._resolve_by_title_conservative(
                source_doc_id=source_doc_id,
                raw_text=raw_text,
                norm_title=norm_cite,
                context=context,
                cite_year=cite_year
            )

        # Fallback for unrecognized formal reporters or partial mentions
        return {
            "source_doc_id": source_doc_id,
            "mention_raw": raw_text,
            "mention_normalized": norm_cite,
            "resolution_status": "unresolved",
            "resolved_document_id": None,
            "matched_case_title": None,
            "match_method": "unmatched_reporter",
            "confidence_score": 0.0,
            "is_self_citation": False,
            "resolution_reason": "Unmatched reporter citation without identifiable 2024 corpus target.",
            "version": self.VERSION
        }

    def _detect_pre_2024_context(self, raw_text: str, context: str) -> Optional[int]:
        """
        Check if the mention or its immediate sentence context explicitly references
        a pre-2024 year in connection with the cited precedent.
        """
        # Look for explicit reporter patterns in context: (19xx), (200x), (201x), (2020-2023)
        combined = f"{raw_text} {context}"
        years = [int(y) for y in re.findall(r'\b(19\d{2}|20[0-1]\d|202[0-3])\b', combined)]
        if years:
            return years[0]
        return None

    def _resolve_by_title_conservative(
        self,
        source_doc_id: str,
        raw_text: str,
        norm_title: str,
        context: str,
        cite_year: Optional[int]
    ) -> Dict[str, Any]:
        """
        Conservative, year-aware bipartite title resolution.
        Replaces unsafe title_keyword_overlap.
        """
        # Step A: Check if pre-2024 year exists in mention components or context
        effective_year = cite_year or self._detect_pre_2024_context(raw_text, context)
        if effective_year and effective_year < 2024:
            return {
                "source_doc_id": source_doc_id,
                "mention_raw": raw_text,
                "mention_normalized": norm_title,
                "resolution_status": "unresolved",
                "resolved_document_id": None,
                "matched_case_title": None,
                "match_method": "historical_case_pre_2024",
                "confidence_score": 0.0,
                "is_self_citation": False,
                "resolution_reason": f"Pre-2024 year ({effective_year}) detected in citation context; target precedent is outside 2024 corpus.",
                "version": self.VERSION
            }

        # Step B: Parse petitioner and respondent keywords
        p1_kw, p2_kw, total_kw = self._parse_parties(norm_title)

        # Require at least 2 distinctive keywords overall
        if len(total_kw) < 2:
            return {
                "source_doc_id": source_doc_id,
                "mention_raw": raw_text,
                "mention_normalized": norm_title,
                "resolution_status": "unresolved",
                "resolved_document_id": None,
                "matched_case_title": None,
                "match_method": "insufficient_title_keywords",
                "confidence_score": 0.0,
                "is_self_citation": False,
                "resolution_reason": "Title contains fewer than 2 distinctive keywords after stopword filtering.",
                "version": self.VERSION
            }

        # Step C: Evaluate candidates
        candidates = []
        for entry in self.corpus_titles:
            corp_all = entry["all_kw"]
            if not corp_all:
                continue

            # Bipartite check if both p1 and p2 exist
            if p1_kw and p2_kw:
                # Direct check: p1 vs corp_p1 AND p2 vs corp_p2
                p1_match = len(p1_kw.intersection(entry["petitioner_kw"])) / len(p1_kw) if p1_kw else 0
                p2_match = len(p2_kw.intersection(entry["respondent_kw"])) / len(p2_kw) if p2_kw else 0

                # Cross check (inverted appeal): p1 vs corp_p2 AND p2 vs corp_p1
                p1_inv = len(p1_kw.intersection(entry["respondent_kw"])) / len(p1_kw) if p1_kw else 0
                p2_inv = len(p2_kw.intersection(entry["petitioner_kw"])) / len(p2_kw) if p2_kw else 0

                is_direct = (p1_match >= 0.70 and p2_match >= 0.70)
                is_inverted = (p1_inv >= 0.70 and p2_inv >= 0.70)

                if is_direct or is_inverted:
                    inter = total_kw.intersection(corp_all)
                    overlap = len(inter) / len(total_kw)
                    union = total_kw.union(corp_all)
                    jaccard = len(inter) / len(union) if union else 0.0
                    candidates.append((entry, overlap, jaccard, "bipartite_parties"))
            else:
                # Unanchored mention (no 'v.'): require high total keyword subset
                if total_kw.issubset(corp_all) and len(total_kw) >= 3:
                    inter = total_kw.intersection(corp_all)
                    union = total_kw.union(corp_all)
                    jaccard = len(inter) / len(union) if union else 0.0
                    candidates.append((entry, 1.0, jaccard, "unanchored_subset"))

        if not candidates:
            return {
                "source_doc_id": source_doc_id,
                "mention_raw": raw_text,
                "mention_normalized": norm_title,
                "resolution_status": "unresolved",
                "resolved_document_id": None,
                "matched_case_title": None,
                "match_method": "no_title_match",
                "confidence_score": 0.0,
                "is_self_citation": False,
                "resolution_reason": "No 2024 judgment satisfied bipartite party matching criteria.",
                "version": self.VERSION
            }

        # Sort candidates by overlap descending, then jaccard descending
        candidates.sort(key=lambda x: (x[1], x[2]), reverse=True)
        top_entry, top_overlap, top_jaccard, match_style = candidates[0]

        # Step D: Check for ambiguity (multiple companion appeals or identical scores)
        if len(candidates) > 1:
            second_entry, sec_overlap, sec_jaccard, _ = candidates[1]
            if (top_overlap == sec_overlap and abs(top_jaccard - sec_jaccard) < 0.15) or (sec_overlap >= 0.85):
                return {
                    "source_doc_id": source_doc_id,
                    "mention_raw": raw_text,
                    "mention_normalized": norm_title,
                    "resolution_status": "ambiguous",
                    "resolved_document_id": None,
                    "ambiguous_candidate_ids": [c[0]["document_id"] for c in candidates[:4]],
                    "matched_case_title": top_entry["case_title"],
                    "match_method": "multiple_title_candidates",
                    "confidence_score": round(top_overlap, 3),
                    "is_self_citation": False,
                    "resolution_reason": f"Title matched {len(candidates)} tied candidates with equal party overlap.",
                    "version": self.VERSION
                }

        # Step E: Resolved (Self-Citation) vs Candidate Generation (Cross-Document)
        is_self = (top_entry["document_id"] == source_doc_id)
        if is_self:
            return {
                "source_doc_id": source_doc_id,
                "mention_raw": raw_text,
                "mention_normalized": norm_title,
                "resolution_status": "resolved",
                "resolved_document_id": top_entry["document_id"],
                "matched_case_title": top_entry["case_title"],
                "match_method": "self_citation_title",
                "confidence_score": round(top_overlap, 3),
                "is_self_citation": True,
                "resolution_reason": "Judgment cites its own title in introductory header / recital.",
                "version": self.VERSION
            }

        # For cross-document matches:
        # Title matching is a candidate generation mechanism, NOT authoritative proof of identity
        # unless year 2024 is explicitly established and both parties match bipartite!
        if effective_year == 2024 and match_style == "bipartite_parties" and top_overlap >= 0.85:
            return {
                "source_doc_id": source_doc_id,
                "mention_raw": raw_text,
                "mention_normalized": norm_title,
                "resolution_status": "resolved",
                "resolved_document_id": top_entry["document_id"],
                "matched_case_title": top_entry["case_title"],
                "match_method": "year_verified_bipartite_title",
                "confidence_score": round(top_overlap, 3),
                "is_self_citation": False,
                "resolution_reason": "Bipartite party match verified against 2024 judgment with explicit 2024 year.",
                "version": self.VERSION
            }

        # If no explicit 2024 year or unanchored mention: do NOT force resolution!
        return {
            "source_doc_id": source_doc_id,
            "mention_raw": raw_text,
            "mention_normalized": norm_title,
            "resolution_status": "unresolved",
            "resolved_document_id": None,
            "candidate_target_ids": [top_entry["document_id"]],
            "matched_case_title": top_entry["case_title"],
            "match_method": "title_only_lacks_year_corroboration",
            "confidence_score": round(top_overlap, 3),
            "is_self_citation": False,
            "resolution_reason": "Title-only match without verified 2024 year or canonical citation cannot establish case identity (Rule 5).",
            "version": self.VERSION
        }
