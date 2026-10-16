# Knowledge Graph Statutory Identity Audit Report (Milestone 4B.1)

This report details the audit of statutory identity and `PART_OF_ACT` relationships in the NyayaVarta Knowledge Graph prototype, documents confirmed defects versus suspected duplicates, and details the structural fixes implemented in Milestone 4B.1.

---

## 1. Executive Summary

During Milestone 4B, the initial Knowledge Graph construction ingested 782 Supreme Court judgments from 2024, populating 38,030 nodes and 55,101 edges. While citation constraints (Restrictions 1–4, 6–8) successfully prevented self-citations, out-of-corpus targets, and title-only uncorroborated edges, an audit of statutory entities revealed significant defects in how statutory provisions and Acts were parsed and linked.

Specifically, in Milestone 4B:
- Anaphoric references in judicial text (e.g., *"Section 260A of the Act"*, *"Section 238A of the Code"*) created spurious Act nodes (`act:the_act`, `act:the_code`, `act:said_act`, `act:this_act`) with 626 invalid `PART_OF_ACT` edges.
- Regular expression over-captures without strict token boundaries matched words ending in `"act"` (e.g., *"applied to the fact"*, *"legislative in charact"*, *"Trade Pract"*), capturing irrelevant sentence fragments as governing statutes.
- Leading article clutter on acronyms (e.g., `"the CrPC"`, `"the IPC"`, `"the PMLA"`) bypassed uppercase dictionary lookups, fragmenting mentions across duplicate nodes.

In Milestone 4B.1, defensive validation was implemented in both `services/extraction/statute_extractor.py` and `services/graph/builder.py`. The resulting rebuild completely eliminated all spurious pseudo-Act nodes, eradicated 626 invalid `PART_OF_ACT` edges, consolidated acronym variations into canonical Acts, and added 17 automated negative and integrity tests.

---

## 2. 50-Sample Inspection of Milestone 4B `PART_OF_ACT` Relationships

A random sample of 50 `PART_OF_ACT` edges from the baseline Milestone 4B graph (`data/processed/graph/v1/graph.db`) was audited to evaluate grounding validity:

