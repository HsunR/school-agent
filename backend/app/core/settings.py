"""Application settings stubs."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings placeholder.

    Will be extended with configuration fields as needed.
    """

    app_name: str = "School Agent Backend"
    debug: bool = True

    class Config:
        env_file = ".env"


settings = Settings()
