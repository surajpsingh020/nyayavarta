# AWS Supreme Court Data Profile

This profile details the sample subset from the AWS Supreme Court Open Data corpus.

## Dataset Details
- **Source Bucket:** `s3://indian-supreme-court-judgments/`
- **Region:** `ap-south-1` (Mumbai)
- **Sample Selection:** Judgments corresponding to the year 2024 prefix.

## Sample Statistics
- **Total Metadata JSONs Discovered:** 782
- **PDFs Successfully Downloaded:** 782
- **Processed Documents:** 782
- **Duplicates Found:** 0
- **Acquisition Date:** {current_date}

## Metadata Fields Discovered (Source Schema)
The raw JSON payload from the AWS S3 `metadata/json` prefix contains a `raw_html` string (an HTML snippet from the eCourts website), as well as a few top-level identifiers:
- `path` (e.g., "2024_10_108_125")
- `citation_year` (e.g., "2024")
- `nc_display` (e.g., "2024INSC735")
- `scraped_at` (e.g., "2025-06-12T21:53:32.987911")

Inside the `raw_html`, we can parse out the following semantic fields using DOM traversal:
- **Title** (e.g., "VIJAY SINGH @ VIJAY KR. SHARMA versus THE STATE OF BIHAR")
- **Coram/Judges** (e.g., "BELA M. TRIVEDI, SATISH CHANDRA SHARMA")
- **Decision Date** (e.g., "25-09-2024")
- **Case No** (e.g., "CRIMINAL APPEAL No. 1031/2015")
- **Disposal Nature** (e.g., "Disposed off")
- **Bench** (e.g., "2 Judges")

## Data Quality Observations
- **Missing Fields:** The dataset natively lacks structured legal issue categorization, distinct pre-extracted legal provisions, argument segmentation, and relational citations. These currently exist only as unstructured strings inside the PDF text.
- **Language Coverage:** Some paths point to non-English languages (Hindi `_HIN.pdf`, Punjabi `_PUN.pdf`, etc.). The ETL currently attempts to pull the English base file (`_EN.pdf`).