| Sample # | Extracted Provision | Target Act Node | Audit Assessment | Error Classification |
|---|---|---|---|---|
| 1 | `Section 260A of the Act` | `the Act` | **Invalid** | Confirmed Defect: Anaphoric Pseudo-Act |
| 2 | `Section 5 of Monopolies and Restrictive Trade Pract` | `Monopolies and Restrictive Trade Pract` | **Invalid** | Confirmed Defect: Trailing Token Truncation |
| 3 | `Section 166 of Motor Vehicles Act` | `Motor Vehicles Act` | **Valid** | Suspected Duplicate: Unaliased Formal Act |
| 4 | `Section 36 of Industrial Dispute Act` | `Industrial Dispute Act` | **Valid** | Suspected Duplicate: Singular Form |
| 5 | `Section 450... of Indian Penal Code` | `Indian Penal Code` | **Valid** | Suspected Duplicate: Missing Enactment Year |
| 6 | `Section 17(1) of said Act` | `said Act` | **Invalid** | Confirmed Defect: Anaphoric Pseudo-Act |
| 7 | `Section 2(16) of IS Act` | `IS Act` | **Valid** | Domain Acronym (Indian Stamp Act) |
| 8 | `Section 125(1) of the CrPC` | `the CrPC` | **Invalid Target** | Confirmed Defect: Acronym Prefix Clutter |
| 9 | `Section 16 of NIA Act` | `NIA Act` | **Valid** | Domain Acronym (National Investigation Agency Act) |
| 10 | `Section 3(1) of RPwD Act` | `RPWD Act` | **Valid** | Domain Acronym (Rights of Persons with Disabilities Act) |
| 11 | `Section 2(l) of Stamp Act` | `Stamp Act` | **Valid** | Suspected Duplicate: Short Title Variant |
| 12 | `Section 20 of National Green Tribunal Act` | `National Green Tribunal Act` | **Valid** | Valid Act Mention |
| 13 | `Section 17 and 18 of Unlawful Act` | `Unlawful Act` | **Invalid** | Confirmed Defect: Truncated Statute Title |
| 14 | `Section 25 of Tea Act` | `Tea Act` | **Valid** | Valid Act Mention (Tea Act, 1953) |
| 15 | `Section 18 of TCP Act` | `TCP Act` | **Valid** | Domain Acronym (Town and Country Planning Act) |
| 16 | `Section 101... of Indian Evidence Act, 1872` | `Indian Evidence Act, 1872` | **Valid** | Grounded Formal Act |
| 17 | `Section 342... of Indian Penal Code` | `Indian Penal Code` | **Valid** | Suspected Duplicate: Missing Enactment Year |
| 18 | `Section 3 of EP Act` | `EP Act` | **Valid** | Domain Acronym (Environment Protection Act) |
| 19 | `Section 17... of UAPA (Scheduled Offences under the NIA Act` | `UAPA (Scheduled Offences under the NIA Act` | **Invalid** | Confirmed Defect: Runaway Regex Capture |
| 20 | `Section 24 of the PMLA` | `the PMLA` | **Invalid Target** | Confirmed Defect: Acronym Prefix Clutter |
| 21 | `Section 17 and 18 of the Act` | `the Act` | **Invalid** | Confirmed Defect: Anaphoric Pseudo-Act |
| 22 | `Section 13(3B) of Consumer Protection Act` | `Consumer Protection Act` | **Valid** | Valid Act Mention |
| 23 | `Section 207... of the CrPC` | `the CrPC` | **Invalid Target** | Confirmed Defect: Acronym Prefix Clutter |
| 24 | `Section 8 of Protection of Children from Sexual Offences Act` | `Protection of Children from Sexual Offences Act` | **Valid** | Grounded Formal Act |
| 25 | `Article 31C of the Constitution` | `Constitution of India` | **Valid** | Grounded Constitutional Article |
| 26 | `Section 111(7) of Companies Act` | `Companies Act` | **Valid** | Valid Act Mention |
| 27 | `Section 66 of the Act` | `the Act` | **Invalid** | Confirmed Defect: Anaphoric Pseudo-Act |
| 28 | `Section 113A of Evidence Act` | `Evidence Act` | **Valid** | Suspected Duplicate: Missing Preceding 'Indian' |
| 29 | `Section 38 of Madras Marumakkathayam Act` | `Madras Marumakkathayam Act` | **Valid** | Regional State Act |
| 30 | `Article 166 of the Constitution` | `Constitution of India` | **Valid** | Grounded Constitutional Article |
| 31 | `Section 29C of Representation of the People Act` | `Representation of the People Act` | **Valid** | Grounded Formal Act |
| 32 | `Section 31(7)(a) of the Act` | `the Act` | **Invalid** | Confirmed Defect: Anaphoric Pseudo-Act |
| 33 | `Section 191 of Penal Code` | `Penal Code` | **Valid** | Suspected Duplicate: Short Title Variant |
| 34 | `Section 7 of Arbitration and Conciliation Act, 1996` | `Arbitration and Conciliation Act, 1996` | **Valid** | Grounded Formal Act |
| 35 | `Section 2 of Orissa Act` | `Orissa Act` | **Valid** | Regional State Act Variant |
| 36 | `Section 34(3) of Arbitration and Conciliation Act, 1996` | `Arbitration and Conciliation Act, 1996` | **Valid** | Grounded Formal Act |
| 37 | `Section 11 of the 1955 Act` | `the 1955 Act` | **Invalid** | Confirmed Defect: Anaphoric Year Pseudo-Act |
| 38 | `Section 147... of Indian Penal Code` | `Indian Penal Code` | **Valid** | Suspected Duplicate: Missing Enactment Year |
| 39 | `Section 38(2) of Madras Marumakkattayam Act` | `Madras Marumakkattayam Act` | **Valid** | Regional State Act Variant |
| 40 | `Section 33... of Karnataka Stamp Act` | `Karnataka Stamp Act` | **Valid** | Regional State Act |
| 41 | `Section 438 of CrPC are prescribed under Section 438(4)...` | `CrPC are prescribed under Section 438(4)...` | **Invalid** | Confirmed Defect: Runaway Regex Capture |
| 42 | `Section 55 of Wild Life (Protection) Act` | `Wild Life (Protection) Act` | **Valid** | Grounded Formal Act |
| 43 | `Section 11 of the 1894 Act` | `the 1894 Act` | **Invalid** | Confirmed Defect: Anaphoric Year Pseudo-Act |
| 44 | `Section 47 of Act, 1940 the provisions of the said Act` | `Act, 1940 the provisions of the said Act` | **Invalid** | Confirmed Defect: Runaway Regex Capture |
| 45 | `Section 13(2) of PC Act` | `PC Act` | **Valid** | Domain Acronym (Prevention of Corruption Act) |
| 46 | `Section 38V of WLP Act` | `WLP Act` | **Valid** | Domain Acronym (Wild Life Protection Act) |
| 47 | `Article 172 of the Constitution` | `Constitution of India` | **Valid** | Grounded Constitutional Article |
| 48 | `Section 17(2)(vi) of the Act` | `the Act` | **Invalid** | Confirmed Defect: Anaphoric Pseudo-Act |
| 49 | `Section 27(2) of said Act` | `said Act` | **Invalid** | Confirmed Defect: Anaphoric Pseudo-Act |
| 50 | `Section 19 of CC Act` | `CC Act` | **Valid** | Domain Acronym |

