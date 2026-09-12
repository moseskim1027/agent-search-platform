"""FastAPI entrypoint for the Agent Search Platform."""

from fastapi import FastAPI
from pydantic import BaseModel

from agent_search.app.config import get_settings
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


@app.post("/v1/search", response_model=SearchResponse, tags=["search"])
def search(request: SearchRequest) -> SearchResponse:
    """Return ranked source evidence from the deterministic local BM25 baseline."""

    return SearchResponse(
        query=request.query,
        results=retriever.search(request.query, request.filters, limit=request.limit),
    )
