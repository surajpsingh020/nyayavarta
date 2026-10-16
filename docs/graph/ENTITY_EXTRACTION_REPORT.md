# Legal Entity and Citation Extraction Corpus Report (Milestone 4A)

This document reports the empirical extraction counts, entity resolution distributions, and legal entity distributions across the complete corpus of 782 Supreme Court judgments.

---

## 1. Corpus Processing Summary

- **Total Canonical Judgments Processed:** 782 documents (100% of 2024 AWS Supreme Court Open Data development subset).
- **Execution Runtime:** **40.0 seconds** (CPU single-process regex & dictionary tokenization).
- **Processing Throughput:** **19.5 judgments / second** (~1.04 MB text processed / second).
- **Output Storage Format:** Versioned JSON Lines (JSONL) with provenance under `data/processed/extraction/v1/`.

| Output Dataset | File Size | Record Count |
|---|---|---|
| `case_citations.jsonl` | **33.65 MB** | **54,750 citations** |
| `statutory_references.jsonl` | **44.37 MB** | **66,284 statutory refs** |
| `resolved_entities.jsonl` | **21.89 MB** | **54,750 entity resolutions** |
| `extraction_manifest.json` | **< 0.01 MB** | **1 manifest record** |
| **Total Extraction Footprint** | **99.91 MB** | **175,784 total records** |

---

## 2. Citation Extraction Breakdown

A total of **54,750 case citations and references** were detected and indexed:

| Citation Category | Extraction Count | Percentage of Total | Confidence Level |
|---|---|---|---|
| **Case Titles (`X v. Y`)** | 26,325 | 48.08% | Medium |
| **Supreme Court Cases (`SCC`)** | 12,956 | 23.66% | High |
| **Supreme Court Reports (`SCR`)** | 8,225 | 15.02% | High |
| **Unanchored Mentions (`in the case of X`)** | 3,405 | 6.22% | Low |
| **Neutral Citations (`YYYY INSC N`)** | 1,623 | 2.96% | High |
| **SCC OnLine (`YYYY SCC OnLine SC N`)** | 1,209 | 2.21% | High |
| **All India Reporter (`AIR YYYY SC N`)** | 1,007 | 1.84% | High |
| **Total Citations** | **54,750** | **100.0%** | |

### Treatment / Observational Signal Occurrences
Where a citation was accompanied by an explicit procedural or judicial signal:
- `referred to`: 1,520 mentions
- `followed`: 266 mentions
- `distinguished`: 129 mentions
- `cited`: 118 mentions
- `relied upon`: 105 mentions
- `held inapplicable`: 91 mentions
- `overruled`: 66 mentions
- `approved`: 46 mentions

*Guardrail Note: These signals are extracted strictly as observational text features. In accordance with system instructions, they are not inferred to establish binding precedent.*

---

## 3. Statutory Reference Breakdown

A total of **66,284 statutory references** were extracted and normalized:

| Statutory Category | Extraction Count | Examples in Corpus |
|---|---|---|
| **Statutory Sections & Subsections** | 28,973 | `Section 302`, `Section 45(1)(ii)`, `u/s 438`, `Section 302/34` |
| **Acts & Statutes (Formal & Acronym)**| 23,436 | `Indian Penal Code, 1860`, `Limitation Act, 1963`, `PMLA`, `IBC` |
| **Constitutional Articles** | 10,082 | `Article 21`, `Article 142`, `Articles 14, 15 and 21`, `Art. 341` |
| **Procedural Orders & Rules** | 2,760 | `Order XXI Rule 99`, `Order VII Rule 11`, `Rule 9(4)` |
| **Constitutional & Statutory Schedules**| 1,033 | `Tenth Schedule`, `Seventh Schedule`, `Schedule I` |
| **Total Statutory References** | **66,284** | |

### Top 10 Most Frequently Referenced Statutes in the Corpus
1. **Constitution of India:** 6,592 references
2. **Indian Penal Code, 1860:** 2,393 references
3. **Code of Criminal Procedure, 1973:** 2,033 references
4. **Code of Civil Procedure, 1908:** 876 references
5. **Insolvency and Bankruptcy Code, 2016:** 587 references
6. **Limitation Act, 1963:** 524 references
7. **Prevention of Money Laundering Act, 2002 (PMLA):** 461 references
8. **Indian Evidence Act, 1872:** 412 references
9. **Negotiable Instruments Act, 1881:** 389 references
10. **Specific Relief Act, 1963:** 318 references

---

## 4. Entity Resolution Distribution

Entity resolution links extracted citation mentions to canonical documents in the 782-judgment development corpus using a conservative, non-fabricating hierarchy:

| Resolution State | Total Mentions | Share | Definition & Operational Handling |
|---|---|---|---|
| **`unresolved`** | **45,434** | **82.98%** | Historical citation (pre-2024 SCC/AIR/SCR) or external High Court judgment not in 2024 corpus. Stored with target ID `null`. |
| **`resolved`** | **8,844** | **16.15%** | Unambiguously resolved to a single document in the corpus (1,623 via neutral citation, 7,221 via title overlap & self-reference). |
| **`ambiguous`** | **472** | **0.86%** | Multiple candidate documents tied with near-identical title similarity (e.g., related appeals sharing a state title). Candidates preserved. |

### Top In-Corpus Cited Judgments (2024 Supreme Court)
Cross-judgment citations where one 2024 Supreme Court judgment cited another judgment in the same 2024 development corpus:
1. `2024_7_1236_1313`: Cited in **31 other judgments**
2. `2024_9_374_396`: Cited in **17 other judgments**
3. `2024_2_1072_1120`: Cited in **13 other judgments**
4. `2024_4_473_505`: Cited in **13 other judgments**
5. `2024_8_1061_1085`: Cited in **12 other judgments**

---

## 5. Storage and Provenance Metadata

All extraction records are stored under `data/processed/extraction/v1/`:
- **Provenance Field:** `AWS Open Data` tracked on every JSONL record.
- **Pipeline Version:** `1.0.0`
- **Audit Manifest:** `data/processed/extraction/v1/extraction_manifest.json`
- **Reproducibility:** Pipeline executes deterministically in 40.0s on standard CPU hardware.
