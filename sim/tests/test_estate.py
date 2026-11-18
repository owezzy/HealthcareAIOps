"""The six demo services, wired together in-process, behave as the scenarios expect."""

import asyncio
import logging
from pathlib import Path

import httpx
import pytest

from aiops_contracts.catalogue import load_catalogue
from aiops_sim.app import Faults, QueuedMessage, create_app
from aiops_sim.config import build_config

SIM = Path(__file__).resolve().parents[1]
CATALOGUE = load_catalogue(SIM / "services.yaml")
APPS = ["sso", "ehr-api", "interface-engine", "lis", "pacs", "patient-portal"]
ADMIN = "admin-token"


class Estate:
    """All six services; HTTP between them is routed in-process by hostname."""

    def __init__(self, env: dict[str, dict[str, str]] | None = None) -> None:
        self.apps = {}
        estate = self

        class Router(httpx.AsyncBaseTransport):
            async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
                app = estate.apps[request.url.host]
                call = httpx.ASGITransport(app=app).handle_async_request(request)
                # httpx enforces timeouts in its network layer, which ASGITransport
                # skips; apply the request's read timeout the same way here.
                timeout = request.extensions.get("timeout", {}).get("read")
                try:
                    return await asyncio.wait_for(call, timeout)
                except TimeoutError as error:
                    raise httpx.ReadTimeout("timed out", request=request) from error

        self.client = httpx.AsyncClient(transport=Router())
        for component in APPS:
            config = build_config(component, CATALOGUE, (env or {}).get(component, {}))
            self.apps[component] = create_app(config, client=self.client, admin_token=ADMIN)

    def service(self, component: str):
        return self.apps[component].state.service

    async def get(self, component: str, path: str = "/work") -> httpx.Response:
        return await self.client.get(f"http://{component}:8080{path}")

    async def metrics(self, component: str) -> str:
        return (await self.get(component, "/metrics")).text


def run(coro):
    return asyncio.run(coro)


# --- topology ------------------------------------------------------------------


def test_dependencies_follow_the_catalogue() -> None:
    config = build_config("ehr-api", CATALOGUE, {})
    assert (config.app_dependencies, config.database, config.volume) == (("sso",), "ehr-db", None)
    pacs = build_config("pacs", CATALOGUE, {})
    assert (pacs.app_dependencies, pacs.volume) == (("sso",), "pacs-store")
    engine = build_config("interface-engine", CATALOGUE, {})
    assert engine.is_router and engine.app_dependencies == ("lis", "pacs", "ehr-api")


def test_only_applications_can_run() -> None:
    with pytest.raises(ValueError, match="not an application"):
        build_config("ehr-db", CATALOGUE, {})


def test_healthy_estate_serves_every_entry_point() -> None:
    async def scenario():
        estate = Estate()
        return [(await estate.get(c)).status_code for c in APPS if c != "interface-engine"]

    assert run(scenario()) == [200, 200, 200, 200, 200]


# --- scenario signals ----------------------------------------------------------------


def test_s1_small_db_pool_exhausts_under_load() -> None:
    """S1: DB_POOL_SIZE 50 -> 5 (a real rollout) makes ehr-api time out on its pool."""
    env = {"ehr-api": {"DB_POOL_SIZE": "1", "DB_QUERY_MS": "1500", "APP_VERSION": "v2.3.1"}}

    async def scenario():
        estate = Estate(env)
        codes = [
            r.status_code for r in await asyncio.gather(*(estate.get("ehr-api") for _ in range(3)))
        ]
        return codes, await estate.metrics("ehr-api")

    codes, metrics = run(scenario())
    assert 503 in codes and 200 in codes
    assert 'db_pool_size{component="ehr-api",database="ehr-db"} 1.0' in metrics
    assert 'app_info{component="ehr-api",version="v2.3.1"} 1.0' in metrics


