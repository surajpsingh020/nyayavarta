import os
import sys
import subprocess
import json
import hashlib
from datetime import datetime

DATASET = "adarshsingh0903/legal-dataset-sc-judgments-india-19502024"
RAW_DIR = "data/raw"
MANIFEST_DIR = "manifests"

def check_credentials():
    if not os.environ.get("KAGGLE_USERNAME") or not os.environ.get("KAGGLE_KEY"):
        print("Error: KAGGLE_USERNAME and KAGGLE_KEY environment variables must be set.")
        return False
    return True

def download_dataset():
    os.makedirs(RAW_DIR, exist_ok=True)
    os.makedirs(MANIFEST_DIR, exist_ok=True)
    
    print(f"Downloading dataset {DATASET}...")
    try:
        subprocess.run([sys.executable, "-m", "kaggle", "datasets", "download", "-d", DATASET, "-p", RAW_DIR], check=True)
        print("Download completed.")
        
        zip_path = os.path.join(RAW_DIR, "legal-dataset-sc-judgments-india-19502024.zip")
        if os.path.exists(zip_path):
            print("Unzipping dataset...")
            import zipfile
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(RAW_DIR)
            print("Unzip completed.")
    except Exception as e:
        print(f"Failed to download dataset: {e}")
        return False
    return True

def generate_checksum(file_path):
    hash_sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()

def generate_manifest():
    print("Generating manifest...")
    manifest = {
        "dataset_source": "Kaggle",
        "dataset_name": DATASET,
        "acquisition_date": datetime.now().isoformat(),
        "files": []
    }
    
    for root, _, files in os.walk(RAW_DIR):
        for file in files:
            if file == "legal-dataset-sc-judgments-india-19502024.zip":
                continue
            file_path = os.path.join(root, file)
            size = os.path.getsize(file_path)
            checksum = generate_checksum(file_path)
            manifest["files"].append({
                "file_name": file,
                "relative_path": os.path.relpath(file_path, RAW_DIR),
                "size_bytes": size,
                "checksum_sha256": checksum
            })
            
    manifest_path = os.path.join(MANIFEST_DIR, "dataset_manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=4)
    print(f"Manifest saved to {manifest_path}")

if __name__ == "__main__":
    if check_credentials():
        if download_dataset():
            generate_manifest()
    else:
        # Generate an empty manifest if failed
        generate_manifest()
        sys.exit(1)
