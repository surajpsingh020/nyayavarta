"""
Conservative Legal Entity Resolver for NyayaVarta (Milestone 4A).

Resolves extracted citation mentions and case titles against the 782 canonical
judgments in the existing corpus.

States:
- resolved:   Uniquely linked to exactly one document in the corpus.
- ambiguous:  Matches multiple documents with close confidence (e.g., related appeals).
- unresolved: Reference to a pre-2024 decision, High Court ruling, or not present in corpus.

Guarantees:
- Never fabricates target documents.
- Never silently merges cases with similar titles.
"""
import os
import json
import re
from typing import Dict, Any, List, Optional, Tuple


class EntityResolver:
    VERSION = "1.0.0"

    # Stopwords to downweight/strip when comparing case titles
    STOPWORDS = {
        'the', 'of', 'and', 'ors', 'anr', 'others', 'another', 'state',
        'union', 'india', 'in', 're', 'vs', 'versus', 'v', 'ltd', 'limited',
        'pvt', 'private', 'corp', 'corporation', 'dept', 'department', 'govt',
        'government', 'through', 'its', 'sec', 'secretary'
    }

    def __init__(self, processed_dir: str = "data/processed/aws_sc"):
        self.processed_dir = processed_dir
        self.corpus_by_id = {}
        self.corpus_by_neutral = {}
        self.corpus_titles = []
        self._load_corpus()

    def _normalize_title(self, title: str) -> str:
        """Normalize a case title for indexing and matching."""
        if not title:
            return ""
        # Remove alias annotations like "@ VIJAY KR. SHARMA"
        t = re.sub(r'@[^,;]+', '', title)
        # Normalize versus to v.
        t = re.sub(r'\b(?:versus|vs\.?)\b', 'v.', t, flags=re.IGNORECASE)
        # Remove registry numbers like "(Criminal Appeal No. ...)"
        t = re.sub(r'\([^)]*\)', '', t)
        # Clean punctuation
        t = re.sub(r'[^\w\s\.]', ' ', t)
        t = re.sub(r'\s+', ' ', t).strip().lower()
        return t

    def _get_title_keywords(self, title: str) -> set:
        """Extract distinguishing keywords from a title."""
        norm = self._normalize_title(title)
        words = norm.replace('.', ' ').split()
        return {w for w in words if len(w) > 2 and w not in self.STOPWORDS}

    def _load_corpus(self):
        """Index all documents in the processed directory."""
        if not os.path.exists(self.processed_dir):
            return

        for fname in os.listdir(self.processed_dir):
            if not fname.endswith('.json'):
                continue
            fpath = os.path.join(self.processed_dir, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                doc = json.load(f)

            doc_id = doc.get("document_id")
            title = doc.get("case_title", "")
            raw_citation = doc.get("citation", "")
            decision_date = doc.get("decision_date", "")

            # Store document summary
            entry = {
                "document_id": doc_id,
                "case_title": title,
                "citation": raw_citation,
                "decision_date": decision_date,
                "norm_title": self._normalize_title(title),
                "keywords": self._get_title_keywords(title)
            }

            self.corpus_by_id[doc_id] = entry

            # Index by neutral citation: e.g., '2024INSC735'
            if raw_citation:
                clean_cite = re.sub(r'\s+', '', raw_citation).upper()
                self.corpus_by_neutral[clean_cite] = doc_id

            self.corpus_titles.append(entry)

    def resolve_citation(self, citation_mention: Dict[str, Any]) -> Dict[str, Any]:
        """
        Attempt to resolve an extracted citation to a corpus document.
        Returns resolution record with status: 'resolved', 'ambiguous', or 'unresolved'.
        """
        cite_type = citation_mention.get("citation_type")
        raw_text = citation_mention.get("raw_text", "")
        norm_cite = citation_mention.get("normalized_citation", "")
        source_doc_id = citation_mention.get("source_doc_id")

        # 1. Neutral INSC match
        if cite_type == "neutral_insc" and norm_cite:
            clean_key = re.sub(r'\s+', '', norm_cite).upper()
            if clean_key in self.corpus_by_neutral:
                target_id = self.corpus_by_neutral[clean_key]
                # Avoid self-reference as a precedent target
                target_doc = self.corpus_by_id[target_id]
                return {
                    "source_doc_id": source_doc_id,
                    "mention_raw": raw_text,
                    "mention_normalized": norm_cite,
                    "resolution_status": "resolved",
                    "resolved_document_id": target_id,
                    "matched_case_title": target_doc["case_title"],
                    "match_method": "exact_neutral_citation",
                    "confidence_score": 1.0,
                    "is_self_citation": (target_id == source_doc_id),
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
                    "version": self.VERSION
                }

        # 2. Case title resolution (Party A v. Party B)
        if cite_type == "case_title" and norm_cite:
            return self._resolve_by_title(source_doc_id, raw_text, norm_cite)

        # 3. Unanchored mention
        if cite_type == "unanchored_mention" and norm_cite:
            return self._resolve_by_unanchored(source_doc_id, raw_text, norm_cite)

        # 4. Formal reporters (SCC, AIR, SCR) without neutral key
        # Check if year is 2024; pre-2024 citations are guaranteed unresolved in 2024 corpus
        components = citation_mention.get("components", {})
        cite_year = components.get("year")
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
                "version": self.VERSION
            }

        # Fallback: unresolved
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
            "version": self.VERSION
        }

    def _resolve_by_title(self, source_doc_id: str, raw_text: str, norm_title: str) -> Dict[str, Any]:
        """Match case title against corpus titles conservatively."""
        mention_keywords = self._get_title_keywords(norm_title)
        if len(mention_keywords) < 2:
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
                "version": self.VERSION
            }

        candidates = []
        for entry in self.corpus_titles:
            corp_kw = entry["keywords"]
            if not corp_kw:
                continue

            intersection = mention_keywords.intersection(corp_kw)
            union = mention_keywords.union(corp_kw)
            jaccard = len(intersection) / len(union) if union else 0.0
            overlap = len(intersection) / len(mention_keywords)

            # High confidence requires high overlap with mention
            if overlap >= 0.80 and len(intersection) >= 2:
                candidates.append((entry, overlap, jaccard))

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
                "version": self.VERSION
            }

        # Sort by overlap descending, then jaccard descending
        candidates.sort(key=lambda x: (x[1], x[2]), reverse=True)
        top_entry, top_overlap, top_jaccard = candidates[0]

        # Check for ambiguity: if second candidate has same or near-identical score
        if len(candidates) > 1:
            second_entry, second_overlap, second_jaccard = candidates[1]
            if top_overlap == second_overlap and abs(top_jaccard - second_jaccard) < 0.05:
                return {
                    "source_doc_id": source_doc_id,
                    "mention_raw": raw_text,
                    "mention_normalized": norm_title,
                    "resolution_status": "ambiguous",
                    "resolved_document_id": None,
                    "ambiguous_candidate_ids": [c[0]["document_id"] for c in candidates[:3]],
                    "matched_case_title": top_entry["case_title"],
                    "match_method": "multiple_title_candidates",
                    "confidence_score": round(top_overlap, 3),
                    "is_self_citation": False,
                    "version": self.VERSION
                }

        # Resolved
        is_self = (top_entry["document_id"] == source_doc_id)
        return {
            "source_doc_id": source_doc_id,
            "mention_raw": raw_text,
            "mention_normalized": norm_title,
            "resolution_status": "resolved",
            "resolved_document_id": top_entry["document_id"],
            "matched_case_title": top_entry["case_title"],
            "match_method": "title_keyword_overlap",
            "confidence_score": round(top_overlap, 3),
            "is_self_citation": is_self,
            "version": self.VERSION
        }

    def _resolve_by_unanchored(self, source_doc_id: str, raw_text: str, case_name: str) -> Dict[str, Any]:
        """Resolve unanchored reference like 'in the case of X'."""
        keywords = self._get_title_keywords(case_name)
        if len(keywords) < 2:
            return {
                "source_doc_id": source_doc_id,
                "mention_raw": raw_text,
                "mention_normalized": case_name,
                "resolution_status": "unresolved",
                "resolved_document_id": None,
                "matched_case_title": None,
                "match_method": "unanchored_insufficient_keywords",
                "confidence_score": 0.0,
                "is_self_citation": False,
                "version": self.VERSION
            }

        candidates = []
        for entry in self.corpus_titles:
            corp_kw = entry["keywords"]
            if keywords.issubset(corp_kw):
                candidates.append(entry)

        if len(candidates) == 1:
            match = candidates[0]
            return {
                "source_doc_id": source_doc_id,
                "mention_raw": raw_text,
                "mention_normalized": case_name,
                "resolution_status": "resolved",
                "resolved_document_id": match["document_id"],
                "matched_case_title": match["case_title"],
                "match_method": "unanchored_unique_keyword_match",
                "confidence_score": 0.85,
                "is_self_citation": (match["document_id"] == source_doc_id),
                "version": self.VERSION
            }
        elif len(candidates) > 1:
            return {
                "source_doc_id": source_doc_id,
                "mention_raw": raw_text,
                "mention_normalized": case_name,
                "resolution_status": "ambiguous",
                "resolved_document_id": None,
                "ambiguous_candidate_ids": [c["document_id"] for c in candidates[:3]],
                "matched_case_title": candidates[0]["case_title"],
                "match_method": "unanchored_multiple_candidates",
                "confidence_score": 0.5,
                "is_self_citation": False,
                "version": self.VERSION
            }
        else:
            return {
                "source_doc_id": source_doc_id,
                "mention_raw": raw_text,
                "mention_normalized": case_name,
                "resolution_status": "unresolved",
                "resolved_document_id": None,
                "matched_case_title": None,
                "match_method": "unanchored_no_corpus_match",
                "confidence_score": 0.0,
                "is_self_citation": False,
                "version": self.VERSION
            }
