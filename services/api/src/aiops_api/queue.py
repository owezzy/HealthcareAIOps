"""Postgres job queue (ADR-0003): jobs are inserted in the producer's own
transaction and consumed with SELECT ... FOR UPDATE SKIP LOCKED.

Schema owned by migrations/versions/0002_alerts_and_jobs.py.
"""

from sqlalchemy import (
    BigInteger,
    Column,
    Connection,
    DateTime,
    Integer,
    String,
    Table,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, insert

from aiops_api.db import metadata

jobs = Table(
    "jobs",
    metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("kind", String(50), nullable=False),
    Column("dedupe_key", String(300), nullable=False),
    Column("payload", JSONB, nullable=False),
    Column("status", String(20), nullable=False, server_default="pending"),
    Column("attempts", Integer, nullable=False, server_default="0"),
    Column("available_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)


def enqueue(connection: Connection, kind: str, dedupe_key: str, payload: dict) -> bool:
    """Queue a job inside the caller's transaction. Returns False for a duplicate."""
    statement = (
        insert(jobs)
        .values(kind=kind, dedupe_key=dedupe_key, payload=payload)
        .on_conflict_do_nothing(index_elements=[jobs.c.kind, jobs.c.dedupe_key])
        .returning(jobs.c.id)
    )
    return connection.execute(statement).first() is not None
