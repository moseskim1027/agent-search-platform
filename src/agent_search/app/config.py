"""Application configuration."""

from functools import lru_cache
from typing import Literal

from pydantic import SecretStr, model_validator
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
    search_cache_max_entries: int = 1_000
    search_backend: Literal["local", "opensearch"] = "local"
    opensearch_url: str | None = None
    opensearch_username: str | None = None
    opensearch_password: SecretStr | None = None
    opensearch_index: str = "agent-search-chunks-v1"
    opensearch_index_version: str = "opensearch-chunks-v1"
    opensearch_vector_field: str = "embedding"
    opensearch_request_timeout_seconds: float = 3.0
    opensearch_verify_certs: bool = True

    @model_validator(mode="after")
    def opensearch_settings_are_complete(self) -> "Settings":
        """Reject incomplete remote-search configuration at process startup."""

        if self.search_backend == "opensearch" and not self.opensearch_url:
            raise ValueError("OPENSEARCH_URL is required when SEARCH_BACKEND=opensearch")
        if self.opensearch_password and not self.opensearch_username:
            raise ValueError("OPENSEARCH_USERNAME is required when OPENSEARCH_PASSWORD is set")
        return self

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    """Return a cached settings instance for the running process."""

    return Settings()
