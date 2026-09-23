"""OpenSearch k-NN retrieval adapter with a stable agent-evidence contract."""

from collections.abc import Sequence
from typing import Any, Protocol

from agent_search.corpus.schemas import SearchFilters, SearchResult


class OpenSearchUnavailableError(RuntimeError):
    """Raised when an OpenSearch request cannot safely produce a result."""


class OpenSearchClient(Protocol):
    """Small client surface that makes query generation independently testable."""

    def search(self, *, index: str, body: dict[str, object], request_timeout: float) -> Any: ...


class OpenSearchVectorSearchAdapter:
    """Translate the repository-neutral search contract into OpenSearch k-NN DSL."""

    def __init__(
        self,
        client: OpenSearchClient,
        *,
        index: str,
        vector_field: str = "embedding",
        request_timeout_seconds: float = 3.0,
    ) -> None:
        self.client = client
        self.index = index
        self.vector_field = vector_field
        self.request_timeout_seconds = request_timeout_seconds

    def search(
        self,
        query_embedding: Sequence[float],
        filters: SearchFilters,
        *,
        limit: int,
    ) -> list[SearchResult]:
        """Run filtered approximate k-NN and return only grounded source evidence."""

        if limit < 1:
            return []
        if not query_embedding:
            raise ValueError("query_embedding must not be empty")
        try:
            response = self.client.search(
                index=self.index,
                body=self.query_body(query_embedding, filters, limit=limit),
                request_timeout=self.request_timeout_seconds,
            )
        except Exception as error:  # client implementations expose several transport exceptions
            raise OpenSearchUnavailableError("OpenSearch vector retrieval failed") from error
        try:
            hits = response["hits"]["hits"]
            return [self._result(rank, hit) for rank, hit in enumerate(hits, start=1)]
        except (KeyError, TypeError, ValueError) as error:
            message = "OpenSearch returned an invalid search response"
            raise OpenSearchUnavailableError(message) from error

    def query_body(
        self,
        query_embedding: Sequence[float],
        filters: SearchFilters,
        *,
        limit: int,
    ) -> dict[str, object]:
        """Build an efficient-filtering Lucene HNSW k-NN request."""

        vector_query: dict[str, object] = {"vector": list(query_embedding), "k": limit}
        clauses = self._filter_clauses(filters)
        if clauses:
            vector_query["filter"] = {"bool": {"filter": clauses}}
        return {
            "size": limit,
            "track_total_hits": False,
            "_source": {"excludes": [self.vector_field]},
            "query": {"knn": {self.vector_field: vector_query}},
        }

    @staticmethod
    def _filter_clauses(filters: SearchFilters) -> list[dict[str, object]]:
        clauses: list[dict[str, object]] = []
        for field, value in (
            ("domain", filters.domain),
            ("language", filters.language),
            ("metadata.region", filters.region),
            ("metadata.category", filters.category),
            ("metadata.tags", filters.tag),
        ):
            if value is not None:
                clauses.append({"term": {field: value.value if hasattr(value, "value") else value}})
        if filters.published_from or filters.published_to:
            bounds: dict[str, str] = {}
            if filters.published_from:
                bounds["gte"] = filters.published_from.isoformat()
            if filters.published_to:
                bounds["lte"] = filters.published_to.isoformat()
            clauses.append({"range": {"published_at": bounds}})
        if filters.geographic_radius:
            radius = filters.geographic_radius
            clauses.append(
                {
                    "geo_distance": {
                        "distance": f"{radius.radius_meters}m",
                        "metadata.geo": {"lat": radius.latitude, "lon": radius.longitude},
                    }
                }
            )
        return clauses

    @staticmethod
    def _result(rank: int, hit: dict[str, Any]) -> SearchResult:
        source = hit["_source"]
        fields = SearchResult.model_fields
        evidence = {
            name: source[name]
            for name, field in fields.items()
            if name not in {"rank", "score"} and field.is_required()
        }
        evidence.update(
            {name: source[name] for name in fields if name in source and name not in evidence}
        )
        evidence["rank"] = rank
        evidence["score"] = float(hit["_score"])
        return SearchResult.model_validate(evidence)
