from fastapi import FastAPI
from apps.api.config import settings
from apps.api.logging_config import setup_logging
from apps.api.routers.rag import router as rag_router

logger = setup_logging()

app = FastAPI(title=settings.PROJECT_NAME, version=settings.VERSION)

app.include_router(rag_router)

@app.get("/v1/health")
def health_check():
    return {"status": "ok", "environment": settings.ENVIRONMENT}
