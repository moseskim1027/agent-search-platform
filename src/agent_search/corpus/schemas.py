"""Versioned contracts for source-file ingestion, future chunks, and evaluation."""

from datetime import date
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

SCHEMA_VERSION = "1.0"


class Domain(StrEnum):
    """Source domains represented by the initial corpus."""

    LOCATION = "location"
    NEWS = "news"


class GeoPoint(BaseModel):
    """GeoJSON-compatible longitude/latitude point for Atlas geospatial filtering."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["Point"] = "Point"
    coordinates: tuple[float, float]

    @field_validator("coordinates")
    @classmethod
    def coordinates_are_valid(cls, value: tuple[float, float]) -> tuple[float, float]:
        """Require valid GeoJSON longitude then latitude coordinates."""

        longitude, latitude = value
        if not -180 <= longitude <= 180 or not -90 <= latitude <= 90:
            raise ValueError("coordinates must contain valid longitude and latitude")
        return value


class SearchMetadata(BaseModel):
    """Filterable metadata copied from a source file to each future chunk."""

    model_config = ConfigDict(extra="forbid")

    region: str = Field(min_length=1)
    tags: list[str] = Field(min_length=1)
    category: str | None = None
    geo: GeoPoint | None = None


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
    metadata: SearchMetadata


class ChunkRecord(BaseModel):
    """Atlas-ready partition derived from a source file."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    chunk_id: str = Field(pattern=r"^(location|news)-[a-z0-9-]+-chunk-[0-9]{3}$")
    file_id: str = Field(pattern=r"^(location|news)-[a-z0-9-]+$")
    domain: Domain
    language: str = Field(pattern=r"^[a-z]{2}$")
    source_title: str = Field(min_length=1)
    source_url: HttpUrl
    text: str = Field(min_length=1)
    content_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    sequence: int = Field(ge=0)
    character_start: int = Field(ge=0)
    character_end: int = Field(ge=1)
    published_at: date | None = None
    metadata: SearchMetadata
    embedding: list[float] | None = None
    embedding_model: str | None = None
    embedding_version: str | None = None
    embedding_content_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")


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


class GeographicRadius(BaseModel):
    """A location filter expressed as a GeoJSON point plus a radius in meters."""

    model_config = ConfigDict(extra="forbid")

    longitude: float = Field(ge=-180, le=180)
    latitude: float = Field(ge=-90, le=90)
    radius_meters: float = Field(gt=0, le=100_000)


class SearchFilters(BaseModel):
    """Optional metadata constraints shared by local and Atlas lexical retrieval."""

    model_config = ConfigDict(extra="forbid")

    domain: Domain | None = None
    language: str | None = Field(default=None, pattern=r"^[a-z]{2}$")
    region: str | None = None
    tag: str | None = None
    category: str | None = None
    published_from: date | None = None
    published_to: date | None = None
    geographic_radius: GeographicRadius | None = None


class SearchResult(BaseModel):
    """Repository-neutral grounded lexical retrieval result."""

    model_config = ConfigDict(extra="forbid")

    chunk_id: str
    file_id: str
    rank: int = Field(ge=1)
    score: float
    text: str
    character_start: int = Field(ge=0)
    character_end: int = Field(ge=1)
    source_title: str
    source_url: HttpUrl
    domain: Domain
    language: str
    published_at: date | None = None
    metadata: SearchMetadata


class SearchRequest(BaseModel):
    """Versioned HTTP search request for grounded lexical retrieval."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    query: str = Field(min_length=1, max_length=500)
    filters: SearchFilters = Field(default_factory=SearchFilters)
    limit: int = Field(default=10, ge=1, le=50)

    @field_validator("filters")
    @classmethod
    def date_range_is_valid(cls, filters: SearchFilters) -> SearchFilters:
        """Reject date filters whose end precedes their start."""

        if (
            filters.published_from
            and filters.published_to
            and filters.published_from > filters.published_to
        ):
            raise ValueError("published_to must be on or after published_from")
        return filters


class SearchResponse(BaseModel):
    """Versioned grounded search response containing evidence-only results."""

    schema_version: str = SCHEMA_VERSION
    query: str
    results: list[SearchResult]
