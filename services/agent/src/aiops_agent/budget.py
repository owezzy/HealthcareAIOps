"""Budget enforcement: no model call starts once today's budget is exhausted (ADR-0008).

The API owns the decision (`aiops_contracts.usage.budget_status`: dollar cap
or call cap). The agent only obeys it, before every AG-UI run:

- `exhausted`: the run is refused with an AG-UI RUN_ERROR; the model is never called.
- `ok`, `warn`, `unknown`: the run goes ahead. Unknown spend is still bounded
  by the call cap, which the API applies.
- Budget unreadable (API down, bad response): the run is refused. Spending
  real money without being able to see the meter is the wrong default.
"""

import time
from collections.abc import AsyncGenerator, Callable
from dataclasses import dataclass
from typing import Any

import httpx
from ag_ui.core import EventType, RunAgentInput, RunErrorEvent, RunStartedEvent
from ag_ui_langgraph import LangGraphAgent
from pydantic import ValidationError

from aiops_contracts.usage import BudgetStatus

CACHE_SECONDS = 10.0


@dataclass(frozen=True)
class BudgetDecision:
    allowed: bool
    code: str | None = None
    message: str | None = None


ALLOW = BudgetDecision(allowed=True)


class BudgetGate:
    """Reads GET /api/budget/today, caching an answer for a few seconds."""

    def __init__(
        self,
        api_url: str,
        client: httpx.AsyncClient | None = None,
        cache_seconds: float = CACHE_SECONDS,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._url = f"{api_url.rstrip('/')}/api/budget/today"
        self._client = client or httpx.AsyncClient(timeout=2.0)
        self._cache_seconds = cache_seconds
        self._clock = clock
        self._cached: tuple[float, BudgetDecision] | None = None

    async def check(self) -> BudgetDecision:
        now = self._clock()
        if self._cached and now - self._cached[0] < self._cache_seconds:
            return self._cached[1]
        try:
            response = await self._client.get(self._url)
            response.raise_for_status()
            status = BudgetStatus.model_validate(response.json())
        except httpx.HTTPError, ValidationError, ValueError:
            # Not cached: the next run asks again as soon as the API is back.
            return BudgetDecision(
                allowed=False,
                code="budget_unavailable",
                message="The LLM budget cannot be checked right now, so the agent is paused. "
                "Monitoring and incidents are unaffected.",
            )
        decision = ALLOW if status.state != "exhausted" else _exhausted(status)
        self._cached = (now, decision)
        return decision


def _exhausted(status: BudgetStatus) -> BudgetDecision:
    limit = (
        f"${status.cap_usd:.2f} spent"
        if status.exhausted_by == "spend"
        else f"{status.call_cap} model calls made"
    )
    return BudgetDecision(
        allowed=False,
        code="budget_exhausted",
        message=f"Today's LLM budget is used up ({limit}). The agent is paused until "
        "00:00 UTC; recorded runs remain available.",
    )


class BudgetGatedAgent(LangGraphAgent):
    """LangGraphAgent that checks the budget before every run."""

    def __init__(self, *, budget_gate: BudgetGate | None = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.budget_gate = budget_gate

    def clone(self) -> BudgetGatedAgent:
        # The endpoint clones per request; the base clone rebuilds from
        # constructor flags only, so carry the gate across explicitly.
        copy = super().clone()
        copy.budget_gate = self.budget_gate
        return copy

    async def run(self, input: RunAgentInput) -> AsyncGenerator[Any]:
        if self.budget_gate is not None:
            decision = await self.budget_gate.check()
            if not decision.allowed:
                yield RunStartedEvent(
                    type=EventType.RUN_STARTED, thread_id=input.thread_id, run_id=input.run_id
                )
                yield RunErrorEvent(
                    type=EventType.RUN_ERROR, message=decision.message, code=decision.code
                )
                return
        async for event in super().run(input):
            yield event