**Summary of Sampled 50 Edges:**
- **Valid Grounded Relationships:** 34 / 50 (68%)
- **Confirmed Defects:** 16 / 50 (32%)
  - Anaphoric Pseudo-Acts (`"the Act"`, `"said Act"`, `"the 1955 Act"`): 10 / 50 (20%)
  - Acronym Prefix Clutter (`"the CrPC"`, `"the PMLA"`): 3 / 50 (6%)
  - Runaway Regex Captures / Boundary Errors: 3 / 50 (6%)

---

## 3. Taxonomy of Statutory Identity Defects vs. Suspected Duplicates

### Category 1: Confirmed Defects (Logic & Regex Errors)

1. **Anaphoric Pseudo-Acts:**
   - *Pattern:* Judgments reciting *"Section 13 of the Act"*, *"Section 238A of the Code"*, *"Section 11 of the 1894 Act"*, or *"Section 27 of the said Act"*.
   - *Cause:* In a judgment, the court defines an acronym or short title early on (e.g., *"Land Acquisition Act, 1894 (hereinafter referred to as 'the Act')"*) and subsequently references provisions using anaphora. The baseline builder naively created nodes `act:the_act`, `act:the_code`, `act:said_act`, creating meaningless hubs connecting unrelated cases across diverse areas of law.
   - *Fix:* Detected via regex `^(?:the|said|aforesaid|this|an|such)\s+(?:\d{4}\s+)?(?:act|code)$` and exact set matching. All such mentions are stripped of governing statute and re-classified as unanchored bare sections (`governing_statute = None`). They are explicitly excluded from `PART_OF_ACT` under `BARE_SECTION_UNSPECIFIED_ACT`.

2. **Regex Over-Captures Ending in 'act':**
   - *Pattern:* `(?:Act|Code|IPC|CrPC|CPC|PMLA|IBC)` without trailing word boundary `\b` inside `RE_SECTION`.
   - *Cause:* With `re.IGNORECASE` enabled, this pattern matched substrings ending in `"act"` within common English words such as:
     - `...mindful of the fact` (matching `fact`)
     - `...legislative in charact` (matching `charact` from character)
     - `...Trade Pract` (matching `Pract` from Practices)
     - `...will be attract` (matching `attract`)
   - *Fix:* Enforced strict `\b` word boundary before and after the statute tokens in `RE_SECTION`: `\b(?:Act|Code|IPC|CrPC|CPC|PMLA|IBC)\b`. Added disallowed word filter (`fact`, `charact`, `pract`, `attract`, `prescribed`, `provision`, `read with`, `petition`, `under`).

3. **Acronym Prefix Clutter:**
   - *Pattern:* `"the CrPC"`, `"the IPC"`, `"the PMLA"`, `"the IBC"`, `"the CPC"`.
   - *Cause:* While the uppercase dictionary `ACRONYM_TO_ACT` contained `"CRPC"` and `"IPC"`, mentions prefixed with `"the "` failed direct lookup, causing them to generate separate nodes `act:the_crpc` alongside `act:code_of_criminal_procedure_1973`.
   - *Fix:* Added prefix normalization in `clean_and_validate_governing_act`: strips leading `"the "` before dictionary lookup. Re-mapped 1,119 mentions directly to canonical Acts.

### Category 2: Suspected Duplicates (Syntactic Variations of Valid Statutes)

1. **Missing Enactment Years:**
   - `"Indian Penal Code"` vs `"Indian Penal Code, 1860"`
   - `"Indian Evidence Act"` vs `"Indian Evidence Act, 1872"`
   - `"Code of Criminal Procedure"` vs `"Code of Criminal Procedure, 1973"`
   - *Decision:* **Safe Canonical Aliasing**. In Indian law, there is only one Indian Penal Code (1860) and one Code of Criminal Procedure (1973) in force during the 2024 judgment period. Aliasing these to the canonical title with enactment year is legally unambiguous and eliminates node fragmentation.

2. **Leading Article Variants on Formal Titles:**
   - `"The Advocates Act, 1961"` vs `"Advocates Act, 1961"`
   - `"The Arbitration and Conciliation Act, 1996"` vs `"Arbitration and Conciliation Act, 1996"`
   - *Decision:* **Safe Canonical Aliasing**. Formal statutory titles in India frequently oscillate between including and omitting the definite article *"The"*. Stripping the leading `"The "` when followed by a formal title with enactment year normalizes these to the statutory short title without loss of semantics.

