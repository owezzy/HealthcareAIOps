"""Fixtures: an in-memory UsageRepository fake and a real, migrated Postgres."""

import os
import shutil
import socket
import subprocess
import tempfile
from collections.abc import Iterator
from datetime import date
from pathlib import Path

import psycopg
import pytest
from alembic import command
from alembic.config import Config

from aiops_contracts.usage import LlmUsage

API_DIR = Path(__file__).resolve().parents[1]
HOMEBREW_PG = Path("/opt/homebrew/opt/postgresql@18/bin")


class InMemoryUsageRepository:
    def __init__(self) -> None:
        self.rows: dict[str, LlmUsage] = {}

    def add(self, usage: LlmUsage) -> bool:
        if usage.call_id in self.rows:
            return False
        self.rows[usage.call_id] = usage
        return True

    def for_day(self, day: date) -> list[LlmUsage]:
        return [u for u in self.rows.values() if u.recorded_at.date() == day]

    def ping(self) -> None:
        return None


@pytest.fixture
def usage_repo() -> InMemoryUsageRepository:
    return InMemoryUsageRepository()


def _pg_bin(name: str) -> str | None:
    found = shutil.which(name)
    if found:
        return found
    candidate = HOMEBREW_PG / name
    return str(candidate) if candidate.exists() else None


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture(scope="session")
def postgres_url() -> Iterator[str]:
    """A migrated database. Uses AIOPS_TEST_DATABASE_URL (CI) or a throwaway local cluster."""
    if url := os.environ.get("AIOPS_TEST_DATABASE_URL"):
        _migrate(url)
        yield url
        return

    initdb, pg_ctl = _pg_bin("initdb"), _pg_bin("pg_ctl")
    if not (initdb and pg_ctl):
        pytest.skip("no Postgres: set AIOPS_TEST_DATABASE_URL or install postgresql")

    data_dir = tempfile.mkdtemp(prefix="aiops-pg-")
    port = _free_port()
    try:
        subprocess.run(
            [initdb, "-D", data_dir, "-U", "aiops", "--auth=trust", "-E", "UTF8"],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            [
                pg_ctl,
                "-D",
                data_dir,
                "-l",
                f"{data_dir}/log",
                "-w",
                "start",
                "-o",
                f"-p {port} -c listen_addresses=127.0.0.1 -c unix_socket_directories=''",
            ],
            check=True,
            capture_output=True,
        )
        with psycopg.connect(
            f"host=127.0.0.1 port={port} user=aiops dbname=postgres", autocommit=True
        ) as connection:
            connection.execute("CREATE DATABASE aiops_test")
        url = f"postgresql+psycopg://aiops@127.0.0.1:{port}/aiops_test"
        _migrate(url)
        yield url
    finally:
        subprocess.run([pg_ctl, "-D", data_dir, "-m", "fast", "stop"], capture_output=True)
        shutil.rmtree(data_dir, ignore_errors=True)


def _migrate(url: str) -> None:
    config = Config(str(API_DIR / "alembic.ini"))
    config.attributes["database_url"] = url
    command.upgrade(config, "head")
