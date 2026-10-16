# Dataset Assessment

## 1. What the dataset actually contains
The target dataset ("Legal Dataset: SC Judgments India (1950-2024)") consists of approximately 26,000 PDF documents representing Supreme Court of India judgments. Because no Kaggle API credentials were provided to the agent in this environment, the raw files could not be completely retrieved, but based on the Kaggle index and prior documentation, it is an unstructured corpus of PDFs organized by year.

## 2. Which fields are useful for NyayaVarta
Given that this is unstructured PDF data, the raw files themselves do not contain structured database fields. Instead, the raw text inside the PDFs is the core asset. Useful extracted information will include:
- Case Title
- Date of Judgment
- Text of Judgment (facts, issues, law, precedent, decision)

## 3. Which fields are missing
Because it lacks structured JSON/CSV metadata out of the box, we are missing:
- Pre-extracted sections/provisions
- Pre-extracted citations
- Explicit graph relationships (who cites whom)
- Separated arguments vs. decisions

## 4. What preprocessing will be required
To make this dataset viable for Milestone 2 and beyond, we will need:
- An OCR / PDF text extraction pipeline (e.g., PyMuPDF)
- A Legal NER model to extract structured metadata (judges, dates, citations)
- Legal-structure-aware segmentation to chunk the text appropriately for RAG.

## 5. Potential duplication risks
Multiple sources on Kaggle and Indian Kanoon overlap. The exact same judgment might be uploaded multiple times under different names or appeals. We will need a deduplication mechanism using canonical IDs, content hashing, and date/title matching.

## 6. Canonical source or bootstrap?
Due to the unstructured nature (PDFs) and reliance on Kaggle, this dataset should serve as a **bootstrap / cross-check** source. For production, AWS Registry of Open Data (which provides JSON/Parquet metadata) is preferred as the canonical source.

## 7. Additional Indian legal sources needed
To fulfill the requirements, we still need:
- The AWS High Courts corpus for broader coverage.
- Indian Statutes/Acts as a canonical rule grounding dataset to prevent LLM hallucination of laws.
- Specialized NER/Graph extraction datasets to train or evaluate the extraction pipeline.
