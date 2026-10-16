# Knowledge Graph Construction & Integrity Report (Milestone 4B)

**Build Date:** 2026-10-12  
**Milestone:** 4B (Restricted Graph Prototype)  
**Corpus Scope:** 782 Canonical Supreme Court Judgments (2024 AWS Open Data Corpus)  
**Input Extractions:** 54,750 Citations | 54,750 Resolutions | 66,284 Statutory References  
**Build Runtime:** 31.68 seconds on CPU  
**Output Directory:** `data/processed/graph/v1/`  

---

## 1. Build Overview & Executive Summary

The NyayaVarta Knowledge Graph builder transformed validated Milestone 4A.1 extraction records into an inspectable, dual-format (JSONL + SQLite) legal knowledge graph enforcing all eight mandatory graph-readiness restrictions.

### Quantitative Summary:
* **Total Nodes Created:** **38,030** (across 7 node types)
* **Total Edges Created:** **55,101** (across 4 relationship types)
* **Total Edges Excluded:** **72,133** (across 6 auditable exclusion reason codes)
* **Validated Internal CITES Edges:** **311** cross-document citation edges between 2024 judgments
* **Substantive Determinism:** 100% byte-for-byte deterministic across repeated runs

---

## 2. Detailed Node Distribution

| Node Type | Count | Description | Primary Key / ID Format |
| :--- | :---: | :--- | :--- |
| **`Judgment`** | **782** | Canonical 2024 Supreme Court judgments | `doc:{document_id}` |
| **`Act`** | **3,249** | Unique statutes and codes (formal and acronyms) | `act:{normalized_title}` |
| **`Section`** | **5,651** | Grounded and bare statutory sections | `section:{act}:{num}` or `section:unspecified:{num}` |
| **`Article`** | **291** | Unique Articles of the Constitution of India | `article:constitution:{num}` |
| **`Rule`** | **279** | Procedural orders and rules (e.g. CPC Order XXI) | `rule:{order_rule}` |
| **`Schedule`** | **39** | Constitutional and statutory schedules | `schedule:{name}` |
| **`ExternalReference`** | **27,739** | Historical pre-2024 precedents (unverified stubs) | `ext:historical:{normalized_citation}` |
| **Total** | **38,030** | | |

---

## 3. Detailed Edge Distribution

| Relationship Type | Source Type | Target Type | Edge Count | Description |
| :--- | :--- | :--- | :---: | :--- |
| **`CITES`** | `Judgment` | `Judgment` | **311** | Strictly validated cross-document citations between 2024 judgments |
| **`MENTIONS_PROVISION`** | `Judgment` | `Section` / `Article` / `Rule` / `Schedule` / `Act` | **18,369** | Observational statutory references in judgment text |
| **`PART_OF_ACT`** | `Section` / `Article` / `Rule` / `Schedule` | `Act` | **4,087** | Structural hierarchy linking provisions to governing Acts |
| **`CITES_EXTERNAL`** | `Judgment` | `ExternalReference` | **32,334** | Citations linking judgments to historical external precedents |
| **Total** | | | **55,101** | |

---

## 4. Auditable Edge Exclusions Breakdown

During graph construction, **72,133 relationships were actively excluded** under the mandatory graph-readiness restrictions. Every excluded relationship is persisted to `excluded_edges.jsonl` and the SQLite `excluded_edges` table with complete mention provenance and an auditable exclusion code:

| Exclusion Reason | Count | Percentage | Mandatory Restriction Enforced |
| :--- | :---: | :---: | :--- |
| **`HISTORICAL_PRE_2024`** | **22,684** | 31.45% | Restriction 4: Bars pre-2024 precedents from resolving to 2024 judgments. |
| **`UNRESOLVED_MENTION`** | **22,750** | 31.54% | Restriction 6: Unresolved references are barred from internal edges. |
| **`BARE_SECTION_UNSPECIFIED_ACT`** | **18,009** | 24.97% | Restriction 5: Sections without governing Act cannot create `PART_OF_ACT` edges. |
| **`SELF_CITATION`** | **8,184** | 11.35% | Restriction 1: Rejects self-loops ($A \rightarrow A$). Stored as node properties. |
| **`AMBIGUOUS_CANDIDATE`** | **472** | 0.65% | Restriction 6: Ambiguous candidate sets preserved without edge creation. |
| **`TITLE_ONLY_UNCORROBORATED`** | **34** | 0.05% | Restriction 3: Rejects title-only matches lacking year $\ge 2024$ or score $\ge 0.85$. |
| **Total Excluded** | **72,133** | **100.0%** | |

---

## 5. Graph Topology & Structural Properties

### 5.1 Internal Citation Graph Sparsity (2024 Judgments)
Between the 782 judgments in the closed 2024 corpus:
* **Max Possible Directed Edges:** $782 \times 781 = 610,742$
* **Actual Internal `CITES` Edges:** **311**
* **Citation Graph Density:**
  $$D = \frac{311}{610,742} \approx 0.000509 \quad (0.051\%)$$

### 5.2 Degree Distribution for Internal `CITES`
* **Judgments with Outgoing Citations ($\text{Out-degree} > 0$):** 168 (21.5%)
* **Judgments with Incoming Citations ($\text{In-degree} > 0$):** 84 (10.7%)
* **Isolated Judgments (In-degree = 0 and Out-degree = 0 for internal citations):** 574 (73.4%)
* **Top 5 In-Degree Judgments (Most Cited 2024 Judgments in the Corpus):**
  1. `2024_7_1236_1313`: Cited by 31 other 2024 judgments
  2. `2024_9_374_396`: Cited by 17 other 2024 judgments
  3. `2024_2_1072_1120`: Cited by 13 other 2024 judgments
  4. `2024_4_473_505`: Cited by 13 other 2024 judgments
  5. `2024_8_1061_1085` (*Manish Sisodia v. ED*): Cited by 12 other 2024 judgments

### 5.3 Statutory Co-Occurrence Topology
While direct internal case-to-case citations are sparse (311 edges), the statutory bipartite graph is dense and highly connected:
* **18,369 `MENTIONS_PROVISION` edges** connect the 782 judgments to 9,471 statutory and constitutional provisions.
* Judgments frequently cluster around shared foundational provisions:
  * **Article 21 (Constitution of India):** Mentioned in 218 judgments
  * **Article 14 (Constitution of India):** Mentioned in 184 judgments
  * **Section 482 (CrPC - Inherent Powers):** Mentioned in 112 judgments
  * **Section 302 (IPC - Murder):** Mentioned in 94 judgments
  * **Section 439 (CrPC - Bail):** Mentioned in 86 judgments

---

## 6. Determinism & Integrity Sign-Off

The entire graph construction pipeline was tested for determinism. Exported files under `data/processed/graph/v1/` match the manifest checksums:

```json
{
  "nodes.jsonl": "484e5b6ba71216dd197600832fc18df882dbe0b7a8ba3243dd7c0a969bc7f654",
  "edges.jsonl": "dbbc46c6fc38466e3cfbd125fe2b7f3531b7987cc72fe016b8fc58632df6cf85",
  "excluded_edges.jsonl": "a3be0fc48e18408a28f1b402e3b2e59104cfc5a7704251ce7468138dbd2c88f1",
  "graph.db": "91df6ea334c98f921df034ee0ee4d3cb3b5d2595ea4c885e3cb27e5e347781fc"
}
```

* **Test Suite Verification:** 9 automated unit/integrity tests in `tests/test_graph_integrity.py` pass in 0.57s.
* **Full Repository Suite:** All 64 tests pass with 0 failures across the entire codebase.
