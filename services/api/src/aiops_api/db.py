"""Shared SQLAlchemy metadata. Tables register here; Alembic migrations own the schema."""

from sqlalchemy import Engine, MetaData, create_engine

metadata = MetaData()


def make_engine(database_url: str) -> Engine:
    # Connects lazily on first use, so the app starts even if Postgres is not up yet.
    return create_engine(database_url, pool_pre_ping=True)
