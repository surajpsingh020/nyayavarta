# Legal Citation & Entity Extraction Evaluation Report (Milestone 4A)

This document reports empirical precision, recall, and entity resolution accuracy measured against a manually reviewed gold benchmark of 116 citations across 19 diverse legal passages sampled from the canonical Supreme Court corpus.

---

## 1. Overall Performance Metrics

| Metric | Measured Value | Benchmark Target / Operational Standard |
|---|---|---|
| **Citation Extraction Precision** | **92.92%** (105 / 113) | $\ge 90.0\%$ |
| **Citation Extraction Recall** | **90.52%** (105 / 116) | $\ge 85.0\%$ |
| **F1 Score** | **0.9170** | $\ge 0.88$ |
| **Entity Resolution Accuracy** | **80.95%** (85 / 105) | $\ge 80.0\%$ |
| **Unresolved Rate** | **87.62%** (92 / 105) | Expected (80–90% for historical citations) |
| **Ambiguous Rate** | **0.95%** (1 / 105) | Operational guardrail $\le 5.0\%$ |

---

## 2. Extraction Performance by Citation Type

| Citation Type | Gold Citations | Extracted Mentions | True Positives | False Positives | False Negatives | Precision | Recall |
|---|---|---|---|---|---|---|---|
| `air` | 13 | 13 | 13 | 0 | 0 | **100.0%** | **100.0%** |
| `case_title` | 45 | 43 | 38 | 5 | 7 | **88.4%** | **84.4%** |
| `neutral_insc` | 9 | 9 | 9 | 0 | 0 | **100.0%** | **100.0%** |
| `scc` | 29 | 27 | 27 | 0 | 2 | **100.0%** | **93.1%** |
| `scc_online` | 2 | 2 | 2 | 0 | 0 | **100.0%** | **100.0%** |
| `scr` | 15 | 13 | 13 | 0 | 2 | **100.0%** | **86.7%** |
| `unanchored_mention` | 3 | 6 | 3 | 3 | 0 | **50.0%** | **100.0%** |
| **Total** | **116** | **113** | **105** | **8** | **11** | **92.92%** | **90.52%** |

---

## 3. Entity Resolution Analysis

- **Total Mentions Evaluated for Resolution:** 105 true positive extracted mentions
- **Gold Status Distribution:** `{'unresolved': 80, 'resolved': 24, 'ambiguous': 1}`
- **Predicted Status Distribution:** `{'unresolved': 92, 'resolved': 12, 'ambiguous': 1}`
- **Correct Prediction Count:** 85 / 105 (**80.95%**)

### Resolution Insights:
1. **Conservative Safety Invariant:** When in doubt between `resolved` and `unresolved`, the system leans towards `unresolved`. Zero false target documents were linked to non-corpus cases.
2. **Neutral Citations (100% Accuracy):** Every neutral citation (`YYYY INSC N`) targeting an in-corpus document resolved correctly with confidence 1.0.
3. **Ambiguity Preservation:** Generic appeal names (e.g. `State of Madhya Pradesh v. Accused`) where multiple appeals share the title are preserved with status `ambiguous` and candidate IDs recorded.

---

## 4. Annotation Process & Evaluation Protocol

1. **Passage Sampling:** 19 paragraphs were selected across criminal, civil, constitutional, tax, insolvency, service, and property law judgments in `data/processed/aws_sc/`.
2. **Annotation Schema:** Each passage was read to identify every citation mention, recording raw text, reporter type, normalized citation, gold resolution status (`resolved`, `ambiguous`, `unresolved`), and verified target corpus document ID (`target_doc_id`).
3. **Corpus Cross-Verification:** For all citations annotated as `resolved`, the referenced judgment was verified to exist in `data/processed/aws_sc/` by checking neutral citations and case titles.
4. **Benchmark Location:** Stored in `evaluation/citations/annotated_citations_sample.json`.

---

## 5. Limitations Identified

1. **Unanchored Mentions Precision:** Textual mentions ("in the case of X") achieved 50% precision due to phrases like "in the case of an appeal". These are assigned `confidence: low` in the pipeline schema.
2. **Complex Multi-Party Title Splitting:** Occasionally party names joined by multiple `@` aliases or complex intervener descriptions are truncated by the boundary regex.
3. **Historical Precedents Out-of-Corpus:** Since the current corpus comprises only 782 judgments from 2024, ~83% of all cited cases refer to pre-2024 jurisprudence. Full resolution of these references requires scaling the corpus to multi-year historical archives in future milestones.
