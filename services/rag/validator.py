"""
Citation and Claim Attribution Validator for NyayaVarta RAG (Milestone 5A).

Validates generated citation identifiers against supplied evidence, detects
hallucinated citation IDs, maps claim-to-source attribution, and flags unsupported statements.
"""
import re
import json
from typing import List, Tuple, Set, Dict, Any, Optional
from services.rag.models import (
    EvidencePassage,
    ClaimAttribution,
    CitationValidationResult,
    StructuredAnswer,
    StructuredClaim
)
from services.rag.claim_verifier import ClaimVerifier, ClaimVerificationStatus


class CitationValidator:
    # Matches well-formed citation tags like [E1], [E2], etc.
    RE_CITATION_TAG = re.compile(r'\[(E\d+)\]', re.IGNORECASE)
    # Matches malformed citation markers like [E#], [E], [], [Eabc], [E 1], [Evidence 1], etc.
    RE_MALFORMED_TAG = re.compile(
        r'\[\s*\]|\[E\s+[^\]]*\]|\[E([^0-9\]\s]+|(?=\]))\]|\[evidence\b[^\]]*\]|\[source\b[^\]]*\]|\[ref\b[^\]]*\]',
        re.IGNORECASE
    )

    def __init__(self, require_citations_on_all_claims: bool = True, verifier: Optional[ClaimVerifier] = None):
        self.require_citations_on_all_claims = require_citations_on_all_claims
        self.verifier = verifier or ClaimVerifier()

    @classmethod
    def is_clean_abstention(cls, text: str) -> bool:
        """
        Determine if an answer is a genuinely clean explicit abstention, as opposed to
        substantive legal prose that happens to begin with 'INSUFFICIENT EVIDENCE'.

        A genuinely clean abstention MUST:
        1. Start with an explicit abstention declaration (e.g. 'INSUFFICIENT EVIDENCE' or
           'No relevant judgments found in the corpus for this query.').
        2. Be concise: at most 2 lines and at most 300 characters.
        3. Not contain citations ([E#]).
        4. Not introduce substantive legal claims, holdings, or factual assertions;
           any accompanying text must strictly describe evidentiary deficiency or absence.
        """
        if not text or not isinstance(text, str):
            return False

        trimmed = text.strip()
        lower = trimmed.lower()

        # 1. Check for abstention prefix / phrase
        prefix_match = re.match(r'^insufficient\s+evidence(?:\s*:\s*|\s+-\s*|\s+)?', lower)
        is_no_relevant = (lower == "no relevant judgments found in the corpus for this query.")
        if not prefix_match and not is_no_relevant:
            return False

        # 2. Check structure and brevity (multi-paragraph text is never a clean abstention)
        lines = [l.strip() for l in trimmed.splitlines() if l.strip()]
        if len(lines) > 2 or len(trimmed) > 300:
            return False

        # 3. Must not contain citation markers
        if re.search(r'\[(?:E\d+|E#|E|evidence|source|ref)[^\]]*\]', trimmed, re.IGNORECASE):
            return False

        # 4. Check remainder text for evidence deficiency indicators
        # If pure abstention declaration with no remainder, it is clean
        if lower in ["insufficient evidence", "insufficient evidence.", "insufficient evidence:"]:
            return True

        if is_no_relevant:
            return True

        if prefix_match:
            remainder = lower[prefix_match.end():].strip()
        else:
            remainder = lower

        if not remainder:
            return True

        # Deficiency keywords that characterize genuine abstention rationales
        deficiency_indicators = [
            "not provide", "not contain", "no relevant", "do not", "does not",
            "fails to", "cannot be determined", "not present", "disjoint",
            "inadequate", "unsupported", "lacks", "none are present", "none present",
            "unable to", "not found", "insufficient", "no evidence", "missing",
            "do not support", "does not support", "cannot answer", "not established",
            "not enough", "absence of"
        ]

        has_deficiency = any(indicator in remainder for indicator in deficiency_indicators)
        if not has_deficiency:
            return False

        # 5. Substantive legal holding or factual assertion patterns that must NEVER appear in a clean abstention
        substantive_patterns = [
            # Adjudicative rulings & holdings
            r'\b(?:held|ruled|decided|concluded|ordered|granted|dismissed|allowed|permitted|acquitted|convicted)\b',
            # Litigation parties & proceedings
            r'\b(?:appellant|petitioner|respondent|accused|prosecution|plaintiff|defendant|writ petition|civil appeal|criminal appeal|full bench|division bench)\b',
            # Substantive legal rules & affirmative powers
            r'\b(?:rules?\s+(?:can|cannot|may|must|shall)\s+be|power\s+under\s+article|governor\s+has|officer\s+can|employer\s+may|criteria\s+may|authority\s+may)\b',
            # Case facts & specific statutory actions
            r'\b(?:scored\s+\d+|vacancies\s+were|rules\s+were\s+framed|notified\s+in\s+\d+|filed\s+(?:a\s+)?(?:writ|appeal|petition)|preliminary\s+examination)\b',
            r'\b(?:unilaterally\s+extend|extend\s+the\s+\d+-day|borrower\s+consent)\b'
        ]
        for pat in substantive_patterns:
            if re.search(pat, remainder):
                return False

        # 6. Contrastive pivots that transition from deficiency to affirmative assertions
        # Genuine abstentions only contrast into absence (e.g. "...inquires about Section 36A, but none are present...")
        contrastive_match = re.search(r'\b(?:but|however|although|though|while|yet|nevertheless)\s+(.*)', remainder)
        if contrastive_match:
            after_pivot = contrastive_match.group(1).strip()
            # The clause following a contrastive pivot MUST explicitly declare deficiency/absence
            if not any(ind in after_pivot for ind in ["none are present", "none present", "no relevant", "not present", "not found", "no evidence", "not provide", "not contain", "neither"]):
                return False

        # 7. Multi-clause and sentence validation across punctuation (periods, semicolons, em-dashes, colons, and clause conjunctions)
        clauses = [s.strip() for s in re.split(r'(?:(?<=[\.\?!])\s+|;\s*|:\s*|\s+[—–-]\s+|,\s+(?:and|or|while|whereas|although|though|because)\s+)', remainder) if s.strip()]
        if len(clauses) > 1:
            for c in clauses[1:]:
                # Subsequent clauses must describe evidence deficiency, absence, or scoping
                clause_has_deficiency = any(ind in c for ind in deficiency_indicators)
                is_scoping = any(sc in c for sc in ["to answer this question", "in retrieved evidence", "in the corpus", "on this issue"])
                if not (clause_has_deficiency or is_scoping):
                    return False

        return True

    def validate(
        self,
        answer: str,
        supplied_evidence: List[EvidencePassage]
    ) -> Tuple[CitationValidationResult, List[ClaimAttribution]]:
        """
        Validate generated answer text against supplied evidence passages (Milestone 5B, 6.1 & 7).
        Supports both free-form text with [E#] citations and structured JSON responses.
        Decouples citation syntax, existence, attribution completeness, evidence integrity,
        and semantic support.
        """
        ans_trimmed = answer.strip()

        # Check if answer is a structured JSON payload
        if ans_trimmed.startswith("{"):
            try:
                data = json.loads(ans_trimmed)
                if isinstance(data, dict) and ("status" in data or "claims" in data):
                    try:
                        structured = StructuredAnswer.model_validate(data)
                        return self.validate_structured(structured, supplied_evidence)
                    except Exception as p_err:
                        # Malformed or missing fields in structured answer schema
                        return CitationValidationResult(
                            is_valid=False,
                            validation_status="invalid",
                            citation_syntax_valid=False,
                            citation_existence_valid=False,
                            attribution_complete=False,
                            evidence_integrity_valid=True,
                            semantic_support_status="not_evaluated",
                            cited_source_ids=[],
                            valid_source_ids=[],
                            invalid_source_ids=[],
                            unsupported_sentences=[],
                            has_invalid_citations=True,
                            validation_notes=[f"Structured output schema validation failed: {p_err}"]
                        ), []
            except json.JSONDecodeError as j_err:
                # Started with { but failed json decoding
                return CitationValidationResult(
                    is_valid=False,
                    validation_status="invalid",
                    citation_syntax_valid=False,
                    citation_existence_valid=False,
                    attribution_complete=False,
                    evidence_integrity_valid=True,
                    semantic_support_status="not_evaluated",
                    cited_source_ids=[],
                    valid_source_ids=[],
                    invalid_source_ids=[],
                    unsupported_sentences=[],
                    has_invalid_citations=True,
                    validation_notes=[f"Malformed JSON in structured output: {j_err}"]
                ), []

        supplied_ids: Set[str] = {ep.evidence_id.upper() for ep in supplied_evidence}
        validation_notes: List[str] = []

        # 1. Check for explicit clean abstention / insufficient evidence
        # Must be a genuinely clean abstention rather than substantive prose with an abstention prefix
        ans_clean_abstention = self.is_clean_abstention(ans_trimmed)

        # 2. Extract citation tags & malformed markers
        raw_matches = self.RE_CITATION_TAG.findall(answer)
        cited_ids = [m.upper() for m in raw_matches]
        malformed_matches = self.RE_MALFORMED_TAG.findall(answer)

        # Deduplicate while preserving order of appearance
        seen = set()
        unique_cited = []
        for cid in cited_ids:
            if cid.upper() not in seen:
                seen.add(cid.upper())
                unique_cited.append(cid.upper())

        # If answer is a genuinely clean explicit abstention and has NO citations, handle cleanly
        if ans_clean_abstention and len(unique_cited) == 0:
            validation_notes.append("System explicitly declared clean abstention due to insufficient evidence.")
            result = CitationValidationResult(
                is_valid=True,
                validation_status="valid",
                citation_syntax_valid=True,
                citation_existence_valid=True,
                attribution_complete=True,
                evidence_integrity_valid=True,
                semantic_support_status="not_evaluated",
                cited_source_ids=[],
                valid_source_ids=[],
                invalid_source_ids=[],
                unsupported_sentences=[],
                has_invalid_citations=False,
                validation_notes=validation_notes
            )
            return result, []

        # 3. Syntax validation
        citation_syntax_valid = len(malformed_matches) == 0
        if not citation_syntax_valid:
            validation_notes.append(f"Detected {len(malformed_matches)} malformed citation marker(s).")

        # 4. Existence validation
        valid_ids = [cid for cid in unique_cited if cid in supplied_ids]
        invalid_ids = [cid for cid in unique_cited if cid not in supplied_ids]
        has_invalid = len(invalid_ids) > 0 or (not citation_syntax_valid)
        citation_existence_valid = (len(invalid_ids) == 0) and (len(valid_ids) > 0)

        if invalid_ids:
            validation_notes.append(f"Detected {len(invalid_ids)} unknown/hallucinated citation ID(s): {invalid_ids}")

        # 5. Sentence-level claim attribution & completeness
        # Split along substantive sentence boundaries while protecting:
        # - Numbered lists (1., 2., 10.) via (?<!\b\d)
        # - Legal abbreviations (v., vs., anr., ors., ltd., pvt., no., art., sec., u/s., para., dr., mr., mrs., hon.)
        # - Trailing citations attached to terminal punctuation (. [E1], . [E1][E2])
        abbrev_lookbehind = (
            r'(?<!\b\d)'
            r'(?<!\s[vV])(?<!\s[vV]s)(?<!\s[aA]nr)(?<!\s[oO]rs)(?<!\s[lL]td)'
            r'(?<!\s[pP]vt)(?<!\s[nN]o)(?<!\s[aA]rt)(?<!\s[sS]ec)(?<!\s[uU]/[sS])'
            r'(?<!\s[pP]ara)(?<!\s[dD]r)(?<!\s[mM]r)(?<!\s[mM]rs)(?<!\s[hH]on)'
        )
        split_pattern = (
            abbrev_lookbehind + r'(?:[\.\?!])\s+(?!\[(?:E\d+|E#|E|evidence|source|ref)[^\]]*\])|'
            r'(?<=\])\s+(?=[A-Z0-9#\n])|'
            r'\n\s*\n'
        )
        sentences = [s.strip() for s in re.split(split_pattern, answer) if len(s.strip()) > 5]
        claims: List[ClaimAttribution] = []
        unsupported_sentences: List[str] = []

        for s in sentences:
            s_cites = [m.upper() for m in self.RE_CITATION_TAG.findall(s)]
            # Structural headings, markdown formatting, bench metadata, or disclaimers
            s_clean = re.sub(r'^[#*\s\-\d\.]+', '', s).strip().lower()
            is_heading = any(
                s_clean.startswith(h) for h in [
                    "short answer", "relevant legal principles", "application to facts",
                    "supporting judgments", "limitations & uncertainties", "limitations and uncertainties"
                ]
            )
            is_bench_header = bool(re.search(r'\b(?:jj|j|cji)\.\]?$', s.strip(), re.IGNORECASE))
            is_structural = any(
                s_clean.startswith(h) for h in [
                    "issue for consideration", "headnote", "held:", "coram:", "judgment:",
                    "order:", "civil appeal", "criminal appeal", "writ petition"
                ]
            )
            is_clean_abs_sentence = s.lower().startswith("insufficient evidence") and self.is_clean_abstention(s)
            is_meta = is_heading or is_bench_header or is_structural or is_clean_abs_sentence or any(
                s.lower().startswith(m) for m in [
                    "as stated above", "in conclusion",
                    "to summarize", "note:", "disclaimer:", "###", "##", "#"
                ]
            )

            sentence_has_valid = bool(s_cites and all(c in supplied_ids for c in s_cites))
            sentence_syntax_ok = not bool(self.RE_MALFORMED_TAG.search(s))

            if not s_cites and not is_meta:
                unsupported_sentences.append(s)

            # Determine structural nature of cited evidence passages
            cited_eps = [ep for ep in supplied_evidence if ep.evidence_id.upper() in s_cites]
            s_natures = [ep.structural_label for ep in cited_eps if ep.structural_label]
            relies_only_submissions = bool(s_natures and all(sn == "party_submissions" for sn in s_natures))
            if relies_only_submissions:
                validation_notes.append(f"Warning: Sentence '{s[:40]}...' relies entirely on party submissions rather than judicial findings.")

            claims.append(ClaimAttribution(
                sentence=s,
                cited_evidence_ids=s_cites,
                citation_syntax_valid=sentence_syntax_ok,
                citation_existence_valid=sentence_has_valid or (len(s_cites) == 0 and is_meta),
                is_attributed=sentence_has_valid or is_meta,
                semantic_support_status="not_evaluated",
                is_grounded=sentence_has_valid,
                structural_natures=s_natures,
                relies_only_on_party_submissions=relies_only_submissions
            ))

        attribution_complete = (len(unsupported_sentences) == 0)
        if unsupported_sentences:
            validation_notes.append(
                f"Identified {len(unsupported_sentences)} substantive sentence(s) lacking evidence citations."
            )

        if not unique_cited:
            citation_existence_valid = False
            validation_notes.append("No source citations found in the generated response.")

        # 6. Verify substantive claims with ClaimVerifier
        contradicted_count = 0
        unsupported_count = 0
        partially_supported_count = 0
        supported_count = 0
        unverified_count = 0
        verification_notes = []

        if claims and supplied_evidence:
            self.verifier.verify_claims(claims=claims, supplied_evidence=supplied_evidence)
            contradicted_count = sum(1 for c in claims if c.verification_status == ClaimVerificationStatus.CONTRADICTED.value)
            unsupported_count = sum(1 for c in claims if c.verification_status == ClaimVerificationStatus.UNSUPPORTED.value)
            partially_supported_count = sum(1 for c in claims if c.verification_status == ClaimVerificationStatus.PARTIALLY_SUPPORTED.value)
            supported_count = sum(1 for c in claims if c.verification_status == ClaimVerificationStatus.SUPPORTED.value)
            unverified_count = sum(1 for c in claims if c.verification_status == ClaimVerificationStatus.NOT_EVALUATED.value)

        # 7. Syntactic and existence validity
        validation_notes.append(
            "Semantic legal support status: not_evaluated (citation reference existence verified; "
            "semantic correctness requires independent verification)."
        )
        is_valid = (
            (len(valid_ids) > 0) and
            (not has_invalid) and
            citation_syntax_valid and
            citation_existence_valid and
            (attribution_complete if self.require_citations_on_all_claims else True)
        )

        cand_result = CitationValidationResult(
            is_valid=is_valid,
            validation_status="valid" if is_valid else "invalid",
            citation_syntax_valid=citation_syntax_valid,
            citation_existence_valid=citation_existence_valid,
            attribution_complete=attribution_complete,
            evidence_integrity_valid=True,
            semantic_support_status="not_evaluated",
            cited_source_ids=unique_cited,
            valid_source_ids=valid_ids,
            invalid_source_ids=invalid_ids,
            unsupported_sentences=unsupported_sentences,
            has_invalid_citations=has_invalid,
            validation_notes=validation_notes
        )

        # 8. Evaluate conservative acceptance policy
        policy = ClaimVerifier.evaluate_acceptance_policy(
            validation_result=cand_result,
            claims=claims,
            is_abstention=False
        )

        is_valid = policy["is_valid"]
        if contradicted_count > 0:
            validation_status = "contradicted"
            semantic_status = "contradicted"
        elif not is_valid:
            validation_status = "invalid"
            semantic_status = "unsupported" if (unsupported_count > 0 and supported_count == 0 and unverified_count == 0) else "not_evaluated"
        elif policy["accepted_status"] == "answered_with_qualification":
            validation_status = "partially_supported"
            semantic_status = "partially_supported"
        elif (
            supported_count > 0
            and supported_count == len(claims)
            and unverified_count == 0
            and partially_supported_count == 0
            and unsupported_count == 0
            and contradicted_count == 0
        ):
            validation_status = "valid"
            semantic_status = "supported"
        else:
            validation_status = "valid"
            semantic_status = "not_evaluated"

        verification_notes.append(policy["rationale"])
        for i, c in enumerate(claims, 1):
            if c.verification_method:
                verification_notes.append(f"Claim {i}: {c.verification_status} via {c.verification_method} - {c.verification_reason}")

        result = CitationValidationResult(
            is_valid=is_valid,
            validation_status=validation_status,
            citation_syntax_valid=citation_syntax_valid,
            citation_existence_valid=citation_existence_valid,
            attribution_complete=attribution_complete,
            evidence_integrity_valid=True,
            semantic_support_status=semantic_status,
            contradicted_claims_count=contradicted_count,
            unsupported_claims_count=unsupported_count,
            partially_supported_claims_count=partially_supported_count,
            supported_claims_count=supported_count,
            unverified_claims_count=unverified_count,
            cited_source_ids=unique_cited,
            valid_source_ids=valid_ids,
            invalid_source_ids=invalid_ids,
            unsupported_sentences=unsupported_sentences,
            has_invalid_citations=has_invalid,
            validation_notes=validation_notes,
            verification_notes=verification_notes,
            shadow_nli_disagreements_count=sum(1 for c in claims if getattr(c, "shadow_nli_disagreement", False))
        )

        return result, claims

    def validate_structured(
        self,
        structured_answer: StructuredAnswer,
        supplied_evidence: List[EvidencePassage]
    ) -> Tuple[CitationValidationResult, List[ClaimAttribution]]:
        """
        Validate a StructuredAnswer instance against active supplied evidence passages (Milestone 7).
        Enforces:
        - Exact active evidence ID matching (rejects unknown, unexpected, or stale IDs).
        - Substantive claims with empty evidence_ids are flagged and rejected.
        - Correct abstention handling (empty claims list required).
        - Strict syntax check on all evidence IDs.
        """
        supplied_ids: Set[str] = {ep.evidence_id.upper() for ep in supplied_evidence}
        validation_notes: List[str] = []

        # 1. Handle abstention
        if structured_answer.status == "abstain":
            if len(structured_answer.claims) > 0:
                validation_notes.append("Structured abstention contains unexpected substantive claims.")
                result = CitationValidationResult(
                    is_valid=False,
                    validation_status="invalid",
                    citation_syntax_valid=True,
                    citation_existence_valid=False,
                    attribution_complete=False,
                    evidence_integrity_valid=True,
                    semantic_support_status="insufficient_grounding",
                    cited_source_ids=[],
                    valid_source_ids=[],
                    invalid_source_ids=[],
                    unsupported_sentences=[c.text for c in structured_answer.claims],
                    has_invalid_citations=True,
                    validation_notes=validation_notes
                )
                return result, []

            validation_notes.append(
                f"Structured abstention accepted. Reason: {structured_answer.abstention_reason or 'No reason provided.'}"
            )
            result = CitationValidationResult(
                is_valid=True,
                validation_status="valid",
                citation_syntax_valid=True,
                citation_existence_valid=True,
                attribution_complete=True,
                evidence_integrity_valid=True,
                semantic_support_status="not_evaluated",
                cited_source_ids=[],
                valid_source_ids=[],
                invalid_source_ids=[],
                unsupported_sentences=[],
                has_invalid_citations=False,
                validation_notes=validation_notes
            )
            return result, []

        # 2. Handle 'answer' status
        if structured_answer.status != "answer":
            validation_notes.append(
                f"Invalid structured answer status: '{structured_answer.status}'. Expected 'answer' or 'abstain'."
            )
            result = CitationValidationResult(
                is_valid=False,
                validation_status="invalid",
                citation_syntax_valid=False,
                citation_existence_valid=False,
                attribution_complete=False,
                evidence_integrity_valid=True,
                semantic_support_status="not_evaluated",
                cited_source_ids=[],
                valid_source_ids=[],
                invalid_source_ids=[],
                unsupported_sentences=[],
                has_invalid_citations=True,
                validation_notes=validation_notes
            )
            return result, []

        if len(structured_answer.claims) == 0:
            validation_notes.append("Status is 'answer' but claims list is empty.")
            result = CitationValidationResult(
                is_valid=False,
                validation_status="invalid",
                citation_syntax_valid=True,
                citation_existence_valid=False,
                attribution_complete=False,
                evidence_integrity_valid=True,
                semantic_support_status="not_evaluated",
                cited_source_ids=[],
                valid_source_ids=[],
                invalid_source_ids=[],
                unsupported_sentences=[],
                has_invalid_citations=False,
                validation_notes=validation_notes
            )
            return result, []

        # 3. Process each substantive claim
        all_cited_ids: List[str] = []
        valid_ids: List[str] = []
        invalid_ids: List[str] = []
        unsupported_sentences: List[str] = []
        claims_attributions: List[ClaimAttribution] = []
        citation_syntax_valid = True

        re_valid_eid = re.compile(r'^E\d+$', re.IGNORECASE)

        for claim in structured_answer.claims:
            c_text = claim.text.strip()
            eids = [e.strip().upper() for e in claim.evidence_ids if e and isinstance(e, str)]

            # Check if substantive claim has no evidence citations
            if len(eids) == 0:
                unsupported_sentences.append(c_text)
                claims_attributions.append(ClaimAttribution(
                    sentence=c_text,
                    cited_evidence_ids=[],
                    citation_syntax_valid=True,
                    citation_existence_valid=False,
                    is_attributed=False,
                    semantic_support_status="unsupported",
                    is_grounded=False
                ))
                continue

            claim_c_syntax = True
            claim_c_existence = True
            for eid in eids:
                if eid not in all_cited_ids:
                    all_cited_ids.append(eid)

                # Syntax check
                if not re_valid_eid.match(eid):
                    citation_syntax_valid = False
                    claim_c_syntax = False
                    if eid not in invalid_ids:
                        invalid_ids.append(eid)
                    validation_notes.append(f"Malformed evidence ID format: '{eid}' in claim '{c_text[:40]}...'.")
                elif eid not in supplied_ids:
                    claim_c_existence = False
                    if eid not in invalid_ids:
                        invalid_ids.append(eid)
                else:
                    if eid not in valid_ids:
                        valid_ids.append(eid)

            # Determine structural nature of cited evidence passages
            cited_eps = [ep for ep in supplied_evidence if ep.evidence_id.upper() in eids]
            s_natures = [ep.structural_label for ep in cited_eps if ep.structural_label]
            relies_only_submissions = bool(s_natures and all(sn == "party_submissions" for sn in s_natures))
            if relies_only_submissions:
                validation_notes.append(f"Warning: Claim '{c_text[:40]}...' relies entirely on party submissions rather than judicial findings.")

            claims_attributions.append(ClaimAttribution(
                sentence=c_text,
                cited_evidence_ids=eids,
                citation_syntax_valid=claim_c_syntax,
                citation_existence_valid=claim_c_existence,
                is_attributed=claim_c_existence and claim_c_syntax,
                semantic_support_status="not_evaluated",
                is_grounded=claim_c_existence,
                structural_natures=s_natures,
                relies_only_on_party_submissions=relies_only_submissions
            ))

        if invalid_ids:
            validation_notes.append(f"Detected {len(invalid_ids)} unknown/stale/hallucinated citation ID(s): {invalid_ids}")

        if unsupported_sentences:
            validation_notes.append(f"Identified {len(unsupported_sentences)} substantive claim(s) lacking evidence citations.")

        validation_notes.append(
            "Semantic legal support status: not_evaluated (citation reference existence verified; "
            "semantic correctness requires independent verification)."
        )

        # 4. Verify substantive claims with ClaimVerifier
        contradicted_count = 0
        unsupported_count = 0
        partially_supported_count = 0
        supported_count = 0
        unverified_count = 0
        verification_notes = []

        if claims_attributions and supplied_evidence:
            self.verifier.verify_claims(claims=claims_attributions, supplied_evidence=supplied_evidence)
            contradicted_count = sum(1 for c in claims_attributions if c.verification_status == ClaimVerificationStatus.CONTRADICTED.value)
            unsupported_count = sum(1 for c in claims_attributions if c.verification_status == ClaimVerificationStatus.UNSUPPORTED.value)
            partially_supported_count = sum(1 for c in claims_attributions if c.verification_status == ClaimVerificationStatus.PARTIALLY_SUPPORTED.value)
            supported_count = sum(1 for c in claims_attributions if c.verification_status == ClaimVerificationStatus.SUPPORTED.value)
            unverified_count = sum(1 for c in claims_attributions if c.verification_status == ClaimVerificationStatus.NOT_EVALUATED.value)

        # Compute overall validity
        has_invalid = len(invalid_ids) > 0 or not citation_syntax_valid
        attribution_complete = len(unsupported_sentences) == 0
        citation_existence_valid = (len(invalid_ids) == 0) and (len(valid_ids) > 0)
        is_valid = (
            (len(valid_ids) > 0) and
            (not has_invalid) and
            citation_syntax_valid and
            citation_existence_valid and
            (attribution_complete if self.require_citations_on_all_claims else True)
        )

        cand_result = CitationValidationResult(
            is_valid=is_valid,
            validation_status="valid" if is_valid else "invalid",
            citation_syntax_valid=citation_syntax_valid,
            citation_existence_valid=citation_existence_valid,
            attribution_complete=attribution_complete,
            evidence_integrity_valid=True,
            semantic_support_status="not_evaluated",
            cited_source_ids=all_cited_ids,
            valid_source_ids=valid_ids,
            invalid_source_ids=invalid_ids,
            unsupported_sentences=unsupported_sentences,
            has_invalid_citations=has_invalid,
            validation_notes=validation_notes
        )

        # 5. Evaluate conservative acceptance policy
        policy = ClaimVerifier.evaluate_acceptance_policy(
            validation_result=cand_result,
            claims=claims_attributions,
            is_abstention=False
        )

        is_valid = policy["is_valid"]
        if contradicted_count > 0:
            validation_status = "contradicted"
            semantic_status = "contradicted"
        elif not is_valid:
            validation_status = "invalid"
            semantic_status = "unsupported" if (unsupported_count > 0 and supported_count == 0 and unverified_count == 0) else "not_evaluated"
        elif policy["accepted_status"] == "answered_with_qualification":
            validation_status = "partially_supported"
            semantic_status = "partially_supported"
        elif (
            supported_count > 0
            and supported_count == len(claims_attributions)
            and unverified_count == 0
            and partially_supported_count == 0
            and unsupported_count == 0
            and contradicted_count == 0
        ):
            validation_status = "valid"
            semantic_status = "supported"
        else:
            validation_status = "valid"
            semantic_status = "not_evaluated"

        verification_notes.append(policy["rationale"])
        for i, c in enumerate(claims_attributions, 1):
            if c.verification_method:
                verification_notes.append(f"Claim {i}: {c.verification_status} via {c.verification_method} - {c.verification_reason}")

        result = CitationValidationResult(
            is_valid=is_valid,
            validation_status=validation_status,
            citation_syntax_valid=citation_syntax_valid,
            citation_existence_valid=citation_existence_valid,
            attribution_complete=attribution_complete,
            evidence_integrity_valid=True,
            semantic_support_status=semantic_status,
            contradicted_claims_count=contradicted_count,
            unsupported_claims_count=unsupported_count,
            partially_supported_claims_count=partially_supported_count,
            supported_claims_count=supported_count,
            unverified_claims_count=unverified_count,
            cited_source_ids=all_cited_ids,
            valid_source_ids=valid_ids,
            invalid_source_ids=invalid_ids,
            unsupported_sentences=unsupported_sentences,
            has_invalid_citations=has_invalid,
            validation_notes=validation_notes,
            verification_notes=verification_notes,
            shadow_nli_disagreements_count=sum(1 for c in claims_attributions if getattr(c, "shadow_nli_disagreement", False))
        )
        return result, claims_attributions
