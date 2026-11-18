"""LLM token usage, cost and the daily budget (plan §8.2, §10.1, ADR-0008).

Shared so the agent (records usage), the API (stores it, enforces the budget)
and the evals (cost per investigation) all count tokens and dollars the same way.
"""

from collections import defaultdict
from collections.abc import Iterable
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Literal, Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

_MILLION = 1_000_000
BUDGET_WARN_RATIO = 0.8


class _Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ModelPrice(_Contract):
    """USD per million tokens, from the provider's published price list."""

    input_per_million_usd: float = Field(ge=0)
    output_per_million_usd: float = Field(ge=0)

    def cost_usd(self, input_tokens: int, output_tokens: int) -> float:
        return round(
            input_tokens * self.input_per_million_usd / _MILLION
            + output_tokens * self.output_per_million_usd / _MILLION,
            6,
        )


class PriceTable(_Contract):
    """Prices keyed by model ID as reported by the provider (e.g. response model_name)."""

    models: dict[str, ModelPrice] = Field(default_factory=dict)

    def cost_usd(self, model: str, input_tokens: int, output_tokens: int) -> float | None:
        """None when the model has no price: cost is unknown, never guessed."""
        price = self.models.get(model)
        return None if price is None else price.cost_usd(input_tokens, output_tokens)


class LlmUsage(_Contract):
    """One LLM call. Unmetered calls (provider reported no usage) carry no token counts."""

    call_id: str = Field(min_length=1, max_length=200)
    thread_id: str | None = Field(default=None, max_length=200)
    provider: str | None = Field(default=None, max_length=100)
    model: str = Field(min_length=1, max_length=200)
    metered: bool = True
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)
    cost_usd: float | None = Field(default=None, ge=0)
    recorded_at: datetime

    @model_validator(mode="after")
    def _metered_has_tokens(self) -> Self:
        counts = (self.input_tokens, self.output_tokens, self.total_tokens)
        if self.metered and any(c is None for c in counts):
            raise ValueError("a metered call must report input, output and total tokens")
        if not self.metered and (any(c is not None for c in counts) or self.cost_usd is not None):
            raise ValueError("an unmetered call has no token counts or cost")
        if self.recorded_at.tzinfo is None:
            raise ValueError("recorded_at must be timezone-aware")
        return self


class ModelUsageTotal(_Contract):
    model: str
    calls: int
    unmetered_calls: int
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float | None


class UsageSummary(_Contract):
    """Daily totals.

    cost_usd is None if any call that day had an unknown price or reported no
    usage at all: spend is then unknown, never understated.
    """

    day: date
    calls: int
    unmetered_calls: int
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float | None
    by_model: tuple[ModelUsageTotal, ...]


BudgetState = Literal["ok", "warn", "exhausted", "unknown"]


class BudgetStatus(_Contract):
    """What the console's budget meter shows. Exhausted means Replay mode (design spec §6)."""

    day: date
    cap_usd: float
    spent_usd: float | None
    state: BudgetState
    calls: int
    unmetered_calls: int


def summarize(records: Iterable[LlmUsage], day: date) -> UsageSummary:
    """Totals for one UTC day. Pure: the API and the agent's dev ledger share it."""
    todays = [r for r in records if r.recorded_at.astimezone(UTC).date() == day]
    by_model: dict[str, list[LlmUsage]] = defaultdict(list)
    for usage in todays:
        by_model[usage.model].append(usage)
    totals = _totals(todays)
    return UsageSummary(
        day=day,
        **totals,
        by_model=tuple(
            ModelUsageTotal(model=model, **_totals(calls))
            for model, calls in sorted(by_model.items())
        ),
    )


def budget_status(summary: UsageSummary, cap_usd: float) -> BudgetStatus:
    spent = summary.cost_usd
    if spent is None:
        state: BudgetState = "unknown"
    elif spent >= cap_usd:
        state = "exhausted"
    elif spent >= cap_usd * BUDGET_WARN_RATIO:
        state = "warn"
    else:
        state = "ok"
    return BudgetStatus(
        day=summary.day,
        cap_usd=cap_usd,
        spent_usd=spent,
        state=state,
        calls=summary.calls,
        unmetered_calls=summary.unmetered_calls,
    )


def _totals(calls: list[LlmUsage]) -> dict[str, int | float | None]:
    metered = [c for c in calls if c.metered]
    unmetered = len(calls) - len(metered)
    costs = [c.cost_usd for c in metered]
    known = unmetered == 0 and all(cost is not None for cost in costs)
    return {
        "calls": len(calls),
        "unmetered_calls": unmetered,
        "input_tokens": sum(c.input_tokens or 0 for c in metered),
        "output_tokens": sum(c.output_tokens or 0 for c in metered),
        "total_tokens": sum(c.total_tokens or 0 for c in metered),
        "cost_usd": round(sum(c for c in costs if c is not None), 6) if known else None,
    }


def load_price_table(path: Path) -> PriceTable:
    raw = yaml.safe_load(path.read_text()) or {}
    return PriceTable.model_validate({"models": raw.get("models") or {}})
