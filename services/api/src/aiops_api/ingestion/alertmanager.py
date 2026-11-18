"""Alertmanager webhook payload (version 4), translated into our Alert.

Kept at the edge so Alertmanager's format never leaks into the domain.
Reference: https://prometheus.io/docs/alerting/latest/configuration/#webhook_config
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from aiops_api.ingestion.domain import Alert

#: Alertmanager sends this zero time as endsAt for alerts still firing.
_ZERO_TIME = datetime.fromisoformat("0001-01-01T00:00:00+00:00")


class _Wire(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)


class WebhookAlert(_Wire):
    status: Literal["firing", "resolved"]
    labels: dict[str, str]
    annotations: dict[str, str] = Field(default_factory=dict)
    starts_at: datetime = Field(alias="startsAt")
    ends_at: datetime | None = Field(default=None, alias="endsAt")
    fingerprint: str = Field(min_length=1, max_length=64)

    @field_validator("labels")
    @classmethod
    def _named(cls, labels: dict[str, str]) -> dict[str, str]:
        if not labels.get("alertname"):
            raise ValueError("alert has no alertname label")
        return labels

    @field_validator("starts_at", "ends_at")
    @classmethod
    def _aware(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("timestamps must carry a time zone")
        return value

    def to_alert(self) -> Alert:
        ends_at = None if self.ends_at in (None, _ZERO_TIME) else self.ends_at
        return Alert(
            fingerprint=self.fingerprint,
            alertname=self.labels["alertname"],
            status=self.status,
            starts_at=self.starts_at,
            ends_at=ends_at,
            component=self.labels.get("component"),
            severity=self.labels.get("severity"),
            summary=self.annotations.get("summary"),
            labels=dict(self.labels),
        )


class Webhook(_Wire):
    version: Literal["4"]
    status: Literal["firing", "resolved"]
    receiver: str
    alerts: list[WebhookAlert] = Field(min_length=1, max_length=1000)
