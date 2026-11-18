from datetime import date

from aiops_api.usage.ports import UsageRepository
from aiops_contracts.usage import BudgetStatus, LlmUsage, budget_status, summarize


def record_usage(repo: UsageRepository, usage: LlmUsage) -> bool:
    """Store one LLM call reported by the agent. Returns False for a duplicate (retry)."""
    return repo.add(usage)


def daily_budget(repo: UsageRepository, day: date, cap_usd: float, call_cap: int) -> BudgetStatus:
    """Spend and calls against the daily caps; 'exhausted' pauses the agent (Replay mode)."""
    return budget_status(summarize(repo.for_day(day), day), cap_usd, call_cap)
