from agent_search.corpus.generator import build_judgments, build_queries, build_source_files
from agent_search.corpus.partitioning import partition_source_files
from agent_search.corpus.schemas import Domain, GeographicRadius, SearchFilters
from agent_search.retrieval.lexical import AtlasSearchAdapter, LocalBM25Retriever


def make_retriever() -> LocalBM25Retriever:
    return LocalBM25Retriever(partition_source_files(build_source_files()))


def test_bm25_returns_evidence_for_current_file_level_judgments() -> None:
    retriever = make_retriever()
    judgments = build_judgments()
    judged_file_ids = {judgment.file_id for judgment in judgments}

    for query in build_queries():
        results = retriever.search(query.query, SearchFilters(domain=query.domain), limit=10)
        assert results
        assert any(result.file_id in judged_file_ids for result in results)
        assert all(result.text and result.source_title and result.source_url for result in results)


def test_bm25_applies_metadata_date_and_geographic_filters() -> None:
    results = make_retriever().search(
        "late night shuttle",
        SearchFilters(
            domain=Domain.LOCATION,
            language="en",
            region="seoul",
            tag="night-shuttle",
            category="shuttle-stop",
            geographic_radius=GeographicRadius(
                longitude=127.0674, latitude=37.5401, radius_meters=100
            ),
        ),
    )

    assert [result.file_id for result in results] == ["location-riverside-park"]
    assert make_retriever().search(
        "night", SearchFilters(published_from="2027-01-01")
    ) == []


def test_atlas_adapter_builds_text_and_filter_pipeline() -> None:
    pipeline = AtlasSearchAdapter().pipeline(
        "cargo terminal",
        SearchFilters(domain=Domain.LOCATION, region="busan"),
        limit=5,
    )

    search_stage = pipeline[0]["$search"]
    assert search_stage["index"] == "chunk_text_and_filters"
    assert pipeline[1] == {"$limit": 5}
