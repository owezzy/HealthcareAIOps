"""Composition root: builds the FastAPI app and wires adapters into use cases.

Run locally:  make api   (uvicorn aiops_api.app:create_app --factory --port 8000)
Env: see aiops_api/settings.py (AIOPS_DATABASE_URL, AIOPS_INTERNAL_TOKEN,
AIOPS_DAILY_LLM_BUDGET_USD). Schema: `make migrate` (Alembic).
"""

from fastapi import FastAPI, HTTPException, Request, status

from aiops_api.db import make_engine
from aiops_api.ingestion import http as ingestion_http
from aiops_api.ingestion.adapters.postgres import PostgresAlertStore
from aiops_api.ingestion.ports import AlertStore
from aiops_api.settings import Settings
from aiops_api.usage import http as usage_http
from aiops_api.usage.adapters.postgres import PostgresUsageRepository
from aiops_api.usage.ports import UsageRepository


def create_app(
    settings: Settings | None = None,
    usage_repo: UsageRepository | None = None,
    alert_store: AlertStore | None = None,
) -> FastAPI:
    settings = settings or Settings.from_env()
    app = FastAPI(title="Healthcare AIOps API", version="0.1.0")
    app.state.settings = settings
    # One engine (connection pool) shared by every Postgres adapter.
    engine = None if usage_repo and alert_store else make_engine(settings.database_url)
    app.state.usage_repo = usage_repo or PostgresUsageRepository(engine)
    app.state.alert_store = alert_store or PostgresAlertStore(engine)

    @app.get("/health", tags=["platform"])
    def health() -> dict[str, str]:
        """Liveness: the process is up."""
        return {"status": "ok"}

    @app.get("/ready", tags=["platform"])
    def ready(request: Request) -> dict[str, str]:
        """Readiness: the database is reachable."""
        try:
            request.app.state.usage_repo.ping()
        except Exception as error:
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE, "database unavailable"
            ) from error
        return {"status": "ready"}

    app.include_router(usage_http.router)
    app.include_router(ingestion_http.router)
    return app
