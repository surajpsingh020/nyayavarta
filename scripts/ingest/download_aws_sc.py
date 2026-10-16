import os
import json
import hashlib
from datetime import datetime
import boto3
from botocore import UNSIGNED
from botocore.config import Config
import concurrent.futures

S3_BUCKET = "indian-supreme-court-judgments"
MAX_DOCS = 1000
RAW_DIR = "data/raw/aws_sc"
META_DIR = os.path.join(RAW_DIR, "metadata")
PDF_DIR = os.path.join(RAW_DIR, "pdf")
MANIFEST_FILE = "manifests/aws_sc_manifest.json"

os.makedirs(META_DIR, exist_ok=True)
os.makedirs(PDF_DIR, exist_ok=True)
os.makedirs(os.path.dirname(MANIFEST_FILE), exist_ok=True)

def generate_checksum(file_path):
    hash_sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()

def download_file(s3_client, bucket, key, local_path):
    if not os.path.exists(local_path):
        s3_client.download_file(bucket, key, local_path)
    return local_path

def process_item(item):
    s3 = boto3.client('s3', config=Config(signature_version=UNSIGNED), region_name='ap-south-1')
    json_key = item['Key']
    file_name = os.path.basename(json_key)
    local_json_path = os.path.join(META_DIR, file_name)
    
    download_file(s3, S3_BUCKET, json_key, local_json_path)
    
    with open(local_json_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)
        
    path_val = metadata.get("path")
    citation_year = metadata.get("citation_year", "2024")
    
    pdf_key = f"data/pdf/year={citation_year}/english/{path_val}_EN.pdf"
    pdf_file_name = os.path.basename(pdf_key)
    local_pdf_path = os.path.join(PDF_DIR, pdf_file_name)
    
    try:
        download_file(s3, S3_BUCKET, pdf_key, local_pdf_path)
    except Exception as e:
        # Some PDFs might not exist in English
        return None
        
    return {
        "document_id": path_val,
        "source": "AWS Supreme Court Open Data",
        "source_url": f"s3://{S3_BUCKET}/{pdf_key}",
        "acquisition_date": datetime.now().isoformat(),
        "file_path": local_pdf_path,
        "metadata_path": local_json_path,
        "checksum": generate_checksum(local_pdf_path),
        "license": "CC-BY-4.0" # Assuming as per TRD
    }

def main():
    s3 = boto3.client('s3', config=Config(signature_version=UNSIGNED), region_name='ap-south-1')
    
    # List JSON files
    paginator = s3.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=S3_BUCKET, Prefix='metadata/json/year=2024/')
    
    items = []
    for page in pages:
        for obj in page.get('Contents', []):
            items.append(obj)
            if len(items) >= MAX_DOCS * 2: # Get more in case some PDFs fail
                break
        if len(items) >= MAX_DOCS * 2:
            break
            
    print(f"Found {len(items)} metadata keys. Downloading up to {MAX_DOCS}...")
    
    manifest_entries = []
    success_count = 0
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(process_item, item) for item in items]
        
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            if res:
                manifest_entries.append(res)
                success_count += 1
                if success_count % 100 == 0:
                    print(f"Downloaded {success_count} documents.")
            if success_count >= MAX_DOCS:
                # Cancel remaining
                break
                
    manifest = {
        "dataset": "AWS Supreme Court Open Data",
        "total_documents": len(manifest_entries),
        "documents": manifest_entries
    }
    
    with open(MANIFEST_FILE, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=4)
        
    print(f"Manifest saved to {MANIFEST_FILE}")

if __name__ == "__main__":
    main()
