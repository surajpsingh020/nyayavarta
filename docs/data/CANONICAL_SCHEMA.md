# NyayaVarta Canonical LegalDocument Schema

To unify documents coming from AWS SC, High Courts, and other supplemental sets, we have defined the following canonical schema for a `LegalDocument`.

## Core Identifiers
* `document_id`: The system-wide unique identifier (e.g., `2024_10_108_125`).
* `source_id`: Source prefixed identifier (e.g., `AWS_SC_2024_10_108_125`).
* `dedup_key`: A deterministic hash combining the `document_id`, normalized `case_title`, and the `content_hash` of the PDF text to facilitate cross-corpus deduplication.
* `content_hash`: MD5/SHA-256 hash of the extracted `full_text`.

## Legal Metadata
* `court`: The string name of the court (e.g., "Supreme Court of India").
* `court_level`: General categorization (e.g., "Supreme Court", "High Court").
* `case_title`: The full title (e.g., "VIJAY SINGH versus THE STATE OF BIHAR").
* `case_number`: The internal court registry number (e.g., "CRIMINAL APPEAL No. 1031/2015").
* `citation`: The Neutral Citation or standard reporter citation (e.g., "2024INSC735").
* `decision_date`: Date the judgment was rendered ("YYYY-MM-DD").
* `judges`: The Coram/bench of judges.
* `bench`: The size/type of the bench (e.g., "2 Judges", "Constitution Bench").
* `disposition`: The outcome/disposal nature (e.g., "Disposed off").

## Source & Provenance
* `source_url`: The exact S3 URI or URL where the raw file originated.
* `language`: The document language (e.g., "English").
* `license`: Licensing terms (e.g., "CC-BY-4.0").
* `ingestion_version`: The version of the ETL pipeline used to create this record.

## Content & Structure (To be populated by NLP/LLM layers later)
* `full_text`: The complete unstructured text extracted from the PDF.
* `facts`: (Reserved) Extracted summary of facts.
* `issues`: (Reserved) Extracted legal questions.
* `petitioner_arguments`: (Reserved) Arguments from the petitioner.
* `respondent_arguments`: (Reserved) Arguments from the respondent.
* `evidence`: (Reserved) Mentioned evidence.
* `legal_provisions`: (Reserved) Statutes and sections invoked.
* `precedents`: (Reserved) Prior case law cited.
* `court_reasoning`: (Reserved) The ratio decidendi.
* `decision`: (Reserved) The final holding.
