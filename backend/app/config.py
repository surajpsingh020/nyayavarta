import os
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # BHASHINI API keys
    BHASHINI_UDYAT_KEY: str = ""
    BHASHINI_INFERENCE_KEY: str = ""
    BHASHINI_PIPELINE_URL: str = "https://meity-auth.ulcacontrib.org/ulca/apis/v0/model/getModelsPipeline"
    BHASHINI_INFERENCE_URL: str = "https://dhruva-api.bhashini.gov.in/services/inference/pipeline"

    # Gemini API key
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.8-flash"

    # RAG settings
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 100
    TOP_K_RESULTS: int = 5
    BM25_WEIGHT: float = 0.4
    FAISS_WEIGHT: float = 0.6

    # Embedding model
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"

    # Neo4j Graph Database
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USERNAME: str = "neo4j"
    NEO4J_PASSWORD: str = "nyayavarta_secret"
    NEO4J_DATABASE: str = "neo4j"

    # Upload settings
    UPLOAD_DIR: str = "uploads"
    MAX_FILE_SIZE_MB: int = 20

    # CORS
    FRONTEND_URL: str = "http://localhost:3000"

    class Config:
        env_file = [
            ".env",
            "../.env",
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env"),
        ]
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
