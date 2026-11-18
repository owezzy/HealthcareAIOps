from typing import Annotated

from fastapi import APIRouter, Depends, Request

from aiops_api.auth import require_service_token
from aiops_api.ingestion import use_cases
from aiops_api.ingestion.alertmanager import Webhook
from aiops_api.ingestion.ports import AlertStore

router = APIRouter()


def _store(request: Request) -> AlertStore:
    return request.app.state.alert_store


@router.post("/internal/alerts", tags=["internal"], dependencies=[Depends(require_service_token)])
def receive_alerts(
    webhook: Webhook, store: Annotated[AlertStore, Depends(_store)]
) -> dict[str, int]:
    """Alertmanager webhook (version 4). Idempotent: replays store nothing new."""
    outcome = use_cases.ingest_alerts(store, [a.to_alert() for a in webhook.alerts])
    return {"stored": outcome.stored, "updated": outcome.updated, "unchanged": outcome.unchanged}
