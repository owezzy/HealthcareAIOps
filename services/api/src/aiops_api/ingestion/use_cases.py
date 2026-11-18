from aiops_api.ingestion.domain import Alert, IngestOutcome
from aiops_api.ingestion.ports import AlertStore


def ingest_alerts(store: AlertStore, alerts: list[Alert]) -> IngestOutcome:
    """Record a batch of alerts; replays change nothing (Alertmanager retries on failure)."""
    return store.record(alerts)
