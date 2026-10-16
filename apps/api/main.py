from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apps.api.config import settings
from apps.api.logging_config import setup_logging
from apps.api.routers.rag import router as rag_router

logger = setup_logging()

app = FastAPI(title=settings.PROJECT_NAME, version=settings.VERSION)

# Allowed local development client origins (Vite dev server, preview, and alternative local ports)
ALLOWED_DEV_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:4173",
]

# Enable CORS strictly for local development origins (credentials disabled as unnecessary)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_DEV_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(rag_router)

@app.get("/v1/health")
def health_check():
    return {"status": "ok", "environment": settings.ENVIRONMENT}
