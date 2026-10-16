# Architecture Decision Records (ADRs)

## 1. Monorepo Structure
* **Decision:** Use a monorepo containing `apps`, `services`, `data`, and `models`.
* **Rationale:** Easier orchestration of Python backend services and React frontend; simplifies integration testing and versioning.

## 2. FastAPI for Backend
* **Decision:** Use FastAPI for the core API gateway and services.
* **Rationale:** Native async support, automatic OpenAPI docs, and high performance suitable for I/O heavy retrieval tasks.

## 3. Local-First Retrieval
* **Decision:** Base architecture on SQLite FTS5 (BM25) and FAISS CPU (ANN) for retrieval.
* **Rationale:** Avoids expensive full-corpus scans; ensures freeware baseline runs on consumer hardware.

## 4. Unresolved Decisions
* Embedding model choice (starting with 384-dim, but pending V1 benchmark).
* Next.js vs standard React SPA for the frontend.
* Precise schema representation for Indian statutes in the Knowledge Graph.
