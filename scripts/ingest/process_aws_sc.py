import os
import json
import hashlib
from bs4 import BeautifulSoup
import fitz  # PyMuPDF
from datetime import datetime

MANIFEST_FILE = "manifests/aws_sc_manifest.json"
PROCESSED_DIR = "data/processed/aws_sc"

os.makedirs(PROCESSED_DIR, exist_ok=True)

def parse_html_metadata(html_str):
    soup = BeautifulSoup(html_str, "html.parser")
    
    # Extract title
    title_element = soup.find("strong")
    title = title_element.text.strip() if title_element else None
    
    # Extract Coram (Judges)
    coram = None
    for strong in soup.find_all("strong"):
        if strong.text.startswith("Coram :"):
            coram = strong.text.replace("Coram :", "").strip()
            break
            
    # Extract case details
    details = {}
    case_details_td = soup.find(class_="caseDetailsTD")
    if case_details_td:
        fonts = case_details_td.find_all("font")
        spans = case_details_td.find_all("span")
        
        # Usually spans are the keys and fonts are the values
        for span, font in zip(spans, fonts):
            key = span.text.strip().strip("|").strip().replace(" :", "")
            value = font.text.strip()
            details[key] = value
            
    return {
        "title": title,
        "judges": coram,
        "decision_date": details.get("Decision Date"),
        "case_no": details.get("Case No"),
        "disposal_nature": details.get("Disposal Nature"),
        "bench": details.get("Bench")
    }

def extract_pdf_text(pdf_path):
    try:
        doc = fitz.open(pdf_path)
        text = "\n".join([page.get_text() for page in doc])
        return text.strip()
    except Exception as e:
        return ""

def process_document(entry):
    doc_id = entry["document_id"]
    pdf_path = entry["file_path"]
    meta_path = entry["metadata_path"]
    
    with open(meta_path, "r", encoding="utf-8") as f:
        raw_meta = json.load(f)
        
    html_meta = parse_html_metadata(raw_meta.get("raw_html", ""))
    
    # Read PDF text
    full_text = extract_pdf_text(pdf_path)
    
    # Deduplication identifiers
    norm_title = "".join([c.lower() for c in (html_meta.get("title") or "") if c.isalnum()])
    content_hash = hashlib.md5(full_text.encode("utf-8")).hexdigest() if full_text else ""
    dedup_key = f"{norm_title}_{content_hash}"
    
    canonical_doc = {
        "document_id": doc_id,
        "source_id": f"AWS_SC_{doc_id}",
        "court": "Supreme Court of India",
        "court_level": "Supreme Court",
        "case_title": html_meta.get("title"),
        "case_number": html_meta.get("case_no"),
        "citation": raw_meta.get("nc_display"),
        "decision_date": html_meta.get("decision_date"),
        "judges": html_meta.get("judges"),
        "parties": None, # Complex to extract accurately without full NLP
        "legal_domain": None,
        "language": "English",
        "source_url": entry["source_url"],
        "license": "unverified", "provenance": "AWS Open Data", "license_verified": False,
        "full_text": full_text,
        "facts": None,
        "issues": None,
        "petitioner_arguments": None,
        "respondent_arguments": None,
        "evidence": None,
        "legal_provisions": None,
        "precedents": None,
        "court_reasoning": None,
        "decision": None,
        "disposition": html_meta.get("disposal_nature"),
        "content_hash": content_hash,
        "dedup_key": dedup_key,
        "ingestion_version": "1.0",
        "index_version": None
    }
    
    processed_path = os.path.join(PROCESSED_DIR, f"{doc_id}.json")
    with open(processed_path, "w", encoding="utf-8") as f:
        json.dump(canonical_doc, f, indent=4)
        
    return canonical_doc

def main():
    if not os.path.exists(MANIFEST_FILE):
        print("Manifest not found.")
        return
        
    with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
        manifest = json.load(f)
        
    seen_dedup = set()
    duplicate_count = 0
    processed_count = 0
    
    for entry in manifest["documents"]:
        doc = process_document(entry)
        if doc["dedup_key"] in seen_dedup:
            duplicate_count += 1
            # In a real system, we might delete the duplicate JSON or ignore it
            # We'll just count it here.
        else:
            seen_dedup.add(doc["dedup_key"])
            processed_count += 1
            
        if (processed_count + duplicate_count) % 100 == 0:
            print(f"Processed {processed_count + duplicate_count} documents.")
            
    # Write summary
    print(f"Total processed: {processed_count}")
    print(f"Duplicates found: {duplicate_count}")

if __name__ == "__main__":
    main()
