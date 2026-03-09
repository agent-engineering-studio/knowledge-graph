"""Application settings using pydantic-settings."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Central configuration loaded from environment variables and .env file."""

    # Neo4j (Graph DB)
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "changeme"
    NEO4J_DATABASE: str = "neo4j"

    # Redis (Vector Store)
    REDIS_URL: str = "redis://localhost:6379"
    REDIS_INDEX_NAME: str = "kg_vectors"
    REDIS_VECTOR_DIM: int = 768

    # Ollama (Inference API locale)
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_LLM_MODEL: str = "llama3"
    # Dedicated model for entity/relation extraction during ingestion.
    # Smaller/faster models (e.g. qwen2.5:7b) work well here because the
    # task is structured JSON output guided by few-shot examples.
    # Falls back to OLLAMA_LLM_MODEL if not set.
    OLLAMA_EXTRACTION_MODEL: str = ""
    OLLAMA_EMBEDDING_MODEL: str = "nomic-embed-text"

    # App
    CHUNK_SIZE: int = 1024
    CHUNK_OVERLAP: int = 128
    MAX_RETRIES: int = 5
    LOG_LEVEL: str = "INFO"
    DEBUG: bool = False

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


settings = Settings()
