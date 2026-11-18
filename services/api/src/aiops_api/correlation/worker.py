"""Correlation worker: consumes `correlate` jobs and groups alerts into incidents.

Run: python -m aiops_api.correlation.worker   (make correlator)

Each job is handled in one transaction: claim (FOR UPDATE SKIP LOCKED),
correlate, link, mark done. A crash rolls all of it back and the job is
picked up again. An advisory lock serialises correlation across workers,
so two related alerts arriving together cannot each open an incident.
Failures retry with backoff, then go to `dead` with the error recorded.
"""

import logging
import time
from datetime import timedelta
from pathlib import Path

from sqlalchemy import (
    BigInteger,
    Column,
    Connection,
    DateTime,
    Engine,
    ForeignKey,
    String,
    Table,
    func,
    insert,
    select,
    text,
    update,
)

from aiops_api.correlation.domain import CORRELATION_WINDOW, Attach, OpenIncident, correlate
from aiops_api.db import make_engine, metadata
from aiops_api.ingestion.adapters.postgres import CORRELATE, alerts
from aiops_api.queue import jobs
from aiops_api.settings import Settings
from aiops_contracts.catalogue import Catalogue, load_catalogue

log = logging.getLogger(__name__)

#: Any fixed number shared by all workers; serialises correlation decisions.
CORRELATION_LOCK = 0x4149_4F50_5343_4F52  # "AIOPSCOR"
MAX_ATTEMPTS = 5

# Schema owned by migrations/versions/0003_incidents.py; keep the two in step.
incidents = Table(
    "incidents",
    metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("root_component", String(200), nullable=True),
    Column("status", String(20), nullable=False, server_default="open"),
    Column("opened_at", DateTime(timezone=True), nullable=False),
    Column("last_alert_at", DateTime(timezone=True), nullable=False),
    Column("merged_into", BigInteger, ForeignKey("incidents.id"), nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)
incident_alerts = Table(
    "incident_alerts",
    metadata,
    Column("alert_id", BigInteger, ForeignKey("alerts.id"), primary_key=True),
    Column("incident_id", BigInteger, ForeignKey("incidents.id"), nullable=False),
)


class CorrelationWorker:
    def __init__(
        self,
        engine: Engine,
        catalogue: Catalogue,
        max_attempts: int = MAX_ATTEMPTS,
        backoff: timedelta = timedelta(seconds=5),
    ) -> None:
        self._engine = engine
        self._catalogue = catalogue
        self._max_attempts = max_attempts
        self._backoff = backoff

    def run_once(self) -> bool:
        """Handle one due job. Returns False when there was nothing to do."""
        with self._engine.begin() as connection:
            connection.execute(
                text("SELECT pg_advisory_xact_lock(:key)"), {"key": CORRELATION_LOCK}
            )
            job = connection.execute(
                select(jobs)
                .where(
                    jobs.c.kind == CORRELATE,
                    jobs.c.status == "pending",
                    jobs.c.available_at <= func.now(),
                )
                .order_by(jobs.c.id)
                .limit(1)
                .with_for_update(skip_locked=True)
            ).first()
            if job is None:
                return False
            attempts = job.attempts + 1
            try:
                with connection.begin_nested():  # a failure undoes only the correlation
                    self._correlate(connection, job.payload["alert_id"])
            except Exception as error:
                dead = attempts >= self._max_attempts
                log.warning("correlate job %s failed (attempt %s): %s", job.id, attempts, error)
                connection.execute(
                    update(jobs)
                    .where(jobs.c.id == job.id)
                    .values(
                        attempts=attempts,
                        status="dead" if dead else "pending",
                        available_at=func.now() + self._backoff * attempts,
                        last_error=str(error)[:2000],
                    )
                )
                return True
            connection.execute(
                update(jobs).where(jobs.c.id == job.id).values(attempts=attempts, status="done")
            )
            return True

    def drain(self) -> int:
        handled = 0
        while self.run_once():
            handled += 1
        return handled

    def _correlate(self, connection: Connection, alert_id: int) -> None:
        alert = connection.execute(select(alerts).where(alerts.c.id == alert_id)).first()
        if alert is None:
            raise LookupError(f"alert {alert_id} does not exist")
        already = connection.execute(
            select(incident_alerts.c.incident_id).where(incident_alerts.c.alert_id == alert_id)
        ).first()
        if already is not None:
            return  # duplicate job, or the resolve of an alert already correlated

        rows = connection.execute(
            select(incidents.c.id, incidents.c.root_component, incidents.c.last_alert_at).where(
                incidents.c.status == "open",
                incidents.c.last_alert_at >= alert.starts_at - CORRELATION_WINDOW,
            )
        ).all()
        decision = correlate(
            alert.component,
            alert.starts_at,
            [OpenIncident(r.id, r.root_component, r.last_alert_at) for r in rows],
            self._catalogue,
        )

        if isinstance(decision, Attach):
            target = decision.incident_id
            if decision.merge:
                connection.execute(
                    update(incident_alerts)
                    .where(incident_alerts.c.incident_id.in_(decision.merge))
                    .values(incident_id=target)
                )
                connection.execute(
                    update(incidents)
                    .where(incidents.c.id.in_(decision.merge))
                    .values(status="merged", merged_into=target)
                )
            changes: dict = {
                "last_alert_at": func.greatest(incidents.c.last_alert_at, alert.starts_at)
            }
            if decision.new_root:
                changes["root_component"] = decision.new_root
            connection.execute(update(incidents).where(incidents.c.id == target).values(**changes))
        else:
            target = connection.execute(
                insert(incidents)
                .values(
                    root_component=decision.root_component,
                    status="open",
                    opened_at=alert.starts_at,
                    last_alert_at=alert.starts_at,
                )
                .returning(incidents.c.id)
            ).scalar_one()
        connection.execute(insert(incident_alerts).values(alert_id=alert_id, incident_id=target))


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = Settings.from_env()
    worker = CorrelationWorker(
        make_engine(settings.database_url), load_catalogue(Path(settings.catalogue_path))
    )
    log.info("correlation worker started")
    while True:
        if worker.drain() == 0:
            time.sleep(1.0)


if __name__ == "__main__":
    main()
