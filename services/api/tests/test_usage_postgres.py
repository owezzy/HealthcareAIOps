"""PostgresUsageRepository against a real, migrated database."""

from datetime import UTC, date, datetime

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from aiops_api.db import make_engine
from aiops_api.usage.adapters.postgres import PostgresUsageRepository
from aiops_contracts.usage import LlmUsage


@pytest.fixture
def repo(postgres_url: str) -> PostgresUsageRepository:
    engine = make_engine(postgres_url)
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE llm_usage"))
    return PostgresUsageRepository(engine)


def _usage(call_id: str, at: datetime, **overrides) -> LlmUsage:
    fields = {
        "call_id": call_id,
        "thread_id": "inc-1042",
        "provider": "openai",
        "model": "m",
        "input_tokens": 1_000,
        "output_tokens": 500,
        "total_tokens": 1_500,
        "cost_usd": 0.006,
        "recorded_at": at,
    }
    return LlmUsage(**{**fields, **overrides})


def test_round_trips_metered_and_unmetered_records(repo) -> None:
    at = datetime(2026, 11, 18, 9, 30, tzinfo=UTC)
    metered = _usage("c1", at)
    unmetered = LlmUsage(call_id="c2", model="m", metered=False, recorded_at=at)

    assert repo.add(metered) and repo.add(unmetered)
    stored = {u.call_id: u for u in repo.for_day(date(2026, 11, 18))}
    assert stored == {"c1": metered, "c2": unmetered}


def test_add_is_idempotent_on_call_id(repo) -> None:
    at = datetime(2026, 11, 18, 9, 30, tzinfo=UTC)
    assert repo.add(_usage("c1", at)) is True
    assert repo.add(_usage("c1", at, cost_usd=99.0)) is False
    [stored] = repo.for_day(date(2026, 11, 18))
    assert stored.cost_usd == 0.006  # the retry did not overwrite


def test_for_day_uses_utc_day_boundaries(repo) -> None:
    repo.add(_usage("late", datetime(2026, 11, 17, 23, 59, 59, tzinfo=UTC)))
    repo.add(_usage("start", datetime(2026, 11, 18, 0, 0, tzinfo=UTC)))
    assert [u.call_id for u in repo.for_day(date(2026, 11, 18))] == ["start"]


def test_schema_rejects_inconsistent_rows(repo, postgres_url) -> None:
    with pytest.raises(IntegrityError), make_engine(postgres_url).begin() as connection:
        connection.execute(
            text(
                "INSERT INTO llm_usage (call_id, model, metered, recorded_at)"
                " VALUES ('bad', 'm', true, now())"
            )
        )


def test_http_records_usage_and_reports_budget_end_to_end(repo, postgres_url) -> None:
    from fastapi.testclient import TestClient

    from aiops_api.app import create_app
    from aiops_api.settings import Settings

    settings = Settings(database_url=postgres_url, internal_token="t", daily_llm_budget_usd=0.01)
    client = TestClient(create_app(settings))
    body = _usage("e2e-1", datetime.now(UTC)).model_dump(mode="json")

    posted = client.post("/internal/usage", json=body, headers={"Authorization": "Bearer t"})
    assert posted.status_code == 201
    assert client.get("/ready").status_code == 200
    budget = client.get("/api/budget/today").json()
    assert (budget["spent_usd"], budget["state"]) == (0.006, "ok")
