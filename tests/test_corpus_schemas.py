from datetime import date

import pytest
from pydantic import ValidationError

from agent_search.corpus.schemas import CorpusDocument, Domain, RelevanceJudgment, SearchQuery


def test_document_accepts_a_versioned_synthetic_source() -> None:
    document = CorpusDocument(
        document_id="news-transit-update",
        domain=Domain.NEWS,
        language="en",
        title="Transit update",
        body="A synthetic update about a rail service.",
        published_at=date(2026, 1, 1),
        source_url="https://synthetic.example/news-transit-update",
    )

    assert document.schema_version == "1.0"
    assert str(document.source_url) == "https://synthetic.example/news-transit-update"


def test_query_allows_an_optional_domain_filter() -> None:
    query = SearchQuery(query_id="q-transit", query="rail service update", language="en")

    assert query.domain is None


def test_judgment_rejects_zero_relevance() -> None:
    with pytest.raises(ValidationError, match="greater than zero"):
        RelevanceJudgment(query_id="q-transit", document_id="news-transit-update", relevance=0)
