"""Runtime configuration, read once from the environment at startup."""

from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_DATABASE_URL = "postgresql+psycopg://aiops:aiops@localhost:5432/aiops"
DEFAULT_DAILY_LLM_BUDGET_USD = 5.0
DEFAULT_DAILY_LLM_CALL_CAP = 300


@dataclass(frozen=True)
class Settings:
    database_url: str
    #: Service token for /internal endpoints. None means they refuse every call (fail closed).
    internal_token: str | None
    daily_llm_budget_usd: float
    #: Calls per UTC day; caps models whose cost is unknown (ADR-0008).
    daily_llm_call_cap: int = DEFAULT_DAILY_LLM_CALL_CAP

    @classmethod
    def from_env(cls) -> Settings:
        budget = float(os.environ.get("AIOPS_DAILY_LLM_BUDGET_USD", DEFAULT_DAILY_LLM_BUDGET_USD))
        if budget <= 0:
            raise ValueError("AIOPS_DAILY_LLM_BUDGET_USD must be positive")
        call_cap = int(os.environ.get("AIOPS_DAILY_LLM_CALL_CAP", DEFAULT_DAILY_LLM_CALL_CAP))
        if call_cap <= 0:
            raise ValueError("AIOPS_DAILY_LLM_CALL_CAP must be positive")
        return cls(
            database_url=os.environ.get("AIOPS_DATABASE_URL", DEFAULT_DATABASE_URL),
            internal_token=os.environ.get("AIOPS_INTERNAL_TOKEN") or None,
            daily_llm_budget_usd=budget,
            daily_llm_call_cap=call_cap,
        )
