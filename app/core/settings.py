from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "sqlite:///./app.db"

    llm_api_base_url: str | None = None
    llm_api_key: str | None = None
    llm_model: str | None = None

    llm_timeout_seconds: float = Field(
        default=30.0,
        gt=0,
        le=300,
    )

    llm_stream_include_usage: bool = False


@lru_cache
def get_settings() -> Settings:
    """Return one cached settings object per process."""

    return Settings()
