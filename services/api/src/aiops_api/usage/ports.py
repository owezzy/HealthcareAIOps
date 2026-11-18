from datetime import date
from typing import Protocol

from aiops_contracts.usage import LlmUsage


class UsageRepository(Protocol):
    """Implemented by adapters/postgres.py and the in-memory fake in tests."""

    def add(self, usage: LlmUsage) -> bool:
        """Store a record. Idempotent on call_id: returns False if it already existed."""
        ...

    def for_day(self, day: date) -> list[LlmUsage]:
        """Every record whose recorded_at falls on this UTC day."""
        ...

    def ping(self) -> None:
        """Raise if the store is unreachable (readiness probe)."""
        ...
