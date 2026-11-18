from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    Engine,
    String,
    Table,
    Text,
    UniqueConstraint,
    func,
    literal_column,
)
from sqlalchemy.dialects.postgresql import JSONB, insert

from aiops_api.db import metadata
from aiops_api.ingestion.domain import Alert, IngestOutcome
from aiops_api.queue import enqueue

CORRELATE = "correlate"

# Schema owned by migrations/versions/0002_alerts_and_jobs.py; keep the two in step.
alerts = Table(
    "alerts",
    metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("fingerprint", String(64), nullable=False),
    Column("starts_at", DateTime(timezone=True), nullable=False),
    Column("ends_at", DateTime(timezone=True), nullable=True),
    Column("alertname", String(200), nullable=False),
    Column("status", String(10), nullable=False),
    Column("component", String(200), nullable=True),
    Column("severity", String(20), nullable=True),
    Column("summary", Text, nullable=True),
    Column("labels", JSONB, nullable=False),
    Column("received_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    UniqueConstraint("fingerprint", "starts_at", name="uq_alerts_occurrence"),
)


class PostgresAlertStore:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def record(self, batch: list[Alert]) -> IngestOutcome:
        stored = updated = unchanged = 0
        with self._engine.begin() as connection:  # alerts and their jobs commit together
            for alert in batch:
                values = {
                    "fingerprint": alert.fingerprint,
                    "starts_at": alert.starts_at,
                    "ends_at": alert.ends_at,
                    "alertname": alert.alertname,
                    "status": alert.status,
                    "component": alert.component,
                    "severity": alert.severity,
                    "summary": alert.summary,
                    "labels": alert.labels,
                }
                statement = insert(alerts).values(**values)
                excluded = statement.excluded
                statement = statement.on_conflict_do_update(
                    constraint="uq_alerts_occurrence",
                    set_={
                        "status": excluded.status,
                        "ends_at": excluded.ends_at,
                        "summary": excluded.summary,
                        "updated_at": func.now(),
                    },
                    # Only a real change (e.g. firing -> resolved) counts as an update.
                    where=(alerts.c.status != excluded.status)
                    | alerts.c.ends_at.is_distinct_from(excluded.ends_at),
                ).returning(alerts.c.id, literal_column("(xmax = 0)").label("inserted"))
                row = connection.execute(statement).first()
                if row is None:
                    unchanged += 1
                    continue
                stored, updated = (stored + 1, updated) if row.inserted else (stored, updated + 1)
                enqueue(
                    connection,
                    CORRELATE,
                    f"{alert.fingerprint}:{alert.starts_at.isoformat()}:{alert.status}",
                    {"alert_id": row.id},
                )
        return IngestOutcome(stored=stored, updated=updated, unchanged=unchanged)
