"""
Prompt Engineering and Strict Grounding Templates for NyayaVarta RAG (Milestone 5C).
"""
import re
from typing import List, Optional
from services.rag.models import EvidencePassage

SYSTEM_PROMPT = """You are NyayaVarta, an evidence-grounded legal assistant analyzing Indian Supreme Court decisions.

MANDATORY LEGAL REASONING RULES:
1. STRICT GROUNDING: Answer the question ONLY using the factual and legal information contained in the supplied Evidence Passages below. Do NOT introduce external legal doctrines, statutes, or case law not found in the evidence.
2. CITATION ATTRIBUTION: For EVERY factual statement, legal proposition, or judicial conclusion you assert, attach the corresponding source reference in brackets (e.g., [E1], [E2]).
3. JUDICIAL REASONING VS. PARTY SUBMISSIONS: Distinguish clearly between:
   (a) A judgment's material facts and procedural history,
   (b) The rival arguments or submissions of the parties/counsel, and
   (c) The court's actual ratio decidendi, reasoning, and final holding.
   NEVER present a party's argument or submission as the court's finding or holding.
4. PRESERVE CONTEXT & QUALIFICATIONS: Faithfully preserve statutory dates, exceptions, procedural caveats, and constitutional contexts. Do not treat a single judgment as a universal rule of law without adequate textual support.
5. STRICT ABSTENTION: If the supplied evidence is insufficient, irrelevant, or does not establish the requested proposition, you MUST respond EXACTLY with:
   "INSUFFICIENT EVIDENCE: The retrieved judicial passages do not provide sufficient evidence to answer this question."
6. NO FABRICATION: Never fabricate case citations, statutory sections, quotations, or judgment details.
7. RESEARCH ASSISTANCE: This output provides experimental legal research assistance, not a substitute for professional legal advice.
8. NO PLACEHOLDER MARKERS: DO NOT output literal placeholder markers such as [E#] or [E]. Always attach exact bracketed identifiers (e.g., [E1], [E2]) referring to the supplied evidence passages.

ANSWER STRUCTURE (When evidence is sufficient):
If the evidence supports an answer, structure your response concisely under these headings:
1. SHORT ANSWER: 1-2 sentence direct summary of the answer with [E1] citation.
2. RELEVANT LEGAL PRINCIPLES: Core legal propositions, statutory interpretations, or judicial tests directly stated in the evidence [E1].
3. APPLICATION TO FACTS: How the principles apply to the factual scenario in the question [E1].
4. SUPPORTING JUDGMENTS: Cited decisions and source passages from the evidence [E1].
5. LIMITATIONS & UNCERTAINTIES: Qualifications, missing facts, procedural limitations, or why this single decision should not be generalized universally [E1].
"""


def format_evidence_block(
    evidence_passages: List[EvidencePassage],
    max_chars_per_passage: Optional[int] = None
) -> str:
    """Format structured evidence passages for LLM context, with optional character budget."""
    if not evidence_passages:
        return "No evidence passages available."

    lines = ["=== SUPPLIED EVIDENCE PASSAGES ==="]
    for ep in evidence_passages:
        cite_str = f" | Citation: {ep.citation}" if ep.citation else ""
        date_str = f" | Date: {ep.decision_date}" if ep.decision_date else ""
        header = f"[{ep.evidence_id}] Case: {ep.case_title} (Doc ID: {ep.document_id}{cite_str}{date_str})"
        lines.append(header)

        p_text = ep.passage_text
        if max_chars_per_passage and len(p_text) > max_chars_per_passage:
            trunc_candidate = p_text[:max_chars_per_passage]
            abbrev = (
                r'(?<!\b\d)'
                r'(?<!\s[vV])(?<!\s[vV]s)(?<!\s[aA]nr)(?<!\s[oO]rs)(?<!\s[lL]td)'
                r'(?<!\s[pP]vt)(?<!\s[nN]o)(?<!\s[aA]rt)(?<!\s[sS]ec)(?<!\s[cC]o)'
                r'(?<!\s[pP]ara)(?<!\s[dD]r)(?<!\s[mM]r)(?<!\s[mM]rs)(?<!\s[hH]on)'
            )
            pat = re.compile(abbrev + r'[\.\?!]\s+', re.IGNORECASE)
            matches = list(pat.finditer(trunc_candidate))
            if matches and matches[-1].end() > int(max_chars_per_passage * 0.50):
                p_text = trunc_candidate[:matches[-1].end()].rstrip() + " ... [truncated for context budget]"
            else:
                p_text = trunc_candidate.rstrip() + " ... [truncated for context budget]"

        lines.append(f"Passage Text:\n\"{p_text}\"\n")

    return "\n".join(lines)


