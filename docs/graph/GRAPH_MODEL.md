# NyayaVarta Knowledge Graph Model Specification (Milestone 4B)

**Version:** 1.0.0  
**Status:** Approved & Enforced  
**Engine:** SQLite & Deterministic JSONL (Dual Representation)  
**Corpus Scope:** 782 Canonical Supreme Court Judgments (2024 AWS Open Data Corpus)  

---

## 1. Architectural Philosophy & Non-Inference Guardrails

The NyayaVarta Knowledge Graph is a **restricted, evidence-first graph model** built from validated textual extractions. It deliberately avoids optimistic heuristics that produce hallucinated or circular legal authority.

> [!IMPORTANT]
> **Legal Epistemology & Non-Inference Policy:**
> 1. **No Ratio Decidendi Inference:** An edge `[:CITES]` indicates that judgment $A$ cited judgment $B$ in its text. It does **not** signify that $B$ was followed, applied, or formed the binding *ratio decidendi* of $A$.
> 2. **No Legislative Applicability Inference:** An edge `[:MENTIONS_PROVISION]` indicates that a statutory section, article, rule, or act was referenced in the opinion. It does **not** imply that the provision governed the case, was constitutional, or remains good law under current Indian statutes.
> 3. **Closed Corpus Boundary:** The current corpus is restricted to 782 Supreme Court judgments delivered in 2024. All citations to precedents delivered prior to 2024 are external references and are strictly barred from resolving to internal 2024 judgments.

---

## 2. Node Schema

The graph defines seven discrete node types:

### 2.1 `Judgment` Node
Represents a canonical judgment in the corpus.
* **Identifier Format:** `doc:{document_id}` (e.g. `doc:2024_10_108_125`)
* **Canonical ID:** Document ID from `data/processed/aws_sc/`
* **Properties:**
  * `document_id` (str): Unique document slug (e.g. `2024_10_108_125`)
  * `case_title` (str): Full title of the case (e.g. `VIJAY SINGH @ VIJAY KR. SHARMA versus THE STATE OF BIHAR`)
  * `case_number` (str): Formal registry number (e.g. `CRIMINAL APPEAL No. 1031/2015`)
  * `citation` (str): Neutral citation (e.g. `2024INSC735`)
  * `decision_date` (str): Date of judgment (DD-MM-YYYY)
  * `judges` (str): Bench composition
  * `header_citations` (list of str): Self-referential citations from the judgment header (stored as node properties, not edges)

### 2.2 `Act` Node
Represents a formal legislation or code.
* **Identifier Format:** `act:{normalized_act_name}` (e.g. `act:indian_penal_code_1860`, `act:constitution_of_india`)
* **Canonical ID:** Official Act name
* **Properties:**
  * `year` (int, optional): Enactment year (e.g. `1860`, `1950`)

### 2.3 `Section` Node
Represents a statutory section or subsection.
* **Identifier Format:**
  * Grounded Section: `section:{normalized_act_name}:{normalized_sec_num}` (e.g. `section:indian_penal_code_1860:302`)
  * Bare Unspecified Section: `section:unspecified:{normalized_sec_num}` (e.g. `section:unspecified:302`)
* **Properties:**
  * `section_numbers` (str): Extracted section tokens (e.g. `302`, `45`, `14(1)`)
  * `governing_statute` (str or null): Associated Act if explicitly stated in token/phrase; `null` if bare

### 2.4 `Article` Node
Represents a constitutional article.
* **Identifier Format:** `article:constitution:{article_number}` (e.g. `article:constitution:21`, `article:constitution:14`)
* **Properties:**
  * `article_number` (str): Article identifier (e.g. `21`, `19(1)(g)`)
  * `governing_act` (str): Always `"Constitution of India"`

### 2.5 `Rule` Node
Represents a procedural order and rule (e.g., Code of Civil Procedure, Supreme Court Rules).
* **Identifier Format:** `rule:{normalized_order_rule}` (e.g. `rule:order_xxi_rule_99`)
* **Properties:**
  * `order` (str): Order number (e.g. `XXI`)
  * `rule` (str): Rule number (e.g. `99`)

### 2.6 `Schedule` Node
Represents a constitutional or statutory schedule.
* **Identifier Format:** `schedule:{normalized_schedule_name}` (e.g. `schedule:tenth_schedule`)
* **Properties:**
  * `schedule_name` (str): Schedule name

### 2.7 `ExternalReference` Node
Represents an external precedent pre-dating the 2024 corpus or outside Supreme Court jurisdiction.
* **Identifier Format:** `ext:historical:{normalized_citation}` (e.g. `ext:historical:1980_1_scc_81`)
* **Properties:**
  * `raw_text` (str): Exact surface mention
  * `citation_type` (str): Reporter category (`scc`, `air`, `scr`)
  * `verified` (bool): Always `False`
  * `external_source` (str): `"Unverified Historical Reference"`

---

## 3. Edge Schema & Relationship Types

Edges are directed and deterministic.

### 3.1 Edge Types
1. **`CITES`** (`Judgment -> Judgment`):
   * Represents an internal, verified cross-judgment citation between two 2024 judgments in the canonical corpus.
   * Confidence: `high` (exact neutral citation) or `medium` (corroborated title overlap $\ge 0.85$ with year $\ge 2024$).
