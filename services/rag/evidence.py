"""
Evidence Assembly and Passage Extraction for NyayaVarta RAG (Milestone 5A).

Extracts relevant passages from canonical judgment full texts, preserving exact
character offsets, deduplicating overlapping spans, and enforcing 100% offset fidelity.
"""
import os
import json
import re
from typing import List, Dict, Any, Optional, Tuple, Set
from services.rag.models import EvidencePassage
from services.rag.structure import JudgmentStructureParser, StructuralRegionType

CORPUS_DIR = "data/processed/aws_sc"


class EvidenceAssembler:
    def __init__(
        self,
        corpus_dir: str = CORPUS_DIR,
        target_passage_chars: int = 800,
        min_passage_chars: int = 120,
        max_passages_per_doc: int = 2,
        total_max_passages: int = 5,
        enable_structure_aware: bool = True
    ):
        self.corpus_dir = corpus_dir
        self.target_passage_chars = target_passage_chars
        self.min_passage_chars = min_passage_chars
        self.max_passages_per_doc = max_passages_per_doc
        self.total_max_passages = total_max_passages
        self.enable_structure_aware = enable_structure_aware

    def _load_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Load canonical judgment JSON."""
        fpath = os.path.join(self.corpus_dir, f"{doc_id}.json")
        if not os.path.exists(fpath):
            return None
        with open(fpath, "r", encoding="utf-8") as f:
            return json.load(f)

    def _extract_candidate_spans(self, full_text: str) -> List[Tuple[int, int, str]]:
        """
        Split full text into coherent candidate passage spans with exact character offsets.
        Preserves exact substring: full_text[start:end] == span_text.
        """
        spans = []
        text_len = len(full_text)
        if text_len == 0:
            return spans

        # Split along double newlines or paragraph boundaries
        para_pattern = re.compile(r'\n\s*\n')
        last_end = 0

        for match in para_pattern.finditer(full_text):
            start = last_end
            end = match.start()
            last_end = match.end()

            span_text = full_text[start:end].strip()
            # Find exact character offsets of non-whitespace substring
            if len(span_text) >= self.min_passage_chars:
                # Find start of stripped content
                content_start = full_text.find(span_text, start, end)
                if content_start != -1:
                    content_end = content_start + len(span_text)
                    spans.append((content_start, content_end, span_text))

        # Trailing span
        if last_end < text_len:
            trailing = full_text[last_end:].strip()
            if len(trailing) >= self.min_passage_chars:
                c_start = full_text.find(trailing, last_end)
                if c_start != -1:
                    spans.append((c_start, c_start + len(trailing), trailing))

        # Fallback if no natural paragraphs were found: fixed-window sliding spans
        if not spans and text_len >= self.min_passage_chars:
            step = self.target_passage_chars // 2
            for i in range(0, text_len, step):
                chunk = full_text[i:i + self.target_passage_chars]
                if len(chunk.strip()) >= self.min_passage_chars:
                    spans.append((i, i + len(chunk), chunk))

        return spans

    def _score_passage(
        self,
        passage_text: str,
        query_tokens: Set[str],
        structural_label: Optional[str] = None,
        is_quoted: bool = False
    ) -> float:
        """
        Score a passage by keyword overlap and structural authority.
        """
        if not passage_text or not query_tokens:
            return 0.0

        p_lower = passage_text.lower()
        tokens = set(re.findall(r'\b[a-z0-9]+\b', p_lower))
        
        # Token overlap score
        overlap = len(tokens.intersection(query_tokens))
        score = float(overlap)

        # Structural weighting when structural classification is active
        if structural_label:
            if structural_label in (StructuralRegionType.HEADNOTE_HOLDING, StructuralRegionType.JUDICIAL_HOLDING):
                score += 4.0
            elif structural_label == StructuralRegionType.COURT_ANALYSIS:
                score += 2.5
            elif structural_label == StructuralRegionType.ISSUE_FRAMING:
                score += 2.0
            elif structural_label == StructuralRegionType.STATUTORY_CONTEXT:
                score += 1.5
            elif structural_label == StructuralRegionType.PARTY_SUBMISSIONS:
                # Down-weight party submissions so party arguments are not prioritized as authoritative holdings
                score -= 4.0
            elif structural_label == StructuralRegionType.FINAL_DISPOSITION:
                score += 1.0
            elif structural_label == StructuralRegionType.FACTS_PROCEDURAL:
                score += 0.5

            if is_quoted:
                # Quoted precedent down-weighted compared to court's own ruling
                score -= 2.0
        else:
            # Baseline keyword bonuses when structure awareness is disabled
            if any(marker in p_lower for marker in ["held:", "held :", "headnotes", "issue for consideration"]):
                score += 3.0
            if any(marker in p_lower for marker in ["analysis, reasoning", "conclusion", "we hold", "we find"]):
                score += 2.0
            if any(marker in p_lower for marker in ["section ", "article ", "act, 19", "act, 20"]):
                score += 1.5

        return score

    def assemble_evidence(
        self,
        query: str,
        retrieved_candidates: List[Dict[str, Any]]
    ) -> List[EvidencePassage]:
        """
        Given query and top retrieved judgments, extract and rank passage-level evidence.
        Uses structure-aware segmentation when enabled, preserving 100% exact offsets.
        """
        if not retrieved_candidates:
            return []

        query_tokens = set(re.findall(r'\b[a-z0-9]+\b', query.lower()))
        stopwords = {"what", "are", "the", "for", "in", "and", "or", "to", "of", "a", "an", "is", "by", "under", "can", "with"}
        query_tokens = query_tokens - stopwords

        all_candidate_passages: List[Dict[str, Any]] = []

        for c_rank, cand in enumerate(retrieved_candidates, 1):
            doc_id = cand["document_id"]
            doc = self._load_document(doc_id)
            if not doc or not doc.get("full_text"):
                continue

            full_text = doc["full_text"]

            if self.enable_structure_aware:
                spans_dict = JudgmentStructureParser.extract_structural_candidate_spans(
                    full_text,
                    target_passage_chars=self.target_passage_chars,
                    min_passage_chars=self.min_passage_chars
                )
            else:
                spans_dict = []

            if not spans_dict:
                raw_spans = self._extract_candidate_spans(full_text)
                spans_dict = [
                    {
                        "start_char": start,
                        "end_char": end,
                        "text": txt,
                        "structural_label": None,
                        "structural_confidence": 0.0,
                        "detection_method": "paragraph_split",
                        "is_quoted": False
                    }
                    for start, end, txt in raw_spans
                ]

            doc_passages = []
            for item in spans_dict:
                text = item["text"]
                s_label = item.get("structural_label")
                is_q = item.get("is_quoted", False)
                p_score = self._score_passage(
                    passage_text=text,
                    query_tokens=query_tokens,
                    structural_label=s_label,
                    is_quoted=is_q
                )
                doc_passages.append({
                    "document_id": doc_id,
                    "case_title": doc.get("case_title", doc_id),
                    "citation": doc.get("citation"),
                    "case_number": doc.get("case_number"),
                    "decision_date": doc.get("decision_date"),
                    "passage_text": text,
                    "start_char": item["start_char"],
                    "end_char": item["end_char"],
                    "judgment_rank": c_rank,
                    "judgment_score": cand.get("fused_score") or cand.get("score") or (1.0 / c_rank),
                    "passage_score": p_score,
                    "structural_label": s_label,
                    "structural_confidence": item.get("structural_confidence", 0.0),
                    "detection_method": item.get("detection_method")
                })

            # Sort this document's passages by score descending and keep top N
            doc_passages.sort(key=lambda p: p["passage_score"], reverse=True)
            selected_for_doc = doc_passages[:self.max_passages_per_doc]
            all_candidate_passages.extend(selected_for_doc)

        # Sort all passages across documents by combined (judgment_rank, passage_score)
        all_candidate_passages.sort(
            key=lambda p: (-p["judgment_rank"], p["passage_score"]),
            reverse=True
        )

        final_passages = all_candidate_passages[:self.total_max_passages]

        # Format into EvidencePassage models with stable IDs: E1, E2, ...
        evidence_list: List[EvidencePassage] = []
        for idx, p in enumerate(final_passages, 1):
            evidence_id = f"E{idx}"
            evidence_list.append(EvidencePassage(
                evidence_id=evidence_id,
                document_id=p["document_id"],
                case_title=p["case_title"],
                citation=p["citation"],
                case_number=p["case_number"],
                decision_date=p["decision_date"],
                passage_text=p["passage_text"],
                start_char=p["start_char"],
                end_char=p["end_char"],
                judgment_rank=p["judgment_rank"],
                judgment_score=p["judgment_score"],
                passage_score=p["passage_score"],
                structural_label=p.get("structural_label"),
                structural_confidence=p.get("structural_confidence", 0.0),
                detection_method=p.get("detection_method")
            ))

        return evidence_list


def verify_and_filter_evidence(
    evidence: List[EvidencePassage],
    corpus_dir: str = CORPUS_DIR
) -> Tuple[List[EvidencePassage], List[Dict[str, Any]]]:
    """
    Fail-closed evidence validator (Milestone 5B):
    Verifies that full_text[start_char:end_char] == passage_text for every passage.
    Returns (valid_passages, diagnostic_errors).
    Invalid passages are excluded; valid passages retain deterministic ranking and exact offsets.
    """
    valid_passages: List[EvidencePassage] = []
    diagnostics: List[Dict[str, Any]] = []

    for ep in evidence:
        # Check boundary validity
        if ep.start_char < 0 or ep.end_char <= ep.start_char or not ep.passage_text:
            diagnostics.append({
                "evidence_id": ep.evidence_id,
                "document_id": ep.document_id,
                "start_char": ep.start_char,
                "end_char": ep.end_char,
                "reason": "invalid_boundary_or_empty_text"
            })
            continue

        fpath = os.path.join(corpus_dir, f"{ep.document_id}.json")
        if not os.path.exists(fpath):
            diagnostics.append({
                "evidence_id": ep.evidence_id,
                "document_id": ep.document_id,
                "start_char": ep.start_char,
                "end_char": ep.end_char,
                "reason": "corpus_document_not_found"
            })
            continue

        try:
            with open(fpath, "r", encoding="utf-8") as f:
                doc = json.load(f)
            full_text = doc.get("full_text", "")
        except Exception as e:
            diagnostics.append({
                "evidence_id": ep.evidence_id,
                "document_id": ep.document_id,
                "start_char": ep.start_char,
                "end_char": ep.end_char,
                "reason": f"read_error: {str(e)}"
            })
            continue

        if ep.end_char > len(full_text):
            diagnostics.append({
                "evidence_id": ep.evidence_id,
                "document_id": ep.document_id,
                "start_char": ep.start_char,
                "end_char": ep.end_char,
                "full_text_len": len(full_text),
                "reason": "offset_exceeds_full_text_length"
            })
            continue

        slice_text = full_text[ep.start_char:ep.end_char]
        if slice_text != ep.passage_text:
            diagnostics.append({
                "evidence_id": ep.evidence_id,
                "document_id": ep.document_id,
                "start_char": ep.start_char,
                "end_char": ep.end_char,
                "expected_len": len(ep.passage_text),
                "actual_slice_len": len(slice_text),
                "reason": "exact_slice_text_mismatch"
            })
            continue

        # Passage is 100% verified against canonical text
        valid_passages.append(ep)

    # Renumber valid passages sequentially (E1, E2, ...) to ensure deterministic, continuous indexing
    renumbered_valid: List[EvidencePassage] = []
    for idx, vp in enumerate(valid_passages, 1):
        renumbered_valid.append(vp.model_copy(update={"evidence_id": f"E{idx}"}))

    return renumbered_valid, diagnostics


def verify_evidence_offsets(
    evidence: List[EvidencePassage],
    corpus_dir: str = CORPUS_DIR
) -> Tuple[bool, List[str]]:
    """
    Verify that every evidence passage matches its exact slice in the canonical full_text.
    Returns (True, []) if 100% verified, or (False, [error_messages]).
    """
    _, diagnostics = verify_and_filter_evidence(evidence, corpus_dir)
    errors = [
        f"Offset mismatch on {d['evidence_id']} ({d['document_id']}): {d['reason']}"
        for d in diagnostics
    ]
    return (len(errors) == 0, errors)


def compute_jaccard_similarity(text1: str, text2: str) -> float:
    """Compute token Jaccard similarity between two texts, ignoring common short words."""
    t1 = set(re.findall(r'\b[a-z0-9]{3,}\b', text1.lower()))
    t2 = set(re.findall(r'\b[a-z0-9]{3,}\b', text2.lower()))
    if not t1 or not t2:
        return 0.0
    return len(t1.intersection(t2)) / len(t1.union(t2))


class ExtractiveSentenceCompressor:
    """
    Extractive sentence compressor for legal passages (Milestone 8 Task 4).
    Preserves exact character offsets in canonical text, complete sentences,
    statutory references, and legal qualifications without paraphrasing.
    """
    RE_LEGAL_ABBREV = re.compile(
        r'\b(?:art|sec|no|ltd|pvt|ors|anr|vs|v|hon|para|dr|mr|mrs|s|u/s|ss|r|c)\.',
        re.IGNORECASE
    )

    @classmethod
    def split_sentences_with_offsets(cls, text: str, base_offset: int = 0) -> List[Dict[str, Any]]:
        """
        Split passage text into complete sentences while calculating exact offsets relative to judgment full_text.
        Ensures full_text[base_offset + rel_start : base_offset + rel_end] == sentence_text.
        """
        sentences: List[Dict[str, Any]] = []
        text_len = len(text)
        pattern = re.compile(r'([.!?])(?:\s+|\n+)')

        last_start = 0
        for match in pattern.finditer(text):
            terminator_end = match.end(1)
            candidate = text[last_start:terminator_end].strip()

            prefix = text[max(0, terminator_end - 6):terminator_end]
            if cls.RE_LEGAL_ABBREV.search(prefix):
                continue

            open_brackets = text[last_start:terminator_end].count('[') - text[last_start:terminator_end].count(']')
            if open_brackets > 0:
                continue

            if len(candidate) > 15:
                lead_spaces = len(text[last_start:terminator_end]) - len(text[last_start:terminator_end].lstrip())
                actual_start = last_start + lead_spaces
                actual_end = actual_start + len(candidate)
                sentences.append({
                    "text": candidate,
                    "rel_start": actual_start,
                    "rel_end": actual_end,
                    "abs_start": base_offset + actual_start,
                    "abs_end": base_offset + actual_end
                })
                last_start = match.end()

        if last_start < text_len:
            trailing = text[last_start:].strip()
            if len(trailing) > 15:
                lead_spaces = len(text[last_start:]) - len(text[last_start:].lstrip())
                actual_start = last_start + lead_spaces
                actual_end = actual_start + len(trailing)
                sentences.append({
                    "text": trailing,
                    "rel_start": actual_start,
                    "rel_end": actual_end,
                    "abs_start": base_offset + actual_start,
                    "abs_end": base_offset + actual_end
                })

        return sentences

    @classmethod
    def compress_passage(
        cls,
        passage: EvidencePassage,
        query: str,
        max_sentences: int = 4,
        max_chars: Optional[int] = None
    ) -> EvidencePassage:
        """
        Extract complete sentences relevant to the query while preserving exact character offsets.
        Never removes exceptions, qualifications, or negations within sentences.
        """
        sents = cls.split_sentences_with_offsets(passage.passage_text, base_offset=passage.start_char)
        if not sents or len(sents) <= 2:
            return passage

        q_tokens = set(re.findall(r'\b[a-z0-9]{3,}\b', query.lower()))
        stopwords = {
            "what", "are", "the", "for", "in", "and", "or", "to", "of", "a", "an",
            "is", "by", "under", "can", "with", "does", "did", "whether"
        }
        salient_q_tokens = q_tokens - stopwords

        scored_sents = []
        for s in sents:
            s_lower = s["text"].lower()
            s_tokens = set(re.findall(r'\b[a-z0-9]{3,}\b', s_lower))
            overlap = len(s_tokens.intersection(salient_q_tokens))
            score = float(overlap)
            if any(m in s_lower for m in ["held:", "held :", "we hold", "we find", "ratio", "functionality test", "test", "rule"]):
                score += 3.0
            if any(m in s_lower for m in ["section", "article", "clause", "sub-section", "act"]):
                score += 1.5
            scored_sents.append((score, s))

        # Select best contiguous sentence window to guarantee 100% exact character offset slicing:
        # full_text[new_start : new_end] == new_text
        n_sents = len(sents)
        sent_scores = [0.0] * n_sents
        for sc, s in scored_sents:
            idx = sents.index(s)
            sent_scores[idx] = sc

        best_score = -1.0
        best_i = 0
        best_j = 0

        for i in range(n_sents):
            window_score = 0.0
            for j in range(i, min(i + max_sentences, n_sents)):
                span_len = sents[j]["rel_end"] - sents[i]["rel_start"]
                if max_chars and span_len > max_chars and j > i:
                    break
                window_score += sent_scores[j]
                if window_score > best_score:
                    best_score = window_score
                    best_i = i
                    best_j = j

        start_rel = sents[best_i]["rel_start"]
        end_rel = sents[best_j]["rel_end"]
        new_text = passage.passage_text[start_rel:end_rel]
        new_start = passage.start_char + start_rel
        new_end = passage.start_char + end_rel

        return passage.model_copy(update={
            "passage_text": new_text,
            "start_char": new_start,
            "end_char": new_end
        })


STRUCTURAL_PRIORITY_ORDER = {
    StructuralRegionType.HEADNOTE_HOLDING: 5,
    StructuralRegionType.JUDICIAL_HOLDING: 5,
    StructuralRegionType.COURT_ANALYSIS: 4,
    StructuralRegionType.ISSUE_FRAMING: 3,
    StructuralRegionType.STATUTORY_CONTEXT: 2,
    StructuralRegionType.FACTS_PROCEDURAL: 1,
    StructuralRegionType.FINAL_DISPOSITION: 1,
    StructuralRegionType.GENERAL_TEXT: 0,
    None: 0,
    StructuralRegionType.PARTY_SUBMISSIONS: -5
}


def select_complementary_evidence_passages(
    passages: List[EvidencePassage],
    query: str,
    max_passages: int = 1,
    max_total_chars: Optional[int] = None,
    dedup_jaccard_threshold: float = 0.80,
    enable_compression: bool = False,
    enable_issue_holding_pairing: bool = True,
    max_chars_per_passage: Optional[int] = None
) -> List[EvidencePassage]:
    """
    Bounded, complementary evidence selection strategy (Milestone 8 & Milestone 9).
    - Preserves single-passage baseline when max_passages=1.
    - Limits passages to max_passages (1, 2, or 3).
    - Deduplicates identical or overlapping spans and near-identical texts.
    - Selects complementary passages providing novel query concepts or judicial ratio.
    - Pairs issue-framing passages with corresponding holdings from the same judgment.
    - Preserves exact source metadata and character offsets.
    - Renumbers selected passages sequentially as E1, E2, ...
    - Deterministic tie-breaking on equal scores.
    """
    if not passages or max_passages <= 0:
        return []

    # Fast-path for single-passage configuration: preserve baseline 100%
    if max_passages == 1:
        top_p = passages[0]
        if enable_compression:
            top_p = ExtractiveSentenceCompressor.compress_passage(
                top_p, query, max_chars=max_chars_per_passage
            )
        return [top_p.model_copy(update={"evidence_id": "E1"})]

    stopwords = {
        "what", "are", "the", "for", "in", "and", "or", "to", "of", "a", "an", "is",
        "by", "under", "can", "with", "does", "did", "whether", "this", "that"
    }
    q_tokens = set(re.findall(r'\b[a-z0-9]{3,}\b', query.lower())) - stopwords
    generic_legal_words = {
        "court", "courts", "judgment", "judgments", "appeal", "appeals",
        "appellant", "respondent", "section", "article", "case", "cases",
        "held", "order", "bench", "high", "supreme", "rule", "rules", "act"
    }
    salient_q_tokens = q_tokens - generic_legal_words

    def _candidate_sort_key(p: EvidencePassage):
        p_tokens = set(re.findall(r'\b[a-z0-9]{3,}\b', p.passage_text.lower()))
        novel = len(p_tokens.intersection(salient_q_tokens))
        struct_prio = STRUCTURAL_PRIORITY_ORDER.get(p.structural_label, 0)
        p_lower = p.passage_text.lower()
        has_auth = any(m in p_lower for m in ["held:", "held :", "we hold", "we find", "ratio decidendi", "functionality test"])
        effective_score = p.passage_score + (3.0 * novel) + (2.0 if has_auth else 0.0) + (1.5 * struct_prio)
        return (effective_score, -p.judgment_rank, struct_prio, p.passage_score, -p.start_char, p.document_id)

    sorted_candidates = sorted(passages, key=_candidate_sort_key, reverse=True)

    selected: List[EvidencePassage] = []
    total_chars = 0
    covered_salient: Set[str] = set()

    def _is_duplicate(cand: EvidencePassage, current_selected: List[EvidencePassage]) -> bool:
        for s in current_selected:
            if cand.document_id == s.document_id:
                has_span_overlap = not (cand.end_char <= s.start_char or cand.start_char >= s.end_char)
                if has_span_overlap:
                    return True
            jaccard = compute_jaccard_similarity(cand.passage_text, s.passage_text)
            if jaccard >= dedup_jaccard_threshold:
                return True
        return False

    def _add_passage(p: EvidencePassage) -> bool:
        nonlocal total_chars
        p_len = min(len(p.passage_text), max_chars_per_passage) if max_chars_per_passage else len(p.passage_text)
        if max_total_chars and (total_chars + p_len > max_total_chars) and len(selected) > 0:
            return False
        p_to_add = p
        if enable_compression:
            p_to_add = ExtractiveSentenceCompressor.compress_passage(
                p_to_add, query, max_chars=max_chars_per_passage
            )
        selected.append(p_to_add)
        total_chars += p_len
        c_tokens = set(re.findall(r'\b[a-z0-9]{3,}\b', p_to_add.passage_text.lower()))
        covered_salient.update(c_tokens.intersection(salient_q_tokens))
        return True

    # 1. Select primary top candidate
    for cand in sorted_candidates:
        if not _is_duplicate(cand, selected):
            _add_passage(cand)
            break

    # 2. Issue-Holding Pairing Heuristic (Milestone 9 Task 3)
    if enable_issue_holding_pairing and len(selected) > 0 and len(selected) < max_passages:
        primary = selected[0]
        paired_candidate: Optional[EvidencePassage] = None

        if primary.structural_label == StructuralRegionType.ISSUE_FRAMING:
            # Pair issue framing with corresponding holding in the same judgment
            for cand in sorted_candidates:
                if cand.document_id == primary.document_id and cand.structural_label in (
                    StructuralRegionType.HEADNOTE_HOLDING, StructuralRegionType.JUDICIAL_HOLDING
                ):
                    if not _is_duplicate(cand, selected):
                        paired_candidate = cand
                        break
        elif primary.structural_label in (StructuralRegionType.HEADNOTE_HOLDING, StructuralRegionType.JUDICIAL_HOLDING):
            # Pair holding with corresponding issue framing or statutory context in the same judgment
            for cand in sorted_candidates:
                if cand.document_id == primary.document_id and cand.structural_label in (
                    StructuralRegionType.ISSUE_FRAMING, StructuralRegionType.STATUTORY_CONTEXT
                ):
                    if not _is_duplicate(cand, selected):
                        paired_candidate = cand
                        break

        if paired_candidate is not None:
            _add_passage(paired_candidate)

    # 3. Fill remaining passage budget with highest scoring non-duplicate candidates
    for cand in sorted_candidates:
        if len(selected) >= max_passages:
            break
        if not _is_duplicate(cand, selected):
            _add_passage(cand)

    # Renumber selected passages sequentially: E1, E2, ...
    renumbered_passages: List[EvidencePassage] = []
    for idx, p in enumerate(selected, 1):
        renumbered_passages.append(p.model_copy(update={"evidence_id": f"E{idx}"}))

    return renumbered_passages

