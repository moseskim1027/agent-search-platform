"""FastAPI entrypoint for the Agent Search Platform."""

from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from pydantic import BaseModel

from agent_search.app.cache import TTLCache
from agent_search.app.config import get_settings
from agent_search.app.observability import SearchMetrics, log_search, query_hash
from agent_search.corpus.generator import build_source_files
from agent_search.corpus.partitioning import partition_source_files
from agent_search.corpus.schemas import SearchRequest, SearchResponse
from agent_search.retrieval.lexical import LocalBM25Retriever
from agent_search.retrieval.opensearch import (
    OpenSearchUnavailableError,
    OpenSearchVectorSearchAdapter,
)

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Grounded multi-domain search APIs for AI agents.",
)
retriever = LocalBM25Retriever(partition_source_files(build_source_files()))
metrics = SearchMetrics()
cache = TTLCache[SearchResponse](
    ttl_seconds=settings.search_cache_ttl_seconds,
    max_entries=settings.search_cache_max_entries,
)


def _opensearch_retriever() -> OpenSearchVectorSearchAdapter:
    """Create the remote adapter lazily so local development needs no cluster."""

    if not settings.opensearch_url:
        raise OpenSearchUnavailableError("OPENSEARCH_URL is not configured")
    try:
        from opensearchpy import OpenSearch

        client = OpenSearch(
            hosts=[settings.opensearch_url],
            http_auth=(
                (settings.opensearch_username, settings.opensearch_password.get_secret_value())
                if settings.opensearch_username and settings.opensearch_password
                else None
            ),
            use_ssl=settings.opensearch_url.startswith("https://"),
            verify_certs=settings.opensearch_verify_certs,
        )
        return OpenSearchVectorSearchAdapter(
            client,
            index=settings.opensearch_index,
            vector_field=settings.opensearch_vector_field,
            request_timeout_seconds=settings.opensearch_request_timeout_seconds,
        )
    except Exception as error:
        raise OpenSearchUnavailableError("OpenSearch client initialization failed") from error


class HealthResponse(BaseModel):
    """Minimal liveness response used by local and deployed health checks."""

    status: str
    environment: str
    version: str


@app.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    """Return the current service liveness state."""

    return HealthResponse(
        status="ok",
        environment=settings.app_env,
        version=settings.app_version,
    )


@app.get("/metrics", include_in_schema=False)
def prometheus_metrics() -> Response:
    """Expose small Prometheus-compatible counters without an extra dependency."""

    return Response(metrics.render(), media_type="text/plain; version=0.0.4")


@app.post("/v1/search", response_model=SearchResponse, tags=["search"])
def search(request: SearchRequest, http_request: Request) -> SearchResponse:
    """Return grounded evidence, using configured OpenSearch vector retrieval when available."""

    correlation_id = http_request.headers.get("x-correlation-id", str(uuid4()))
    cache_key = (
        f"{request.query.strip().lower()}:{request.filters.model_dump_json()}:{request.limit}"
    )
    cached = cache.get(cache_key)
    if cached is not None:
        metrics.record(status="ok", result_count=len(cached.results), cache_hit=True)
        return cached
    started = perf_counter()
    degraded = False
    degradation_reason = None
    ranking_version = settings.ranking_version
    if settings.search_backend == "opensearch":
        try:
            from agent_search.corpus.embeddings import GeminiEmbeddingProvider
            from agent_search.retrieval.semantic import EmbeddingSpec

            if settings.gemini_api_key is None:
                raise OpenSearchUnavailableError("GEMINI_API_KEY is not configured")
            spec = EmbeddingSpec(
                model=settings.embedding_model,
                dimensions=settings.embedding_dimensions,
                version=settings.embedding_version,
                normalization=settings.embedding_normalization,
            )
            query_embedding = GeminiEmbeddingProvider(
                settings.gemini_api_key.get_secret_value(), spec
            ).embed([request.query])[0]
            results = _opensearch_retriever().search(
                query_embedding, request.filters, limit=request.limit
            )
            ranking_version = settings.opensearch_index_version
        except (OpenSearchUnavailableError, OSError, ValueError, KeyError):
            results = retriever.search(request.query, request.filters, limit=request.limit)
            degraded = True
            degradation_reason = "opensearch_unavailable"
    else:
        results = retriever.search(request.query, request.filters, limit=request.limit)
    response = SearchResponse(
        query=request.query,
        results=results,
        ranking_version=ranking_version,
        degraded=degraded,
        degradation_reason=degradation_reason,
    )
    cache.put(cache_key, response)
    elapsed_ms = (perf_counter() - started) * 1_000
    metrics.record(status="ok", result_count=len(response.results), cache_hit=False)
    log_search(
        correlation_id=correlation_id,
        query_hash=query_hash(request.query),
        filters=request.filters.model_dump(mode="json"),
        result_count=len(response.results),
        ranking_version=settings.ranking_version,
        latency_ms=round(elapsed_ms, 3),
    )
    return response
