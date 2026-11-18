"""Budget enforcement: an exhausted or unreadable budget stops runs before any model call."""

import asyncio
import json

import httpx
import pytest
from ag_ui_langgraph import add_langgraph_fastapi_endpoint
from fastapi import FastAPI
from fastapi.testclient import TestClient

from aiops_agent.budget import BudgetGate, BudgetGatedAgent
from aiops_agent.llm import FakeEchoChatModel
from aiops_agent.spike_graph import build_spike_graph
from aiops_agent.usage import UsageLedger, UsageRecorder
from aiops_contracts.usage import PriceTable


def budget(state: str, exhausted_by: str | None = None) -> dict:
    return {
        "day": "2026-11-18",
        "cap_usd": 5.0,
        "call_cap": 300,
        "spent_usd": None,
        "state": state,
        "exhausted_by": exhausted_by,
        "calls": 300,
        "unmetered_calls": 0,
    }


class FakeBudgetApi:
    def __init__(self, *responses: httpx.Response | Exception) -> None:
        self.responses = list(responses)
        self.calls = 0

    def handler(self, request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/budget/today"
        self.calls += 1
        response = self.responses.pop(0) if len(self.responses) > 1 else self.responses[0]
        if isinstance(response, Exception):
            raise response
        return response

    def gate(self, clock=lambda: 0.0) -> BudgetGate:
        client = httpx.AsyncClient(transport=httpx.MockTransport(self.handler))
        return BudgetGate("http://api:8000", client=client, clock=clock)


def run_agent(gate: BudgetGate, ledger: UsageLedger) -> list[dict]:
    app = FastAPI()
    add_langgraph_fastapi_endpoint(
        app=app,
        agent=BudgetGatedAgent(
            budget_gate=gate,
            name="default",
            graph=build_spike_graph(FakeEchoChatModel()),
            config={"callbacks": [UsageRecorder(ledger, PriceTable())]},
        ),
        path="/agent",
    )
    payload = {
        "threadId": "inc-1",
        "runId": "r-1",
        "state": {},
        "tools": [],
        "context": [],
        "forwardedProps": {},
        "messages": [{"id": "m-1", "role": "user", "content": "hi"}],
    }
    with TestClient(app).stream("POST", "/agent", json=payload) as response:
        assert response.status_code == 200
        return [
            json.loads(line.removeprefix("data: "))
            for line in response.iter_lines()
            if line.startswith("data: ")
        ]


@pytest.mark.parametrize(
    ("exhausted_by", "expected"), [("spend", "$5.00 spent"), ("calls", "300 model calls made")]
)
def test_exhausted_budget_refuses_the_run_without_calling_the_model(exhausted_by, expected):
    api = FakeBudgetApi(httpx.Response(200, json=budget("exhausted", exhausted_by)))
    ledger = UsageLedger()

    events = run_agent(api.gate(), ledger)

    assert [e["type"] for e in events] == ["RUN_STARTED", "RUN_ERROR"]
    assert events[1]["code"] == "budget_exhausted"
    assert expected in events[1]["message"]
    assert ledger.records() == []  # the model was never called


@pytest.mark.parametrize("state", ["ok", "warn", "unknown"])
def test_budget_with_headroom_lets_the_run_through(state):
    api = FakeBudgetApi(httpx.Response(200, json=budget(state)))
    ledger = UsageLedger()

    events = run_agent(api.gate(), ledger)

    assert events[-1]["type"] == "RUN_FINISHED"
    assert len(ledger.records()) == 1


@pytest.mark.parametrize(
    "failure",
    [httpx.Response(503), httpx.ConnectError("api down"), httpx.Response(200, json={"bad": 1})],
)
def test_unreadable_budget_fails_closed(failure):
    ledger = UsageLedger()
    events = run_agent(FakeBudgetApi(failure).gate(), ledger)

    assert events[-1]["type"] == "RUN_ERROR"
    assert events[-1]["code"] == "budget_unavailable"
    assert ledger.records() == []


def test_answers_are_cached_briefly_but_failures_are_not():
    asyncio.run(_cache_scenario())


async def _cache_scenario() -> None:
    now = [0.0]
    api = FakeBudgetApi(
        httpx.ConnectError("api restarting"),
        httpx.Response(200, json=budget("ok")),
        httpx.Response(200, json=budget("exhausted", "spend")),
    )
    gate = api.gate(clock=lambda: now[0])

    assert (await gate.check()).code == "budget_unavailable"  # failure: not cached
    assert (await gate.check()).allowed  # API back
    now[0] = 5.0
    assert (await gate.check()).allowed  # cached; no request
    assert api.calls == 2
    now[0] = 11.0
    assert (await gate.check()).code == "budget_exhausted"  # cache expired
    assert api.calls == 3
