"""Alembic environment: migrations run online against AIOPS_DATABASE_URL."""

from alembic import context

from aiops_api.db import make_engine, metadata
from aiops_api.settings import Settings

target_metadata = metadata


def run_migrations_online() -> None:
    url = context.config.attributes.get("database_url") or Settings.from_env().database_url
    with make_engine(url).connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
