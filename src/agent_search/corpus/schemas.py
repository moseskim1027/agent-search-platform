"""Versioned data contracts for the synthetic retrieval corpus."""

from datetime import date
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

SCHEMA_VERSION = "1.0"


class Domain(StrEnum):
    """Domains represented by the initial synthetic corpus."""

    FINANCE = "finance"
    NEWS = "news"


class CorpusDocument(BaseModel):
    """A document that can be indexed by lexical and vector retrieval systems."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    document_id: str = Field(pattern=r"^(finance|news)-[a-z0-9-]+$")
    domain: Domain
    language: str = Field(pattern=r"^[a-z]{2}$")
    title: str = Field(min_length=1)
    body: str = Field(min_length=1)
    published_at: date
    source_url: HttpUrl
    metadata: dict[str, str] = Field(default_factory=dict)


class SearchQuery(BaseModel):
    """A versioned search query used by the offline evaluation harness."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    query_id: str = Field(pattern=r"^q-[a-z0-9-]+$")
    query: str = Field(min_length=1)
    language: str = Field(pattern=r"^[a-z]{2}$")
    domain: Domain | None = None


class RelevanceJudgment(BaseModel):
    """A graded query-document relevance label for deterministic offline metrics."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    query_id: str = Field(pattern=r"^q-[a-z0-9-]+$")
    document_id: str = Field(pattern=r"^(finance|news)-[a-z0-9-]+$")
    relevance: int = Field(ge=0, le=3)

    @field_validator("relevance")
    @classmethod
    def relevance_is_nonzero(cls, value: int) -> int:
        """Keep qrels concise by omitting unjudged or irrelevant pairs."""

        if value == 0:
            raise ValueError("relevance judgments must be greater than zero")
        return value

