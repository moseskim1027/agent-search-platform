"""FastAPI entrypoint for the Agent Search Platform."""

from fastapi import FastAPI
from pydantic import BaseModel

from agent_search.app.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Grounded multi-domain search APIs for AI agents.",
)


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

