import os
import json
import glob
import shutil
from collections import Counter

RAW_DIR = "data/raw"
DOCS_DATA_DIR = "docs/data"
SAMPLE_DIR = os.path.join(RAW_DIR, "sample")

def profile_dataset():
    os.makedirs(DOCS_DATA_DIR, exist_ok=True)
    os.makedirs(SAMPLE_DIR, exist_ok=True)
    
    file_types = Counter()
    total_size = 0
    file_count = 0
    
    for root, _, files in os.walk(RAW_DIR):
        if "sample" in root: continue
        for file in files:
            if file == "legal-dataset-sc-judgments-india-19502024.zip": continue
            file_count += 1
            ext = os.path.splitext(file)[1].lower()
            file_types[ext] += 1
            total_size += os.path.getsize(os.path.join(root, file))
            
    stats = {
        "file_count": file_count,
        "total_size_bytes": total_size,
        "file_types": dict(file_types),
        "notes": "Dataset empty or not downloaded due to missing Kaggle credentials." if file_count == 0 else "Profiled successfully."
    }
    
    copied = 0
    if file_count > 0:
        for root, _, files in os.walk(RAW_DIR):
            if "sample" in root: continue
            for file in files:
                if file == "legal-dataset-sc-judgments-india-19502024.zip": continue
                if copied >= 500: break
                src = os.path.join(root, file)
                dst = os.path.join(SAMPLE_DIR, file)
                if not os.path.exists(dst):
                    shutil.copy2(src, dst)
                copied += 1
            if copied >= 500: break
            
    stats["sample_size"] = copied

    with open(os.path.join(DOCS_DATA_DIR, "kaggle_sc_profile.json"), "w") as f:
        json.dump(stats, f, indent=4)
        
    markdown_report = f"""# Dataset Profile: Kaggle SC Judgments India (1950-2024)

- **File count**: {file_count}
- **Total size**: {total_size / (1024*1024):.2f} MB
- **File types**: {dict(file_types)}
- **Sample size**: {copied} files

## Inspection Details
Since this is a collection of PDF files (as per Kaggle description), we cannot automatically infer columns/fields, missing-value percentages, row counts, etc., without performing text extraction and NLP. The initial dataset is unstructured text.

## Notes
{stats['notes']}
"""
    with open(os.path.join(DOCS_DATA_DIR, "kaggle_sc_profile.md"), "w") as f:
        f.write(markdown_report)
        
    print(f"Profile saved to {DOCS_DATA_DIR}/kaggle_sc_profile.md")

if __name__ == "__main__":
    profile_dataset()
