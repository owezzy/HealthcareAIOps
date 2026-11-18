from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Engine,
    Integer,
    Numeric,
    String,
    Table,
    select,
    text,
)
from sqlalchemy.dialects.postgresql import insert

from aiops_api.db import metadata
from aiops_contracts.usage import LlmUsage

# Schema owned by migrations/versions/0001_llm_usage.py; keep the two in step.
llm_usage = Table(
    "llm_usage",
    metadata,
    Column("call_id", String(200), primary_key=True),
    Column("thread_id", String(200), nullable=True),
    Column("provider", String(100), nullable=True),
    Column("model", String(200), nullable=False),
    Column("metered", Boolean, nullable=False),
    Column("input_tokens", Integer, nullable=True),
    Column("output_tokens", Integer, nullable=True),
    Column("total_tokens", Integer, nullable=True),
    Column("cost_usd", Numeric(14, 6), nullable=True),
    Column("recorded_at", DateTime(timezone=True), nullable=False),
)


class PostgresUsageRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def add(self, usage: LlmUsage) -> bool:
        statement = (
            insert(llm_usage)
            .values(**usage.model_dump())
            .on_conflict_do_nothing(index_elements=[llm_usage.c.call_id])
            .returning(llm_usage.c.call_id)
        )
        with self._engine.begin() as connection:
            return connection.execute(statement).first() is not None

    def for_day(self, day: date) -> list[LlmUsage]:
        start = datetime.combine(day, time.min, tzinfo=UTC)
        statement = select(llm_usage).where(
            llm_usage.c.recorded_at >= start,
            llm_usage.c.recorded_at < start + timedelta(days=1),
        )
        with self._engine.connect() as connection:
            rows = connection.execute(statement).mappings().all()
        return [
            LlmUsage.model_validate(
                {**row, "cost_usd": None if row["cost_usd"] is None else float(row["cost_usd"])}
            )
            for row in rows
        ]

    def ping(self) -> None:
        with self._engine.connect() as connection:
            connection.execute(text("SELECT 1"))