def test_s2_lis_down_backs_up_the_interface_engine_queue(caplog) -> None:
    """S2: lis failing makes interface-engine queue and retry; it recovers when lis does."""

    async def scenario():
        estate = Estate()
        estate.service("lis").apply_faults(Faults(unavailable=True))
        engine = estate.service("interface-engine")
        for _ in range(3):
            engine.enqueue(QueuedMessage(destination="lis"))
        with caplog.at_level(logging.WARNING, logger="aiops_sim.interface-engine"):
            await engine.drain_once()
        backed_up = await estate.metrics("interface-engine")
        estate.service("lis").apply_faults(Faults())
        for _ in range(3):
            await engine.drain_once()
        return backed_up, await estate.metrics("interface-engine")

    backed_up, recovered = run(scenario())
    assert 'queue_depth{component="interface-engine",destination="lis"} 3.0' in backed_up
    assert 'queue_depth{component="interface-engine",destination="lis"} 0.0' in recovered


def test_s2_delivery_failure_is_logged_like_the_scenario() -> None:
    async def scenario():
        estate = Estate()
        estate.service("lis").apply_faults(Faults(unavailable=True))
        engine = estate.service("interface-engine")
        engine.enqueue(QueuedMessage(destination="lis"))
        records = []
        handler = logging.Handler()
        handler.emit = records.append
        engine.log.addHandler(handler)
        await engine.drain_once()
        return [r.getMessage() for r in records]

    assert "ORU^R01 delivery to lis failed: 503 Service Unavailable (retrying)" in run(scenario())


def test_s3_full_volume_fails_pacs_uploads() -> None:
    async def scenario():
        estate = Estate()
        estate.service("pacs").apply_faults(Faults(volume_used_percent=96))
        return await estate.get("pacs"), await estate.metrics("pacs")

    response, metrics = run(scenario())
    assert response.status_code == 507 and "No space left on device" in response.text
    assert 'volume_used_ratio{component="pacs",volume="pacs-store"} 0.96' in metrics


def test_s4_certificate_expiry_is_a_metric_not_an_outage() -> None:
    async def scenario():
        estate = Estate()
        estate.service("patient-portal").apply_faults(Faults(certificate_days_left=5))
        return await estate.get("patient-portal"), await estate.metrics("patient-portal")

    response, metrics = run(scenario())
    assert response.status_code == 200
    assert 'certificate_expiry_days{component="patient-portal"} 5.0' in metrics


def test_s6_slow_sso_becomes_auth_errors_everywhere_downstream() -> None:
    """S6: sso slower than its callers' timeout; every dependant reports auth errors."""
    slow_auth = {c: {"DEPENDENCY_TIMEOUT_S": "0.2"} for c in APPS}

    async def scenario():
        estate = Estate(slow_auth)
        estate.service("sso").apply_faults(Faults(extra_latency_ms=500))
        codes = {c: (await estate.get(c)).status_code for c in ("ehr-api", "lis", "pacs")}
        return codes, await estate.metrics("lis")

    codes, metrics = run(scenario())
    assert codes == {"ehr-api": 502, "lis": 502, "pacs": 502}
    assert 'auth_upstream_errors_total{component="lis"} 1.0' in metrics


# --- admin boundary ----------------------------------------------------------------


def test_fault_toggles_need_the_admin_token() -> None:
    async def scenario():
        estate = Estate()
        url = "http://pacs:8080/admin/faults"
        anonymous = await estate.client.put(url, json={"unavailable": True})
        wrong = await estate.client.put(
            url, json={"unavailable": True}, headers={"Authorization": "Bearer nope"}
        )
        ok = await estate.client.put(
            url, json={"unavailable": True}, headers={"Authorization": f"Bearer {ADMIN}"}
        )
        health = await estate.get("pacs", "/health")
        cleared = await estate.client.delete(url, headers={"Authorization": f"Bearer {ADMIN}"})
        return anonymous, wrong, ok, health, cleared

    anonymous, wrong, ok, health, cleared = run(scenario())
    assert (anonymous.status_code, wrong.status_code, ok.status_code) == (401, 401, 200)
    assert health.status_code == 503
    assert cleared.json()["unavailable"] is False


def test_router_rejects_messages_for_non_dependencies() -> None:
    async def scenario():
        estate = Estate()
        return await estate.client.post(
            "http://interface-engine:8080/messages", json={"destination": "sso"}
        )

    assert run(scenario()).status_code == 422


def test_ballast_is_resident_memory() -> None:
    service = Estate({"lis": {"BALLAST_MI": "8"}}).service("lis")
    assert len(service.ballast) == 8 * 1024 * 1024
