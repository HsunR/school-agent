"""Application settings using pydantic-settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    deepseek_api_key: str = ""  # DEEPSEEK_API_KEY env var
    llm_model: str = "deepseek-chat"  # LLM_MODEL env var
    llm_base_url: str = "https://api.deepseek.com/v1"  # LLM_BASE_URL env var
    max_input_length: int = 1000  # MAX_INPUT_LENGTH env var
    llm_timeout: int = 30  # LLM_TIMEOUT env var
    app_name: str = "School Agent Backend"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    """Return a cached singleton Settings instance."""
    return Settings()
