"""Law Transition Matrix & Landmark Precedents API Router (/api/matrix).

Exposes all 26+ statutory transitions (IPC <-> BNS, CrPC <-> BNSS, IEA <-> BSA, Special Acts)
and 12 landmark Supreme Court precedents to power the interactive Matrix UI.
"""

import json
import logging
import os
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Query

from app.services.dataset_loader import LANDMARK_SUPREME_COURT_CASES

logger = logging.getLogger(__name__)

router = APIRouter()

KB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "knowledge_base.json")


def _get_category(old_law: str, new_law: str) -> tuple[str, str]:
    """Classify law transition into one of 4 major statutory categories."""
    if "BNSS" in new_law or "CrPC" in old_law or "Criminal Procedure" in old_law:
        return "bnss", "BNSS (Procedure & FIR)"
    elif "BSA" in new_law or "Evidence" in old_law:
        return "bsa", "BSA (Evidence & Records)"
    elif "BNS" in new_law or "IPC" in old_law or "Penal Code" in old_law:
        return "bns", "BNS (Penal)"
    else:
        return "special", "Special & Central Acts"


@router.get("/matrix")
async def get_law_transition_matrix(
    category: Optional[str] = Query(default=None, description="Filter by category: 'bns', 'bnss', 'bsa', 'special'"),
    search: Optional[str] = Query(default=None, description="Search term for crime/subject/section"),
    lang: Optional[str] = Query(default="en", description="Target language code: 'ta', 'hi', 'en'"),
):
    """Return all statutory transitions and landmark case precedents."""
    cat_filter = category.lower().strip() if isinstance(category, str) and category else None
    search_filter = search.lower().strip() if isinstance(search, str) and search else None
    lang_code = lang.lower().strip() if isinstance(lang, str) and lang else "en"
    transitions: List[Dict[str, Any]] = []

    # Check for localized matrix cache
    matrix_cache = None
    if lang_code != "en":
        cache_path = os.path.join(os.path.dirname(__file__), "..", "data", f"matrix_cache_{lang_code}.json")
        if os.path.exists(cache_path):
            try:
                with open(cache_path, "r", encoding="utf-8") as cf:
                    matrix_cache = json.load(cf)
            except Exception as e:
                logger.warning(f"Could not load matrix cache for {lang_code}: {e}")

    if os.path.exists(KB_PATH):
        try:
            with open(KB_PATH, "r", encoding="utf-8") as f:
                raw = json.load(f)
                laws = raw.get("laws", [])
                for i, law in enumerate(laws):
                    old_law = law.get("old_law", "")
                    new_law = law.get("new_law", "")
                    subject = law.get("subject", "")
                    key_changes = law.get("key_changes", "")
                    cat_key, cat_label = _get_category(old_law, new_law)

                    # Apply localized fields if cache exists
                    if matrix_cache:
                        if i < len(matrix_cache.get("subjects", [])):
                            subject = matrix_cache["subjects"][i]
                        if i < len(matrix_cache.get("key_changes", [])):
                            key_changes = matrix_cache["key_changes"][i]

                    sec_display = new_law.split(" - ")[-1] if " - " in new_law else new_law
                    old_display = old_law.split(" - ")[-1] if " - " in old_law else old_law
                    suggested_query = f"What is the difference between old {old_display} and new {sec_display} for {subject}?"

                    item = {
                        "id": f"trans-{i + 1}",
                        "subject": subject,
                        "old_law": old_law,
                        "new_law": new_law,
                        "category": cat_key,
                        "category_label": cat_label,
                        "description": law.get("description", ""),
                        "key_changes": key_changes,
                        "punishment_comparison": law.get("punishment_comparison", ""),
                        "procedural_classification": law.get("procedural_classification", ""),
                        "practical_citizen_advice": law.get("practical_citizen_advice", ""),
                        "full_statutory_text": law.get("full_statutory_text", ""),
                        "suggested_query": suggested_query,
                    }

                    # Filter by category
                    if cat_filter and cat_filter != "all" and cat_key != cat_filter:
                        continue

                    # Filter by search
                    if search_filter:
                        combined = f"{subject} {old_law} {new_law} {law.get('description', '')} {key_changes} {law.get('punishment_comparison', '')}".lower()
                        if search_filter not in combined:
                            continue

                    transitions.append(item)
        except Exception as e:
            logger.error(f"Failed to load knowledge_base.json for matrix: {e}")

    # Prepare Precedents
    precedents: List[Dict[str, Any]] = []
    for idx, case in enumerate(LANDMARK_SUPREME_COURT_CASES):
        headnote = case.get("headnote", "")
        ratio = case.get("ratio_decidendi", "")
        if matrix_cache:
            if idx < len(matrix_cache.get("prec_issues", [])):
                headnote = matrix_cache["prec_issues"][idx]
            if idx < len(matrix_cache.get("prec_ratios", [])):
                ratio = matrix_cache["prec_ratios"][idx]

        p_item = {
            "title": case.get("title", ""),
            "citation": case.get("citation", ""),
            "neutral_citation": case.get("neutral_citation", ""),
            "court": case.get("court", "Supreme Court of India"),
            "year": case.get("year", 0),
            "bench": case.get("bench", ""),
            "headnote": headnote,
            "ratio_decidendi": ratio,
            "applied_sections": case.get("applied_sections", []),
            "significance": case.get("significance", ""),
            "practical_impact": case.get("practical_impact", ""),
            "suggested_query": f"How does the landmark precedent {case.get('title')} apply to Indian criminal procedure and rights?",
        }

        if search_filter:
            combined = f"{p_item['title']} {p_item['citation']} {headnote} {ratio} {p_item['significance']} {p_item['practical_impact']} {' '.join(p_item['applied_sections'])}".lower()
            if search_filter not in combined:
                continue

        precedents.append(p_item)

    return {
        "status": "success",
        "total_transitions": len(transitions),
        "total_precedents": len(precedents),
        "transitions": transitions,
        "precedents": precedents,
    }
