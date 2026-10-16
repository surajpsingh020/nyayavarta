"""
Generate Milestone 16 Legal Reviewer Evaluation Pack and Protocol Mapping.

Creates:
1. evaluation/rag/milestone16_reviewer_pack.jsonl (36 blinded cases with full context)
2. evaluation/rag/milestone16_reviewer_mapping.json (provenance, gold labels, system predictions)
3. evaluation/rag/milestone16_reviewer_template.jsonl (clean reviewer submission template)
"""
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
M14_PATH = PROJECT_ROOT / "evaluation" / "rag" / "milestone14_unseen_claims.jsonl"
M15_RESULTS_PATH = PROJECT_ROOT / "evaluation" / "rag" / "milestone15_verification_results.json"
AWS_SC_DIR = PROJECT_ROOT / "data" / "processed" / "aws_sc"

OUTPUT_PACK_PATH = PROJECT_ROOT / "evaluation" / "rag" / "milestone16_reviewer_pack.jsonl"
OUTPUT_MAPPING_PATH = PROJECT_ROOT / "evaluation" / "rag" / "milestone16_reviewer_mapping.json"
OUTPUT_TEMPLATE_PATH = PROJECT_ROOT / "evaluation" / "rag" / "milestone16_reviewer_template.jsonl"


def generate_pack():
    with open(M14_PATH, "r", encoding="utf-8") as f:
        cases = [json.loads(line) for line in f if line.strip()]

    m15_results = json.load(open(M15_RESULTS_PATH, "r", encoding="utf-8"))
    m15_preds = {d["review_id"]: d for d in m15_results.get("detailed_evaluations", [])}

    # Categories to include (4 cases each = 36 cases total)
    selected_categories = [
        "direct_holding_support",
        "directly_contradicted_holding",
        "unrelated_evidence",
        "multipart_partial_support",
        "missing_statutory_exception",
        "party_submissions_as_holding",
        "quoted_landmark_precedent_confusion",
        "overgeneralized_equitable_relief",
        "genuinely_ambiguous_uncertainty"
    ]

    selected_cases = []
    for cat in selected_categories:
        cat_cases = [c for c in cases if c["category"] == cat]
        selected_cases.extend(cat_cases[:4])

    print(f"Selected {len(selected_cases)} representative cases across {len(selected_categories)} categories.")

    reviewer_pack_records = []
    reviewer_template_records = []
    mapping_records = {}

    for idx, c in enumerate(selected_cases, 1):
        case_id = f"M16_REV_{idx:03d}"
        orig_id = c["review_id"]
        pred_info = m15_preds.get(orig_id, {})

        # Load document to extract surrounding context
        passage_info = c["supporting_passages"][0]
        doc_id = passage_info["document_id"]
        start_char = passage_info["start_char"]
        end_char = passage_info["end_char"]

        doc_path = AWS_SC_DIR / f"{doc_id}.json"
        surrounding_context = ""
        if doc_path.exists():
            with open(doc_path, "r", encoding="utf-8") as df:
                doc_data = json.load(df)
                full_text = doc_data.get("full_text", "")
                pre_start = max(0, start_char - 250)
                post_end = min(len(full_text), end_char + 250)
                pre_text = full_text[pre_start:start_char].strip()
                post_text = full_text[end_char:post_end].strip()
                surrounding_context = (
                    f"... [PRECEDING TEXT]:\n{pre_text}\n\n"
                    f"[CITED EVIDENCE PASSAGE]:\n{passage_info['passage_text']}\n\n"
                    f"[SUCCEEDING TEXT]:\n{post_text} ..."
                )
        else:
            surrounding_context = f"[Context not loaded; passage text]:\n{passage_info['passage_text']}"

        # 1. Blinded Reviewer Pack Entry (NO predicted status, NO gold label)
        pack_entry = {
            "case_id": case_id,
            "query": c["question"],
            "generated_claim": c["claim_sentence"],
            "cited_evidence_ids": c["cited_evidence_ids"],
            "source_document_id": doc_id,
            "source_case_title": passage_info.get("case_title", "Supreme Court Judgment"),
            "exact_source_passage": passage_info["passage_text"],
            "start_char": start_char,
            "end_char": end_char,
            "structural_label": passage_info.get("structural_label", "unspecified"),
            "surrounding_context": surrounding_context,
            "reviewer_label": None,
            "reviewer_rationale": None,
            "reviewer_flag_ambiguous": False,
            "reviewer_request_more_context": False
        }
        reviewer_pack_records.append(pack_entry)

        # 2. Reviewer Annotation Template Entry
        template_entry = {
            "case_id": case_id,
            "query": c["question"],
            "generated_claim": c["claim_sentence"],
            "reviewer_label": None,  # Choose: "supported" | "partially_supported" | "unsupported" | "contradicted" | "not_evaluated"
            "reviewer_rationale": "",
            "reviewer_flag_ambiguous": False,
            "reviewer_request_more_context": False
        }
        reviewer_template_records.append(template_entry)

        # 3. Secret Mapping Entry (Ground truth & System prediction)
        mapping_records[case_id] = {
            "case_id": case_id,
            "original_review_id": orig_id,
            "original_query_id": c["query_id"],
            "category": c["category"],
            "gold_support_label": c["support_label"],
            "system_predicted_status": pred_info.get("predicted_status", "unknown"),
            "system_verification_method": pred_info.get("verification_method", "unknown"),
            "system_verification_reason": pred_info.get("verification_reason", ""),
            "unresolved_uncertainty": pred_info.get("unresolved_uncertainty"),
            "source_structural_nature": c.get("source_structural_nature")
        }

    # Write Reviewer Pack
    OUTPUT_PACK_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PACK_PATH, "w", encoding="utf-8") as f:
        for r in reviewer_pack_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # Write Reviewer Template
    with open(OUTPUT_TEMPLATE_PATH, "w", encoding="utf-8") as f:
        for r in reviewer_template_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # Write Mapping
    with open(OUTPUT_MAPPING_PATH, "w", encoding="utf-8") as f:
        json.dump(mapping_records, f, indent=2, ensure_ascii=False)

    print(f"Generated {len(reviewer_pack_records)} pack records at {OUTPUT_PACK_PATH}")
    print(f"Generated {len(reviewer_template_records)} template records at {OUTPUT_TEMPLATE_PATH}")
    print(f"Generated {len(mapping_records)} mapping records at {OUTPUT_MAPPING_PATH}")


if __name__ == "__main__":
    generate_pack()