2. **`MENTIONS_PROVISION`** (`Judgment -> Section | Article | Rule | Schedule | Act`):
   * Represents an observational textual reference to a statutory provision or statute within the judgment text.
   * Confidence: `high` or `medium`.
3. **`PART_OF_ACT`** (`Section | Article | Rule | Schedule -> Act`):
   * Structural hierarchical relationship linking a provision to its governing Act.
   * Only instantiated when `governing_statute` is non-null.
4. **`CITES_EXTERNAL`** (`Judgment -> ExternalReference`):
   * Links a judgment to an unverified external historical citation stub.
   * Confidence: `low`.

---

## 4. Edge Identity Rule & Provenance Preservation

### 4.1 Deterministic Edge Identity
To prevent duplicate edges across repeated runs or multi-mention passages while avoiding edge explosion:
$$\text{Edge ID} = \text{SHA256}(\text{source\_node\_id} + \text{"->"} + \text{relationship\_type} + \text{"->"} + \text{target\_node\_id})[0:16]$$

* A directed edge between source and target is strictly unique.
* If a judgment mentions a precedent 5 times across its text (e.g. in facts, arguments, and conclusions), **exactly one edge is created**.

### 4.2 Multi-Mention Provenance Array
Deduplicating edges does **not** discard distinct citation mentions. Each edge retains a complete array of `mentions`:
```json
{
  "edge_id": "a1b2c3d4e5f67890",
  "source_node_id": "doc:2024_8_717_726",
  "target_node_id": "doc:2024_8_1061_1085",
  "relationship_type": "CITES",
  "confidence": "high",
  "mention_count": 2,
  "mentions": [
    {
      "source_doc_id": "2024_8_717_726",
      "citation_type": "neutral_insc",
      "raw_text": "2024 INSC 595",
      "normalized_citation": "2024INSC595",
      "start_char": 1420,
      "end_char": 1433,
      "extraction_method": "regex_neutral_insc",
      "match_method": "exact_neutral_citation",
      "treatment_signal": "considered",
      "provenance": "AWS Open Data"
    },
    {
      "source_doc_id": "2024_8_717_726",
      "citation_type": "case_title",
      "raw_text": "Manish Sisodia v. Directorate of Enforcement",
      "normalized_citation": "Manish Sisodia v. Directorate of Enforcement",
      "start_char": 1370,
      "end_char": 1414,
      "extraction_method": "regex_case_name",
      "match_method": "title_keyword_overlap",
      "treatment_signal": null,
      "provenance": "AWS Open Data"
    }
  ]
}
```

---

## 5. Mandatory Restriction Policies & Exclusion Taxonomy

The graph builder enforces 8 strict rules during graph construction. Every excluded relationship is persisted to `excluded_edges.jsonl` and the SQLite `excluded_edges` table with an auditable reason code:

| Exclusion Reason | Trigger Condition | Rationale & Action Taken |
| :--- | :--- | :--- |
| **`SELF_CITATION`** | `source_doc_id == target_doc_id` or `is_self_citation == True` | Prevents self-loop citation edges ($A \rightarrow A$). Mentions are stored as properties on the Judgment node (`header_citations`). |
| **`TARGET_NOT_IN_CORPUS`** | `target_doc_id not in corpus_doc_ids` | Prevents orphan edges pointing to non-existent document nodes. |
| **`HISTORICAL_PRE_2024`** | `cite_year < 2024` or `historical_reporter_pre_2024` | Bars pre-2024 precedents from resolving to 2024 corpus judgments. Mapped to `ExternalReference` stub or excluded. |
| **`TITLE_ONLY_UNCORROBORATED`** | Title keyword overlap without year $\ge 2024$ or confidence $< 0.85$ | Prevents false cross-era links (e.g. matching *State of Punjab v. Davinder Singh (2020)* to 2024 decision). |
| **`AMBIGUOUS_CANDIDATE`** | `resolution_status == 'ambiguous'` | Preserves tied candidate IDs explicitly without forcing an edge. |
| **`UNRESOLVED_MENTION`** | `resolution_status == 'unresolved'` | Prohibits guessing internal targets for unresolvable mentions. |
| **`BARE_SECTION_UNSPECIFIED_ACT`** | Section mention where `governing_statute == null` | Creates an unanchored Section node (`section:unspecified:{num}`) but **strictly prohibits** creating a `PART_OF_ACT` edge to any Act. |

---

## 6. Storage & Query Layer

The model is persisted in two interchangeable representations:
1. **Deterministic JSONL:**
   - `nodes.jsonl`: One JSON object per node, sorted by `node_id`.
   - `edges.jsonl`: One JSON object per edge, sorted by `edge_id`.
   - `excluded_edges.jsonl`: One JSON object per excluded edge.
2. **Relational SQLite (`graph.db`):**
   - Tables: `nodes`, `edges`, `excluded_edges`.
   - Foreign key constraints enforced: `edges.source_node_id` and `edges.target_node_id` reference `nodes.node_id`.
   - Indexed on `node_type`, `source_node_id`, `target_node_id`, `relationship_type`, and `exclusion_reason`.
