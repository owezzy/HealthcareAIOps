from fastapi.testclient import TestClient

from aiops_api.app import create_app
from aiops_api.settings import Settings

SETTINGS = Settings(database_url="unused", internal_token="t", daily_llm_budget_usd=5.0)


def test_health_reports_ok(usage_repo) -> None:
    response = TestClient(create_app(SETTINGS, usage_repo)).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_reports_database_unavailable(usage_repo) -> None:
    def down() -> None:
        raise ConnectionError("db down")

    usage_repo.ping = down
    response = TestClient(create_app(SETTINGS, usage_repo)).get("/ready")
    assert response.status_code == 503