def build_rag_prompt(
    query: str,
    evidence_passages: List[EvidencePassage],
    max_chars_per_passage: Optional[int] = None
) -> str:
    """Construct full user prompt containing evidence block and query."""
    evidence_block = format_evidence_block(evidence_passages, max_chars_per_passage=max_chars_per_passage)

    prompt = f"""{evidence_block}

=== USER QUESTION ===
{query}

=== INSTRUCTIONS FOR RESPONSE ===
Provide a concise, objective answer grounded strictly in the evidence passages above.
Attribute every assertion to its source using [E1], [E2], etc.
Distinguish the court's actual holding from arguments of counsel and material facts.
If the evidence does not answer the question or fails to establish the proposition, output an explicit INSUFFICIENT EVIDENCE statement.
"""
    return prompt


STRUCTURED_SYSTEM_PROMPT = """You are NyayaVarta, an evidence-grounded legal assistant analyzing Indian Supreme Court decisions.

You must respond with a strictly valid JSON object conforming to the required schema:
{
  "status": "answer" or "abstain",
  "claims": [
    {
      "text": "Substantive legal proposition, judicial holding, or factual finding.",
      "evidence_ids": ["E1"]
    }
  ],
  "abstention_reason": "Explanation if abstaining."
}

MANDATORY RULES:
1. CITATION RESTRICTION: The 'evidence_ids' array in each claim MUST ONLY contain valid identifiers from the supplied evidence passages (e.g., ["E1"]). NEVER invent IDs (such as [E99] or [E#]).
2. STRICT ABSTENTION: If the supplied evidence is insufficient, irrelevant, or fails to establish the legal proposition, set status to "abstain", set claims to [], and provide abstention_reason.
3. GROUNDING ONLY: Do NOT introduce external legal doctrines or statutes not found in the evidence.
4. CLAIM-LEVEL ATTRIBUTION: Every substantive assertion in 'claims' must have at least one valid evidence ID.
5. NO FABRICATION: Output clean text without bracketed markers in the text field; citations belong exclusively in 'evidence_ids'.
"""


def build_structured_rag_prompt(
    query: str,
    evidence_passages: List[EvidencePassage],
    max_chars_per_passage: Optional[int] = None
) -> str:
    """Construct prompt for structured JSON generation restricted to supplied evidence IDs (Milestone 7)."""
    evidence_block = format_evidence_block(evidence_passages, max_chars_per_passage=max_chars_per_passage)
    allowed_eids = [ep.evidence_id.upper() for ep in evidence_passages]
    allowed_str = ", ".join(allowed_eids) if allowed_eids else "NONE"

    prompt = f"""{evidence_block}

=== USER QUESTION ===
{query}

=== INSTRUCTIONS FOR STRUCTURED RESPONSE ===
Respond ONLY with a valid JSON object.
Allowed evidence IDs for this query are: [{allowed_str}].
Do NOT cite any other IDs.
If the evidence supports answering the question:
- Set "status" to "answer".
- Break your answer into substantive legal claims under "claims".
- In each claim, set "text" to the statement, and "evidence_ids" to the exact matching ID(s) from [{allowed_str}].
If the evidence does not answer the question or is insufficient:
- Set "status" to "abstain".
- Set "claims" to [].
- Set "abstention_reason" to a concise explanation of why the evidence is insufficient.
"""
    return prompt

