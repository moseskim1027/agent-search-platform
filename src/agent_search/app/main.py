"""FastAPI entrypoint for the Agent Search Platform."""

from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from pydantic import BaseModel

from agent_search.app.config import get_settings
from agent_search.app.observability import SearchMetrics, log_search, query_hash
from agent_search.corpus.generator import build_source_files
from agent_search.corpus.partitioning import partition_source_files
from agent_search.corpus.schemas import SearchRequest, SearchResponse
from agent_search.retrieval.lexical import LocalBM25Retriever

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Grounded multi-domain search APIs for AI agents.",
)
retriever = LocalBM25Retriever(partition_source_files(build_source_files()))
metrics = SearchMetrics()
cache: dict[str, SearchResponse] = {}


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
    """Return ranked source evidence from the deterministic local BM25 baseline."""

    correlation_id = http_request.headers.get("x-correlation-id", str(uuid4()))
    cache_key = (
        f"{request.query.strip().lower()}:{request.filters.model_dump_json()}:{request.limit}"
    )
    cached = cache.get(cache_key)
    if cached:
        metrics.record(status="ok", result_count=len(cached.results), cache_hit=True)
        return cached
    started = perf_counter()
    response = SearchResponse(
        query=request.query,
        results=retriever.search(request.query, request.filters, limit=request.limit),
        ranking_version=settings.ranking_version,
    )
    cache[cache_key] = response
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
