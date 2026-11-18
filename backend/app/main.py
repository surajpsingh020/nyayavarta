from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os

from app.config import get_settings
from app.routers import chat, upload, auth, history
from app.services.rag_pipeline import RAGPipeline
from app.services.auth_db import get_auth_db


# Global RAG pipeline instance
rag_pipeline: RAGPipeline | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize resources on startup, cleanup on shutdown."""
    global rag_pipeline
    settings = get_settings()

    # Create upload directory
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

    # Initialize RAG pipeline with knowledge base
    rag_pipeline = RAGPipeline(settings)
    rag_pipeline.initialize()

    # Initialize SQLite Auth & Chat Database
    get_auth_db()

    # Attach to app state for dependency injection
    app.state.rag_pipeline = rag_pipeline
    app.state.settings = settings

    yield

    # Cleanup
    rag_pipeline = None


app = FastAPI(
    title="Nyayavarta API",
    description="Multilingual Legal Assistant for Indian Citizens",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api", tags=["Auth"])
app.include_router(history.router, prefix="/api", tags=["History"])
app.include_router(chat.router, prefix="/api", tags=["Chat"])
app.include_router(upload.router, prefix="/api", tags=["Upload"])


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "nyayavarta-api"}
