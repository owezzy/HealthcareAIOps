"""Correlation worker on real Postgres: alerts in through ingestion, incidents out."""

import random
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import insert, select, text

from aiops_api.correlation.worker import CorrelationWorker, incident_alerts, incidents
from aiops_api.db import make_engine
from aiops_api.ingestion.adapters.postgres import PostgresAlertStore
from aiops_api.ingestion.domain import Alert
from aiops_api.queue import jobs
from aiops_contracts.catalogue import load_catalogue
from aiops_contracts.scenarios import load_scenarios

SIM = Path(__file__).resolve().parents[3] / "sim"
CATALOGUE = load_catalogue(SIM / "services.yaml")
SCENARIOS = {s.id: s for s in load_scenarios(SIM / "scenarios")}
T0 = datetime(2026, 11, 18, 9, 0, tzinfo=UTC)


@pytest.fixture
def engine(postgres_url):
    engine = make_engine(postgres_url)
    with engine.begin() as connection:
        connection.execute(
            text("TRUNCATE incident_alerts, incidents, alerts, jobs RESTART IDENTITY CASCADE")
        )
    return engine


def alerts_for(scenario_id: str, order_seed: int | None = None) -> list[Alert]:
    signals = [s for s in SCENARIOS[scenario_id].expected_signals if s.kind == "alert"]
    if order_seed is not None:
        random.Random(order_seed).shuffle(signals)
    return [
        Alert(
            fingerprint=f"{scenario_id}-{n}-{s.component}",
            alertname=f"{s.component}Alert",
            status="firing",
            starts_at=T0 + timedelta(seconds=10 * n),
            ends_at=None,
            component=s.component,
            severity="high",
            summary=s.description,
            labels={},
        )
        for n, s in enumerate(signals)
    ]


def open_incidents(engine) -> list[dict]:
    with engine.connect() as connection:
        rows = (
            connection.execute(
                select(incidents.c.id, incidents.c.root_component).where(
                    incidents.c.status == "open"
                )
            )
            .mappings()
            .all()
        )
        linked = connection.execute(select(incident_alerts)).mappings().all()
    return [
        {
            "root": r["root_component"],
            "alerts": sum(1 for link in linked if link["incident_id"] == r["id"]),
        }
        for r in rows
    ]


@pytest.mark.parametrize("seed", [None, 1, 2, 3])
def test_s6_alert_storm_becomes_one_incident_rooted_at_sso(engine, seed) -> None:
    storm = alerts_for("S6", seed)
    PostgresAlertStore(engine).record(storm)
    assert CorrelationWorker(engine, CATALOGUE).drain() == len(storm)
    assert open_incidents(engine) == [{"root": "sso", "alerts": len(storm)}]


def test_s1_alerts_become_one_incident_rooted_at_ehr_api(engine) -> None:
    PostgresAlertStore(engine).record(alerts_for("S1"))
    CorrelationWorker(engine, CATALOGUE).drain()
    assert open_incidents(engine) == [{"root": "ehr-api", "alerts": 1}]


def test_duplicate_jobs_do_not_duplicate_incidents(engine) -> None:
    PostgresAlertStore(engine).record(alerts_for("S1"))
    with engine.begin() as connection:  # the same alert queued twice
        connection.execute(
            insert(jobs).values(kind="correlate", dedupe_key="replay", payload={"alert_id": 1})
        )
    CorrelationWorker(engine, CATALOGUE).drain()
    assert open_incidents(engine) == [{"root": "ehr-api", "alerts": 1}]


def test_resolve_jobs_do_not_open_new_incidents(engine) -> None:
    store = PostgresAlertStore(engine)
    [firing] = alerts_for("S4")
    store.record([firing])
    resolved = Alert(**{**firing.__dict__, "status": "resolved", "ends_at": T0 + timedelta(1)})
    store.record([resolved])
    CorrelationWorker(engine, CATALOGUE).drain()
    assert open_incidents(engine) == [{"root": "patient-portal", "alerts": 1}]


def test_failing_job_retries_then_goes_dead_with_its_error(engine) -> None:
    with engine.begin() as connection:
        connection.execute(
            insert(jobs).values(kind="correlate", dedupe_key="ghost", payload={"alert_id": 999})
        )
    worker = CorrelationWorker(engine, CATALOGUE, max_attempts=2, backoff=timedelta(0))
    worker.drain()
    with engine.connect() as connection:
        job = connection.execute(select(jobs)).mappings().one()
    assert (job["status"], job["attempts"]) == ("dead", 2)
    assert "alert 999 does not exist" in job["last_error"]


def test_completed_jobs_are_marked_done(engine) -> None:
    PostgresAlertStore(engine).record(alerts_for("S3"))
    CorrelationWorker(engine, CATALOGUE).drain()
    with engine.connect() as connection:
        statuses = {r.status for r in connection.execute(select(jobs.c.status))}
    assert statuses == {"done"}