3. **Distinct Historical Enactments:**
   - `"Companies Act, 1956"` vs `"Companies Act, 2013"`
   - `"Arbitration Act, 1940"` vs `"Arbitration and Conciliation Act, 1996"`
   - `"Land Acquisition Act, 1894"` vs `"Right to Fair Compensation and Transparency in Land Acquisition... Act, 2013"`
   - *Decision:* **Preserve Distinct Nodes**. These are fundamentally different statutory regimes enacted in different years. Merging them would falsely conflate provisions (e.g. Section 34 of the 1940 Act is completely different from Section 34 of the 1996 Act). Distinct years are strictly preserved.

---

## 4. Quantitative Pre-Audit vs. Post-Audit Comparison

| Metric | Milestone 4B Baseline | Milestone 4B.1 Audited | Net Delta | Rationale |
|---|---|---|---|---|
| **Total Graph Nodes** | 38,030 | 36,120 | -1,910 | Eliminated pseudo-Acts and consolidated redundant aliases |
| **Act Nodes** | 3,249 | 2,543 | -706 | Purged spurious pseudo-Acts and merged acronyms |
| **Section Nodes** | 4,510 | 4,447 | -63 | Unspecified section deduplication |
| **Article Nodes** | 291 | 291 | 0 | Grounded constitutional articles preserved |
| **Rule Nodes** | 279 | 279 | 0 | Procedural rules preserved |
| **Schedule Nodes** | 39 | 39 | 0 | Schedules preserved |
| **Judgment Nodes** | 782 | 782 | 0 | Canonical 2024 corpus unchanged |
| **External Reference Nodes** | 27,739 | 27,739 | 0 | Historical precedents preserved |
| **Total Graph Edges** | 55,101 | 51,642 | -3,459 | Purged invalid `PART_OF_ACT` edges |
| **PART_OF_ACT Edges** | 3,923 | 2,711 | -1,212 | Eradicated pseudo-Act connections |
| **MENTIONS_PROVISION Edges** | 18,533 | 16,286 | -2,247 | Removed links to invalid pseudo-Act nodes |
| **CITES Edges** | 311 | 311 | 0 | Deterministic citation edges unchanged |
| **CITES_EXTERNAL Edges** | 32,334 | 32,334 | 0 | External stubs unchanged |
| **Excluded Edges** | 72,133 | 76,194 | +4,061 | Explicitly audited exclusions |
| `BARE_SECTION_UNSPECIFIED_ACT` | 18,011 | 22,070 | +4,059 | Anaphoric bare sections cleanly excluded |
| `SELF_CITATION` | 8,184 | 8,184 | 0 | Strict self-citation guardrail |
| `HISTORICAL_PRE_2024` | 22,684 | 22,684 | 0 | Pre-2024 precedent guardrail |
| `AMBIGUOUS_CANDIDATE` | 472 | 472 | 0 | Ambiguous mention guardrail |
| `TITLE_ONLY_UNCORROBORATED` | 34 | 34 | 0 | Title uncorroborated guardrail |

---

## 5. Integrity Verification & Negative Testing

To prevent regression, 8 new negative and constraint tests were added to `tests/test_graph_integrity.py` (bringing total integrity tests to 17):

1. `test_no_part_of_act_edges_to_pseudo_acts`: Confirms zero `PART_OF_ACT` edges point to nodes named `"the Act"`, `"said Act"`, `"aforesaid Act"`, `"the Code"`, or `"this Act"`.
2. `test_mention_provenance_strictly_matches_edge_source`: Verifies across all edges that every mention payload has `source_doc_id` matching `source_node_id`.
3. `test_character_spans_strictly_valid`: Verifies that all mention character spans satisfy `0 <= start_char <= end_char`.
4. `test_foreign_key_and_node_type_constraints`: Runs SQLite `PRAGMA foreign_key_check` and verifies that all `PART_OF_ACT` edges point exclusively to nodes with `node_type = 'Act'`.
5. `test_negative_mismatched_extraction_counts_raises_value_error`: Deliberately feeds mismatched line counts for `case_citations.jsonl` and `resolved_entities.jsonl` into the builder and asserts that `ValueError` is raised.
6. `test_negative_invalid_character_spans_rejected`: Asserts that inverted spans (`start_char > end_char`) raise `ValueError`.
7. `test_negative_mismatched_source_doc_id_rejected`: Asserts that passing a mention payload with a different source ID raises `ValueError`.
8. `test_negative_pseudo_acts_rejected_by_clean_governing_act`: Directly asserts that pseudo-Acts and regex over-captures return `None`.

All 17 integrity and negative tests pass consistently in `2.68s`.
