"""Application configuration."""

from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings read from environment variables or a local .env file."""

    app_name: str = "Agent Search Platform"
    app_version: str = "0.1.0"
    app_env: str = "development"
    log_level: str = "INFO"
    mongodb_uri: str | None = None
    mongodb_database: str = "agent_search"
    mongodb_source_files_collection: str = "source_files"
    mongodb_chunks_collection: str = "chunks"
    gemini_api_key: SecretStr | None = None
    embedding_model: str = "gemini-embedding-2"
    embedding_dimensions: int = 768
    embedding_version: str = "gemini-embedding-2-768-l2-v1"
    embedding_normalization: str = "l2"
    rrf_k: int = 60
    ranking_version: str = "lexical-bm25-v1"
    search_cache_ttl_seconds: int = 60

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    """Return a cached settings instance for the running process."""

    return Settings()
