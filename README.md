# 🏛️ Nyayavarta (न्यायवार्ता)

**Multilingual Legal Assistant for Indian Citizens**

Nyayavarta is a localized legal assistant designed to help users in rural and underserved areas access legal aid, map old Indian laws to new laws (IPC → BNS, CrPC → BNSS, Evidence Act → BSA), and fill out legal applications.

Users can interact via **text or voice** in any of the **22 scheduled Indian languages**. The system translates input, performs hybrid RAG search over a legal knowledge base, generates profile-tailored responses with citations, and returns results in the user's language — with audio output.

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 14, TypeScript, Tailwind CSS, Lucide React |
| Backend | FastAPI, Pydantic, Uvicorn |
| AI/Translation | BHASHINI API (NMT, TTS, ASR, TLD), Google Gemini |
| Retrieval | FAISS (dense), BM25 (sparse), LangChain |
| Document Parsing | PyMuPDF, python-docx |
| Deployment | Docker, docker-compose |

## Quick Start

### Prerequisites
- Python 3.12+
- Node.js 20+
- Docker & Docker Compose (for containerized deployment)

### 1. Clone & Configure
```bash
cp .env.example .env
# Edit .env with your API keys
```

### 2. Backend (Development)
```bash
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend (Development)
```bash
cd frontend
npm install
npm run dev
```

### 4. Docker (Production)
```bash
docker-compose up --build
```

Frontend: http://localhost:3000  
Backend API: http://localhost:8000  
API Docs: http://localhost:8000/docs

## Project Structure

```
nyayavarta/
├── .env.example
├── docker-compose.yml
├── README.md
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx
│   │   │   └── globals.css
│   │   ├── components/
│   │   └── lib/
│   │       └── api.ts
│   └── public/
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── routers/
│   │   │   ├── chat.py
│   │   │   └── upload.py
│   │   ├── services/
│   │   │   ├── bhashini_utils.py
│   │   │   ├── rag_pipeline.py
│   │   │   └── llm_service.py
│   │   ├── models/
│   │   │   └── schemas.py
│   │   └── data/
│   │       └── knowledge_base.json
│   └── tests/
```

## Phases

- [x] **Phase 1**: Setup & Scaffolding
- [x] **Phase 2**: Backend APIs & Ingestion
- [x] **Phase 3**: Core Logic & LLM Orchestration
- [x] **Phase 4**: Frontend Implementation
- [ ] **Phase 5**: Dockerization & Testing

## License

MIT
