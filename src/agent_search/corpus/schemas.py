"""Versioned data contracts for source-file ingestion and retrieval evaluation."""

from datetime import date
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

SCHEMA_VERSION = "1.0"


class Domain(StrEnum):
    """Source domains represented by the initial corpus."""

    LOCATION = "location"
    NEWS = "news"


class SourceFile(BaseModel):
    """An ingested raw file before it is partitioned into search chunks."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    file_id: str = Field(pattern=r"^(location|news)-[a-z0-9-]+$")
    domain: Domain
    language: str = Field(pattern=r"^[a-z]{2}$")
    title: str = Field(min_length=1)
    source_url: HttpUrl
    source_path: str = Field(pattern=r"^(locations|news)/[a-z0-9-]+\.md$")
    raw_text: str = Field(min_length=1)
    body: str = Field(min_length=1)
    content_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    published_at: date | None = None
    metadata: dict[str, str | list[str]] = Field(default_factory=dict)


class SearchQuery(BaseModel):
    """A versioned search query used by the offline evaluation harness."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    query_id: str = Field(pattern=r"^q-[a-z0-9-]+$")
    query: str = Field(min_length=1)
    language: str = Field(pattern=r"^[a-z]{2}$")
    domain: Domain | None = None


class RelevanceJudgment(BaseModel):
    """A graded query-file relevance label for deterministic offline metrics."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    query_id: str = Field(pattern=r"^q-[a-z0-9-]+$")
    file_id: str = Field(pattern=r"^(location|news)-[a-z0-9-]+$")
    relevance: int = Field(ge=0, le=3)

    @field_validator("relevance")
    @classmethod
    def relevance_is_nonzero(cls, value: int) -> int:
        """Keep qrels concise by omitting unjudged or irrelevant pairs."""

        if value == 0:
            raise ValueError("relevance judgments must be greater than zero")
        return value
