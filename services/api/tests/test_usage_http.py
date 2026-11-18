"""Internal usage ingestion (service-token protected) and the public budget endpoint."""

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from aiops_api.app import create_app
from aiops_api.settings import Settings

TOKEN = "svc-token"
AUTH = {"Authorization": f"Bearer {TOKEN}"}


def _settings(token: str | None = TOKEN, cap: float = 1.0, call_cap: int = 300) -> Settings:
    return Settings(
        database_url="unused",
        internal_token=token,
        daily_llm_budget_usd=cap,
        daily_llm_call_cap=call_cap,
    )


def _usage(call_id: str, cost: float | None = 0.1, metered: bool = True) -> dict:
    base = {
        "call_id": call_id,
        "thread_id": "inc-1042",
        "model": "m",
        "recorded_at": datetime.now(UTC).isoformat(),
    }
    if not metered:
        return {**base, "metered": False}
    return {**base, "input_tokens": 100, "output_tokens": 50, "total_tokens": 150, "cost_usd": cost}


@pytest.fixture
def client(usage_repo) -> TestClient:
    return TestClient(create_app(_settings(), usage_repo))


def test_internal_endpoint_fails_closed_without_a_configured_token(usage_repo) -> None:
    client = TestClient(create_app(_settings(token=None), usage_repo))
    assert client.post("/internal/usage", json=_usage("c1"), headers=AUTH).status_code == 503
    assert usage_repo.rows == {}


def test_internal_endpoint_rejects_a_wrong_or_missing_token(client, usage_repo) -> None:
    wrong = {"Authorization": "Bearer nope"}
    assert client.post("/internal/usage", json=_usage("c1"), headers=wrong).status_code == 401
    assert client.post("/internal/usage", json=_usage("c1")).status_code == 401
    assert usage_repo.rows == {}


def test_recording_is_idempotent_on_call_id(client, usage_repo) -> None:
    first = client.post("/internal/usage", json=_usage("c1"), headers=AUTH)
    retry = client.post("/internal/usage", json=_usage("c1"), headers=AUTH)
    assert (first.status_code, retry.status_code) == (201, 200)
    assert list(usage_repo.rows) == ["c1"]


def test_inconsistent_records_are_rejected(client) -> None:
    metered_without_tokens = {**_usage("c1"), "input_tokens": None}
    naive_time = {**_usage("c2"), "recorded_at": "2026-11-18T09:00:00"}
    for body in (metered_without_tokens, naive_time):
        assert client.post("/internal/usage", json=body, headers=AUTH).status_code == 422


@pytest.mark.parametrize(
    ("costs", "state", "spent"),
    [
        ([0.1, 0.2], "ok", 0.3),
        ([0.5, 0.35], "warn", 0.85),
        ([0.6, 0.6], "exhausted", 1.2),
        ([0.1, None], "unknown", None),
    ],
)
def test_budget_reflects_todays_spend(client, costs, state, spent) -> None:
    for i, cost in enumerate(costs):
        client.post("/internal/usage", json=_usage(f"c{i}", cost), headers=AUTH)

    body = client.get("/api/budget/today").json()
    assert (body["state"], body["spent_usd"], body["cap_usd"]) == (state, spent, 1.0)


def test_unmetered_call_makes_spend_unknown(client) -> None:
    client.post("/internal/usage", json=_usage("c1"), headers=AUTH)
    client.post("/internal/usage", json=_usage("c2", metered=False), headers=AUTH)

    body = client.get("/api/budget/today").json()
    assert (body["state"], body["spent_usd"], body["unmetered_calls"]) == ("unknown", None, 1)


@pytest.mark.parametrize(
    ("costs", "state", "exhausted_by"),
    [
        ([None, None, None, None, None], "exhausted", "calls"),  # unknown cost, cap reached
        ([None, None, None, None], "warn", None),  # 80% of the call cap
        ([None, None], "unknown", None),
        ([0.6, 0.6, 0.0, 0.0, 0.0], "exhausted", "spend"),  # spend wins when both apply
    ],
)
def test_call_cap_bounds_unknown_spend(usage_repo, costs, state, exhausted_by) -> None:
    client = TestClient(create_app(_settings(cap=1.0, call_cap=5), usage_repo))
    for i, cost in enumerate(costs):
        client.post("/internal/usage", json=_usage(f"c{i}", cost), headers=AUTH)

    body = client.get("/api/budget/today").json()
    assert (body["state"], body["exhausted_by"], body["call_cap"]) == (state, exhausted_by, 5)
