from agent_search.corpus.schemas import SearchFilters
from agent_search.retrieval.opensearch import OpenSearchVectorSearchAdapter


class RecordingClient:
    def __init__(self) -> None:
        self.request: dict[str, object] | None = None

    def search(
        self, *, index: str, body: dict[str, object], request_timeout: float
    ) -> dict[str, object]:
        self.request = {"index": index, "body": body, "request_timeout": request_timeout}
        return {
            "hits": {
                "hits": [
                    {
                        "_score": 0.91,
                        "_source": {
                            "schema_version": "1.0",
                            "chunk_id": "news-busan-port-weather-delay-chunk-000",
                            "file_id": "news-busan-port-weather-delay",
                            "domain": "news",
                            "language": "en",
                            "source_title": "Synthetic weather delay",
                            "source_url": "https://example.invalid/news/busan-port-weather-delay",
                            "text": "Synthetic grounded evidence.",
                            "content_sha256": "a" * 64,
                            "sequence": 0,
                            "character_start": 0,
                            "character_end": 28,
                            "metadata": {
                                "region": "busan",
                                "tags": ["cargo"],
                                "category": "weather",
                            },
                            "embedding": [0.1, 0.2],
                        },
                    }
                ]
            }
        }


def test_opensearch_adapter_builds_filtered_knn_and_returns_evidence() -> None:
    client = RecordingClient()
    adapter = OpenSearchVectorSearchAdapter(client, index="agent-search-chunks-v1")

    results = adapter.search([0.2, 0.8], SearchFilters(domain="news", region="busan"), limit=3)

    assert results[0].chunk_id == "news-busan-port-weather-delay-chunk-000"
    assert results[0].rank == 1
    assert results[0].score == 0.91
    assert client.request is not None
    body = client.request["body"]
    assert body["_source"] == {"excludes": ["embedding"]}  # type: ignore[index]
    vector_query = body["query"]["knn"]["embedding"]  # type: ignore[index]
    assert vector_query["filter"]["bool"]["filter"] == [  # type: ignore[index]
        {"term": {"domain": "news"}},
        {"term": {"metadata.region": "busan"}},
    ]
