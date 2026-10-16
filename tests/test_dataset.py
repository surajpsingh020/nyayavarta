import os
import json
import pytest

def test_dataset_discovery():
    # Tests if the ingest and inspect scripts exist
    assert os.path.exists("scripts/ingest/download_kaggle.py")
    assert os.path.exists("scripts/inspect/profile_dataset.py")

def test_manifest_generation():
    # Tests if manifest was generated (even if empty)
    assert os.path.exists("manifests/dataset_manifest.json")
    with open("manifests/dataset_manifest.json", "r") as f:
        manifest = json.load(f)
        assert "dataset_source" in manifest
        assert manifest["dataset_source"] == "Kaggle"
        assert "files" in manifest

def test_schema_profile_generation():
    # Tests if the profile markdown and json are created
    assert os.path.exists("docs/data/kaggle_sc_profile.md")
    assert os.path.exists("docs/data/kaggle_sc_profile.json")

def test_sample_generation():
    # Test if sample directory exists
    assert os.path.exists("data/raw/sample")
    
def test_checksum_generation():
    manifest_path = "manifests/dataset_manifest.json"
    if os.path.exists(manifest_path):
        with open(manifest_path, "r") as f:
            manifest = json.load(f)
            if len(manifest["files"]) > 0:
                assert "checksum_sha256" in manifest["files"][0]
