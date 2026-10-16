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

        # 1. Check for explicit abstention / insufficient evidence
        # Must start with or explicitly declare insufficient evidence rather than just mention it in passing
        ans_lower = ans_trimmed.lower()
        is_explicit_abstention = (
            ans_lower.startswith("insufficient evidence") or
            ans_lower == "no relevant judgments found in the corpus for this query."
        )

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

        # If answer is explicit abstention and has NO citations, handle cleanly
        if is_explicit_abstention and len(unique_cited) == 0:
            validation_notes.append("System explicitly declared abstention due to insufficient evidence.")
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
            is_meta = is_heading or is_bench_header or is_structural or any(
                s.lower().startswith(m) for m in [
                    "insufficient evidence", "as stated above", "in conclusion",
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
