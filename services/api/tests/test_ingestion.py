"""Alertmanager webhook: authenticated, validated, idempotent, queues correlation."""

import copy
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text

from aiops_api.app import create_app
from aiops_api.db import make_engine
from aiops_api.ingestion.adapters.postgres import PostgresAlertStore, alerts
from aiops_api.queue import jobs
from aiops_api.settings import Settings

TOKEN = "svc-token"
AUTH = {"Authorization": f"Bearer {TOKEN}"}
URL = "postgresql+psycopg://test@localhost/unused"


def webhook(status: str = "firing", **alert_overrides) -> dict:
    """An Alertmanager v4 payload: S2's LIS alert."""
    alert = {
        "status": status,
        "labels": {
            "alertname": "LISHighErrorRate",
            "component": "lis",
            "severity": "high",
            "namespace": "aiops-estate",
        },
        "annotations": {"summary": "LIS 503 rate above 30%"},
        "startsAt": "2026-11-18T09:06:00Z",
        "endsAt": "0001-01-01T00:00:00Z" if status == "firing" else "2026-11-18T09:20:00Z",
        "generatorURL": "http://prometheus/graph",
        "fingerprint": "a1b2c3d4e5f60718",
        **alert_overrides,
    }
    return {
        "version": "4",
        "status": status,
        "receiver": "aiops",
        "groupKey": "{}:{}",
        "groupLabels": {},
        "commonLabels": {},
        "commonAnnotations": {},
        "externalURL": "http://alertmanager",
        "alerts": [alert],
    }


@pytest.fixture
def client(usage_repo, alert_store) -> TestClient:
    settings = Settings(database_url=URL, internal_token=TOKEN, daily_llm_budget_usd=5.0)
    return TestClient(create_app(settings, usage_repo, alert_store))


def test_webhook_needs_the_service_token(client, alert_store) -> None:
    assert client.post("/internal/alerts", json=webhook()).status_code == 401
    assert alert_store.alerts == {}


def test_replayed_webhook_stores_one_alert_and_one_job(client, alert_store) -> None:
    first = client.post("/internal/alerts", json=webhook(), headers=AUTH).json()
    replay = client.post("/internal/alerts", json=webhook(), headers=AUTH).json()
    assert first == {"stored": 1, "updated": 0, "unchanged": 0}
    assert replay == {"stored": 0, "updated": 0, "unchanged": 1}
    assert len(alert_store.jobs) == 1


def test_resolution_updates_the_same_alert(client, alert_store) -> None:
    client.post("/internal/alerts", json=webhook(), headers=AUTH)
    resolved = client.post("/internal/alerts", json=webhook("resolved"), headers=AUTH).json()
    assert resolved == {"stored": 0, "updated": 1, "unchanged": 0}
    [alert] = alert_store.alerts.values()
    assert alert.status == "resolved" and alert.ends_at is not None


def test_firing_alert_has_no_end_time(client, alert_store) -> None:
    client.post("/internal/alerts", json=webhook(), headers=AUTH)
    [alert] = alert_store.alerts.values()
    assert alert.ends_at is None  # Alertmanager's zero time means "still firing"
    assert (alert.component, alert.severity, alert.alertname) == ("lis", "high", "LISHighErrorRate")


@pytest.mark.parametrize(
    "mutate",
    [
        lambda p: p.update(version="3"),
        lambda p: p.update(alerts=[]),
        lambda p: p["alerts"][0]["labels"].pop("alertname"),
        lambda p: p["alerts"][0].update(startsAt="2026-11-18T09:06:00"),  # no time zone
        lambda p: p["alerts"][0].update(status="exploding"),
        lambda p: p["alerts"][0].pop("fingerprint"),
    ],
)
def test_invalid_payloads_are_rejected(client, alert_store, mutate) -> None:
    payload = copy.deepcopy(webhook())
    mutate(payload)
    assert client.post("/internal/alerts", json=payload, headers=AUTH).status_code == 422
    assert alert_store.alerts == {}


# --- real Postgres ----------------------------------------------------------------


@pytest.fixture
def pg_store(postgres_url) -> PostgresAlertStore:
    engine = make_engine(postgres_url)
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE alerts, jobs RESTART IDENTITY CASCADE"))
    return PostgresAlertStore(engine)


def _rows(store: PostgresAlertStore, table):
    with store._engine.connect() as connection:
        return connection.execute(select(table)).mappings().all()


def _alert(status: str = "firing"):
    from aiops_api.ingestion.alertmanager import Webhook

    return Webhook.model_validate(webhook(status)).alerts[0].to_alert()


def test_postgres_store_is_idempotent_and_queues_once(pg_store) -> None:
    assert pg_store.record([_alert()]).stored == 1
    assert pg_store.record([_alert()]).unchanged == 1
    assert len(_rows(pg_store, alerts)) == 1
    [job] = _rows(pg_store, jobs)
    assert (job["kind"], job["status"], job["attempts"]) == ("correlate", "pending", 0)
    assert job["payload"] == {"alert_id": _rows(pg_store, alerts)[0]["id"]}


def test_postgres_resolution_updates_in_place_and_queues_again(pg_store) -> None:
    pg_store.record([_alert()])
    assert pg_store.record([_alert("resolved")]).updated == 1
    [row] = _rows(pg_store, alerts)
    assert row["status"] == "resolved"
    assert row["ends_at"] == datetime(2026, 11, 18, 9, 20, tzinfo=UTC)
    assert [j["dedupe_key"].rsplit(":", 1)[1] for j in _rows(pg_store, jobs)] == [
        "firing",
        "resolved",
    ]


def test_postgres_batch_commits_alerts_and_jobs_together(pg_store, monkeypatch) -> None:
    import aiops_api.ingestion.adapters.postgres as adapter

    def broken_enqueue(*args, **kwargs):
        raise RuntimeError("queue unavailable")

    monkeypatch.setattr(adapter, "enqueue", broken_enqueue)
    with pytest.raises(RuntimeError):
        pg_store.record([_alert()])
    assert _rows(pg_store, alerts) == []  # no alert without its job
