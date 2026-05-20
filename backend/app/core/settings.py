"""Application settings using pydantic-settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    # ── Chat Node ──
    llm_chat_model: str = "deepseek-chat"
    llm_chat_base_url: str = "https://api.deepseek.com/v1"
    llm_chat_api_key: str = ""

    # ── Routing Node ──
    llm_routing_model: str = "deepseek-chat"
    llm_routing_base_url: str = "https://api.deepseek.com/v1"
    llm_routing_api_key: str = ""

    # ── Embedding (RAG, unified) ──
    llm_embedding_model: str = "text-embedding-ada-002"
    llm_embedding_base_url: str = "https://api.deepseek.com/v1"
    llm_embedding_api_key: str = ""

    # ── Generic LLM (backward compat for existing ChatService) ──
    llm_model: str = "deepseek-chat"
    llm_base_url: str = "https://api.deepseek.com/v1"
    deepseek_api_key: str = ""

    # ── ChromaDB ──
    chroma_persist_dir: str = "./chroma_db"
    rag_top_k_manual: int = 5  # student_manual
    rag_top_k_forum: int = 5   # school_forum

    # ── Other ──
    max_input_length: int = 1000
    llm_timeout: int = 30
    app_name: str = "School Agent Backend"

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


@lru_cache
def get_settings() -> Settings:
    """Return a cached singleton Settings instance."""
    return Settings()
