# ETL Design: Raw to Processed

This document outlines the first stage of our ETL pipeline, migrating the raw AWS Open Data assets into the canonical NyayaVarta `LegalDocument` schema.

## 1. Extraction
* **Source:** `s3://indian-supreme-court-judgments/` (Anonymous Access)
* **Metadata Downloader:** Iterates through `metadata/json/year=YYYY/` to pull the raw HTML metadata stubs.
* **Payload Downloader:** For each JSON stub, infers the PDF path (`data/pdf/year=YYYY/english/{path}_EN.pdf`) and downloads it to `data/raw/aws_sc/pdf/`.

## 2. Transformation
The transformation occurs locally without requiring GPUs or LLMs, ensuring a fast, CPU-bound parsing pipeline.
* **HTML Parsing (BeautifulSoup):** 
  - The `raw_html` attribute inside the JSON contains an eCourts summary block.
  - We extract `case_title`, `judges`, `decision_date`, `case_no`, `disposal_nature`, and `bench` directly from the DOM tags (e.g., `<strong class="caseDetailsTD">`).
* **PDF Text Extraction (PyMuPDF):**
  - The raw PDF file is opened and text is sequentially extracted page by page.
  - The text is concatenated into the `full_text` attribute of the canonical schema.

## 3. Deduplication Strategy
To handle duplicate judgments (e.g., appeals of the same name or multiple uploads):
- We normalize the `case_title` (lowercased, stripped of non-alphanumeric characters).
- We generate an MD5 `content_hash` of the extracted `full_text`.
- We construct a `dedup_key` = `{document_id}_{normalized_title}_{content_hash}`.
- If this key has already been processed in the current ETL run, the duplicate is skipped/logged.

## 4. Loading
* The canonical representation is serialized to a standard `.json` file.
* Saved into `data/processed/aws_sc/{document_id}.json`.
* This processed folder acts as the direct input corpus for the Retrieval and Chunking engines (Milestone 3).
