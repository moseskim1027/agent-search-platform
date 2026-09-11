from datetime import date

import pytest
from pydantic import ValidationError

from agent_search.corpus.schemas import Domain, RelevanceJudgment, SearchQuery, SourceFile


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
        metadata={"region": "seoul", "topics": ["transport"]},
    )

    assert source_file.schema_version == "1.0"
    assert source_file.metadata["region"] == "seoul"


def test_query_allows_an_optional_domain_filter() -> None:
    query = SearchQuery(query_id="q-transit", query="rail service update", language="en")

    assert query.domain is None


def test_judgment_rejects_zero_relevance() -> None:
    with pytest.raises(ValidationError, match="greater than zero"):
        RelevanceJudgment(query_id="q-transit", file_id="news-transit-update", relevance=0)
