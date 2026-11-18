from typing import Protocol

from aiops_api.ingestion.domain import Alert, IngestOutcome


class AlertStore(Protocol):
    """Implemented by adapters/postgres.py and the in-memory fake in tests."""

    def record(self, alerts: list[Alert]) -> IngestOutcome:
        """Store alerts idempotently on (fingerprint, starts_at).

        New alerts and changed ones (firing -> resolved) each queue one
        correlation job, in the same transaction as the alert itself.
        """
        ...
