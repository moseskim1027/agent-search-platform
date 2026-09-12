from datetime import date

import pytest
from pydantic import ValidationError

from agent_search.corpus.schemas import (
    ChunkRecord,
    Domain,
    GeoPoint,
    RelevanceJudgment,
    SearchMetadata,
    SearchQuery,
    SourceFile,
)


def test_source_file_preserves_raw_content_and_provenance() -> None:
    source_file = SourceFile(
        file_id="news-transit-update",
        domain=Domain.NEWS,
        language="en",
        title="Transit update",
        source_url="https://synthetic.example/news/transit-update",
        source_path="news/transit-update.md",
        raw_text='+++\ntitle = "Transit update"\n+++\n\nA synthetic update.',
        body="A synthetic update.",
        content_sha256="a" * 64,
        published_at=date(2026, 1, 1),
        metadata=SearchMetadata(region="seoul", tags=["transport"]),
    )

    assert source_file.schema_version == "1.0"
    assert source_file.metadata.region == "seoul"


def test_chunk_record_copies_filterable_source_metadata() -> None:
    chunk = ChunkRecord(
        chunk_id="location-central-station-chunk-000",
        file_id="location-central-station",
        domain=Domain.LOCATION,
        language="en",
        source_title="Central Station",
        source_url="https://synthetic.example/locations/central-station",
        text="Step-free transfer between the Blue and Green lines.",
        content_sha256="b" * 64,
        sequence=0,
        character_start=0,
        character_end=52,
        metadata=SearchMetadata(
            region="seoul",
            tags=["blue-line", "accessible"],
            geo=GeoPoint(coordinates=(126.9779, 37.5652)),
        ),
    )

    assert chunk.metadata.geo.type == "Point"


def test_query_allows_an_optional_domain_filter() -> None:
    query = SearchQuery(query_id="q-transit", query="rail service update", language="en")

    assert query.domain is None


def test_judgment_rejects_zero_relevance() -> None:
    with pytest.raises(ValidationError, match="greater than zero"):
        RelevanceJudgment(query_id="q-transit", file_id="news-transit-update", relevance=0)
