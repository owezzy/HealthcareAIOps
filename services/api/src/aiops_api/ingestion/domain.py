from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

AlertStatus = Literal["firing", "resolved"]


@dataclass(frozen=True)
class Alert:
    """One firing of one alert. Identity: (fingerprint, starts_at)."""

    fingerprint: str
    alertname: str
    status: AlertStatus
    starts_at: datetime
    ends_at: datetime | None
    component: str | None
    severity: str | None
    summary: str | None
    labels: dict[str, str] = field(default_factory=dict)

    @property
    def key(self) -> tuple[str, datetime]:
        return (self.fingerprint, self.starts_at)


@dataclass(frozen=True)
class IngestOutcome:
    stored: int = 0
    updated: int = 0
    unchanged: int = 0
