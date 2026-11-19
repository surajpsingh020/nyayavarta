# Nyayavarta: Multilingual AI Legal Assistant & GraphRAG Platform

> **Empowering Indian Citizens with Accessible Legal Aid, Statutory Transition Intelligence, and Constitutional Safeguards under the Bharatiya Nyaya Sanhita (BNS, 2023) Framework.**

[![Status](https://img.shields.io/badge/Status-Production%20Ready-brightgreen.svg)]()
[![Backend](https://img.shields.io/badge/Backend-FastAPI%20%7C%20Python%203.12-blue.svg)]()
[![Frontend](https://img.shields.io/badge/Frontend-Next.js%2014%20%7C%20TypeScript%20%7C%20TailwindCSS-black.svg)]()
[![Graph Database](https://img.shields.io/badge/GraphDB-Neo4j%205.18-orange.svg)]()
[![Security Audit](https://img.shields.io/badge/Security%20Audit-25%2F25%20PASS%20(100%25)-success.svg)]()
[![RAGAS Eval](https://img.shields.io/badge/RAGAS%20Faithfulness-78.3%25-informational.svg)]()
[![Relevancy](https://img.shields.io/badge/Answer%20Relevancy-100%25-brightgreen.svg)]()

---

## 1. Project Overview

Nyayavarta is an enterprise-grade legal assistant designed to bridge India's digital and legal literacy gap. It empowers citizens, legal aid volunteers, students, and advocates to navigate the historic transition from colonial criminal codes (IPC 1860, CrPC 1973, IEA 1872) to the modern Indian criminal justice architecture:
* **Bharatiya Nyaya Sanhita (BNS, 2023)**
* **Bharatiya Nagarik Suraksha Sanhita (BNSS, 2023)**
* **Bharatiya Sakshya Adhiniyam (BSA, 2023)**

Through a **hybrid GraphRAG (Knowledge Graph + BM25)** engine, **multilingual speech recognition (BHASHINI / Web Speech)**, and **constitutional guardrails**, Nyayavarta provides instant, verifiable, and citizen-friendly legal guidance with direct routing to free legal aid under the Legal Services Authorities Act, 1987 (NALSA/DLSA Helpline: **15100**).

---

## 2. Core Subsystems & Architecture

```
                                  [ Indian Citizen / Advocate ]
                                                │
                                    (Voice / Text / Document)
                                                ▼
                                    ┌───────────────────────┐
                                    │   Next.js 14 Frontend │
                                    └───────────┬───────────┘
                                                │ (HTTPS / Bearer Auth)
                                                ▼
                                    ┌───────────────────────┐
                                    │    FastAPI Gateway    │
                                    └───────────┬───────────┘
                                                │
                 ┌──────────────────────────────┴──────────────────────────────┐
                 ▼                                                             ▼
     ┌────────────────────────┐                                   ┌────────────────────────┐
     │   Guardrails Engine    │                                   │   Auth & Thread DB     │
     │  • Prompt Injection    │                                   │  • PBKDF2 (600k rounds)│
     │  • Harmful Intent Block│                                   │  • Cross-User IDOR     │
     │  • Aadhaar / PAN DLP   │                                   │  • Session Invalidation│
     └───────────┬────────────┘                                   └────────────────────────┘
                 │ (Sanitized Query)
                 ▼
     ┌────────────────────────────────────────────────────────┐
     │           Hybrid GraphRAG Orchestration                │
     │  ┌─────────────────────────┐  ┌──────────────────────┐ │
     │  │ Neo4j Knowledge Graph   │  │ BM25 Sparse Search   │ │
     │  │ • 515 Nodes / 1,030 Rel │  │ • Statutory Corpus   │ │
     │  │ • 285 Sections          │  │ • Document Chunks   │ │
     │  │ • 40 Landmark Precedents│  │ • Headnotes & Ratios │ │
     │  └───────────┬─────────────┘  └──────────┬───────────┘ │
     └──────────────┼───────────────────────────┼─────────────┘
                    └─────────────┬─────────────┘
                                  │ (Context Injection)
                                  ▼
                     ┌────────────────────────┐
                     │   Gemini 3.5 LLM       │
                     │  • Citizen Plain Advice│
                     │  • Old <-> New Mappings│
                     │  • Procedural Steps    │
                     │  • NALSA 15100 Routing │
                     └────────────┬───────────┘
                                  │
                                  ▼
                     ┌────────────────────────┐
                     │ LLMOps Tracing & Evals │
                     │  • RAGAS Metrics       │
                     │  • LLM-as-a-Judge      │
                     │  • Millisecond Spans   │
                     └────────────────────────┘
```

---

## 3. Key Capabilities

### A. 105 Statutory Transitions & 38 Landmark Precedents
Nyayavarta features an interactive Law Transition Matrix with categorized search and modal dialogs:
* **BNS (Penal Transitions)**: Murder (IPC 302 -> BNS 103), Cheating (IPC 420 -> BNS 318(4)), Theft (IPC 379 -> BNS 303(2)), Hit-and-Run (BNS 106(2)), Mob Lynching (BNS 103(2)), Stalking & Sexual Harassment.
* **BNSS (Procedure & FIR)**: Zero FIR (BNSS 173(1)(ii)), Mandatory Preliminary Inquiry (BNSS 173(3)), Section 35 Arrest Notice (CrPC 41A), Default Bail (BNSS 187), Summary Trial limits.
* **BSA (Evidence & Records)**: Electronic Record Admissibility & Certificates (BSA Section 63 replacing IEA 65B), Digital forensics.
* **Special & Central Acts**: POCSO Act (2012), NDPS Act (1985), IT Act (2000), PMLA (2002), Negotiable Instruments Act (1881 - Section 138), Motor Vehicles Act (1988/2019), Prevention of Corruption Act (1988).
* **38 Landmark Supreme Court Rulings**: *D.K. Basu* (arrest rights), *Arnesh Kumar* (anti-harassment arrest safeguards), *Lalita Kumari* (mandatory FIR), *Shreya Singhal* (digital free speech), *Puttaswamy* (privacy), *Vijay Madanlal Choudhary* (PMLA bail thresholds), *Pranay Sethi* (MACT road accident compensation).

### B. Live Neo4j Knowledge Graph (515 Nodes, 1,030 Relationships)
* **Ontology Nodes**: `Section` (285), `Offence` (136), `CasePrecedent` (40), `DocumentChunk` (36), `Act` (15), `Court` (2), `LegalAid` (1).
* **Semantic Relationships**: `REPLACED_BY`, `REPLACES`, `COVERS_OFFENCE`, `BELONGS_TO`, `APPLIES_SECTION`, `OVERRULES`, `ROUTES_TO_AID`, `REFERENCES_SECTION`.
* **Sub-20ms Graph Traversal**: Direct Cypher queries linking citizen claims to statutory transitions with zero hallucinated section numbers.

### C. Enterprise Guardrails Engine & DLP Compliance
* **Prompt Injection & Jailbreak Defense**: Detects and neutralizes adversarial attacks (e.g., DAN mode, system prompt exfiltration).
* **Harmful Intent Defense**: Rejects queries soliciting assistance with criminal acts, document forgery, or corruption.
* **Data Leak Prevention (DLP)**: Masks Indian citizen credentials (12-digit Aadhaar, 10-character PAN, mobile numbers, payment cards) into sanitized tokens (`[AADHAAR_REDACTED]`) before retrieval and inference.

### D. Rigorous Security Hardening (25/25 Audit Pass)
* **Authentication**: Salted PBKDF2-HMAC-SHA256 (600,000 rounds) + 256-bit entropy session tokens.
* **Authorization & IDOR Defense**: Strict user isolation via database constraints (`WHERE id = ? AND user_id = ?`); unauthenticated access blocked with `401 Unauthorized`, cross-user access returns `404 Not Found`.
* **File Upload Hardening**: Whitelist restriction (`.pdf`, `.docx`, `.doc`, `.txt`), path traversal sanitization, and 20MB payload ceiling.
* **Telemetry Security**: Observability endpoints (`/api/llmops/*`) restricted behind authenticated sessions.

---

## 4. RAGAS & LLM-as-a-Judge Evaluation Benchmark

The system includes an automated evaluation harness ([backend/app/services/eval_engine.py](file:///c:/Users/Suraj%20Singh/Desktop/Repos/NyayaVarta/backend/app/services/eval_engine.py)) executing across a 12-case golden benchmark:

| Metric | Target | Score | Details |
| :--- | :---: | :---: | :--- |
| **Context Precision** | $\ge 80.0\%$ | **83.4%** | Accuracy of retrieved sections matching ground truth |
| **Context Recall** | $\ge 80.0\%$ | **83.4%** | Coverage of statutory provisions needed to answer |
| **Faithfulness** | $\ge 75.0\%$ | **78.3%** | Groundedness in retrieved context vs internal generation |
| **Answer Relevancy** | $\ge 90.0\%$ | **100.0%** | Direct alignment with citizen's legal inquiry |
| **Guardrails Accuracy** | $\ge 90.0\%$ | **91.7%** | Interception of injection, harmful intent, and PII masking |
| **Average Latency** | $< 25\text{s}$ | **~18.8s** | Complete turn including 2-pass LLM-as-a-Judge scoring |

---

## 5. Technology Stack

| Layer | Technologies |
| :--- | :--- |
| **Frontend UI** | Next.js 14 (App Router), TypeScript, Tailwind CSS, Lucide React, ReactMarkdown, Rehype-Raw |
| **Backend API** | FastAPI, Python 3.12, Pydantic v2, Uvicorn |
| **Graph Database** | Neo4j 5.18 Community Edition (Bolt Protocol, Cypher Engine, APOC) |
| **Hybrid Search** | BM25 Sparse Lexical Search + Neo4j Graph Traversal + LangChain |
| **AI & LLM** | Google Gemini (3.5 Flash Lite), BHASHINI ASR/NMT, Web Speech API |
| **Storage & Auth** | SQLite (Thread history & PBKDF2 credentials), Local JSONL Telemetry |
| **Containerization** | Docker, Docker Compose |

---

## 6. Quick Start & Local Setup

### Prerequisites
* [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Docker Compose v2+)
* Python 3.12+ and Node.js 20+ (for local host development)

### 1. Clone & Configure Environment
```bash
git clone https://github.com/surajpsingh020/nyayavarta.git
cd nyayavarta

# Copy sample configuration
cp .env.example .env
```
Edit `.env` and set your `GEMINI_API_KEY`:
```env
GEMINI_API_KEY=your_gemini_api_key_here
NEO4J_PASSWORD=nyayavarta_secret_2024
```

### 2. Launch Entire Stack via Docker Compose
```bash
docker compose up -d --build
```

Verify that all services are healthy:
```bash
docker compose ps
```

| Service | Port | Local Endpoint |
| :--- | :--- | :--- |
| **Frontend Web App** | `3000` | http://localhost:3000 |
| **Backend API** | `8000` | http://localhost:8000 |
| **Interactive API Docs** | `8000` | http://localhost:8000/docs |
| **Neo4j Browser** | `7474` | http://localhost:7474 *(User: neo4j, Pass: nyayavarta_secret_2024)* |

---

## 7. Running Verification & Evaluation Suites

### A. Run Complete 25/25 Endpoint Security Audit
```powershell
$env:PYTHONPATH="backend"
backend\venv\Scripts\python.exe backend\tests\security_audit_test.py
```

### B. Run RAGAS & LLM-as-a-Judge Evaluation Suite
```powershell
$env:PYTHONPATH="backend"
backend\venv\Scripts\python.exe backend\app\services\eval_engine.py
```

### C. Seed / Refresh Neo4j Knowledge Graph
```powershell
docker exec nyayavarta-backend python -m app.services.dataset_loader --all
```

---

## 8. API Endpoint Reference

| Method | Path | Authentication | Description |
| :--- | :--- | :---: | :--- |
| `GET` | `/health` | Public | System status and service health check |
| `GET` | `/api/matrix` | Public | Law transition catalog (105 transitions, 38 precedents) |
| `POST` | `/api/auth/register` | Public | Citizen account registration (PBKDF2 salted hash) |
| `POST` | `/api/auth/login` | Public | Session creation and bearer token generation |
| `GET` | `/api/auth/me` | Bearer Token | Authenticated citizen session validation |
| `POST` | `/api/auth/logout` | Bearer Token | Immediate session token revocation |
| `GET` | `/api/chat/threads` | Bearer Token | List user consultation history |
| `POST` | `/api/chat/threads` | Bearer Token | Create new user-isolated consultation thread |
| `GET` | `/api/chat/threads/{id}/messages`| Bearer Token | Retrieve thread messages (Protected against IDOR) |
| `DELETE`| `/api/chat/threads/{id}` | Bearer Token | Delete thread (Protected against cross-user deletion)|
| `POST` | `/api/chat` | Optional Token | Multilingual GraphRAG consultation with guardrails |
| `POST` | `/api/translate` | Public | On-demand text translation and speech synthesis |
| `POST` | `/api/upload` | Public | Sanitized legal document ingestion (.pdf, .docx, .txt) |
| `GET` | `/api/llmops/metrics` | Bearer Token | Aggregate telemetry, latencies, and redaction rates |
| `GET` | `/api/llmops/traces` | Bearer Token | Detailed consultation traces and execution spans |

---

## 9. Repository Structure

```
nyayavarta/
├── docker-compose.yml              # Container orchestration (Backend, Frontend, Neo4j)
├── .env.example                    # Sample environment variables
├── .gitignore                      # Clean repository ignore patterns
├── README.md                       # Comprehensive platform documentation
├── docs/
│   └── index.html                  # Official GitHub Pages presentation redirect
├── backend/
│   ├── Dockerfile                  # Production Python 3.12 container definition
│   ├── requirements.txt            # Production dependencies
│   ├── app/
│   │   ├── main.py                 # FastAPI application root & CORS lifespan
│   │   ├── config.py               # Pydantic environment settings
│   │   ├── models/schemas.py       # Pydantic request/response schemas
│   │   ├── routers/
│   │   │   ├── auth.py             # User registration, login, session tokens
│   │   │   ├── chat.py             # GraphRAG consultation, speech, LLMOps traces
│   │   │   ├── history.py          # User-isolated thread persistence
│   │   │   ├── matrix.py           # Law transition matrix data feed
│   │   │   └── upload.py           # Hardened document ingestion router
│   │   ├── services/
│   │   │   ├── auth_db.py          # SQLite PBKDF2 user & session management
│   │   │   ├── bhashini_utils.py   # Indian language detection & audio handling
│   │   │   ├── dataset_loader.py   # Neo4j automated ingestion of 38 precedents
│   │   │   ├── eval_engine.py      # RAGAS & LLM-as-a-Judge benchmark suite
│   │   │   ├── guardrails_service.py # Prompt injection, harmful intent, and DLP
│   │   │   ├── llm_service.py      # Gemini cascade, legal reasoning, LLM judge
│   │   │   ├── rag_pipeline.py     # Hybrid Neo4j traversal + BM25 search
│   │   │   └── tracing_service.py  # Structured telemetry & span tracking
│   │   └── data/
│   │       └── knowledge_base.json # 105 statutory transitions catalog
│   └── tests/
│       ├── security_audit_test.py  # 25-point comprehensive security test suite
│       └── verify_full_system.py   # End-to-end full stack validation
└── frontend/
    ├── Dockerfile                  # Next.js production build definition
    ├── package.json                # Dependencies (Next 14, React 18, Tailwind, Lucide)
    └── src/
        ├── app/                    # Next.js App Router (page.tsx, layout.tsx, route.ts)
        ├── components/
        │   ├── AudioPlayer.tsx     # Voice playback widget
        │   ├── AuthModal.tsx       # Secure citizen login/registration modal
        │   ├── ChatInterface.tsx   # Conversational legal consultation UI
        │   ├── CitationCard.tsx    # Statutory source & precedent citation card
        │   ├── DocumentUpload.tsx  # Drag-and-drop document upload interface
        │   ├── LanguageSelector.tsx# Multilingual language switcher
        │   └── LawMatrix.tsx       # Transition matrix & precedent detail modals
        └── lib/
            ├── api.ts              # API client with token authorization
            └── i18n.ts             # Multilingual localization dictionaries
```

---

## 10. License & Disclaimers

Nyayavarta is an artificial intelligence legal literacy assistant developed for educational, academic, and citizen guidance purposes. While grounded in the Bharatiya Nyaya Sanhita, Bharatiya Nagarik Suraksha Sanhita, and Bharatiya Sakshya Adhiniyam, it does not constitute formal legal representation. Citizens requiring legal representation are routed directly to the National Legal Services Authority (NALSA) toll-free helpline (**15100**).
