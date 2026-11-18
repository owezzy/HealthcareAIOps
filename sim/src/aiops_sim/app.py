"""One demo service. Run: COMPONENT_ID=lis uvicorn aiops_sim.app:create_app_from_env --factory

Endpoints
  GET  /health          liveness and readiness (503 while toggled unavailable)
  GET  /work            one unit of work: call dependencies, use the pool, touch storage
  POST /messages        routers only (interface-engine): queue a message for a dependency
  GET  /metrics         Prometheus metrics
  GET|PUT|DELETE /admin/faults   admin toggles, bearer AIOPS_ESTATE_ADMIN_TOKEN
"""

import asyncio
import hmac
import json
import logging
import os
import time
from collections import deque
from contextlib import asynccontextmanager
from dataclasses import dataclass

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, Response, status
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
from pydantic import BaseModel, ConfigDict, Field

from aiops_sim.config import AUTH_COMPONENT, ServiceConfig, config_from_env

MESSAGE_TYPES = {"lis": "ORU^R01", "pacs": "ORM^O01", "ehr-api": "ADT^A08"}


class Faults(BaseModel):
    """Admin toggles for faults that would be destructive if real."""

    model_config = ConfigDict(extra="forbid")

    unavailable: bool = False
    extra_latency_ms: int = Field(default=0, ge=0, le=60_000)
    volume_used_percent: float | None = Field(default=None, ge=0, le=100)
    certificate_days_left: float | None = Field(default=None, ge=0)


class QueuedMessage(BaseModel):
    destination: str
    payload: str = ""


@dataclass
class Metrics:
    registry: CollectorRegistry
    requests: Counter
    latency: Histogram
    dependency_errors: Counter
    auth_errors: Counter
    pool_in_use: Gauge
    pool_size: Gauge
    queue_depth: Gauge
    volume_used: Gauge
    certificate_days: Gauge

    @classmethod
    def create(cls, config: ServiceConfig) -> Metrics:
        registry = CollectorRegistry()
        component = {"component": config.component_id}
        info = Gauge("app_info", "Running version", ["component", "version"], registry=registry)
        info.labels(config.component_id, config.version).set(1)
        metrics = cls(
            registry=registry,
            requests=Counter(
                "http_requests_total", "Requests served", ["component", "code"], registry=registry
            ),
            latency=Histogram(
                "http_request_duration_seconds",
                "Request latency",
                ["component"],
                registry=registry,
                buckets=(0.05, 0.1, 0.25, 0.5, 1, 2, 3, 5, 10),
            ),
            dependency_errors=Counter(
                "dependency_errors_total",
                "Failed calls to a dependency",
                ["component", "dependency"],
                registry=registry,
            ),
            auth_errors=Counter(
                "auth_upstream_errors_total",
                "Failed calls to SSO",
                ["component"],
                registry=registry,
            ),
            pool_in_use=Gauge(
                "db_pool_in_use", "Connections in use", ["component", "database"], registry=registry
            ),
            pool_size=Gauge(
                "db_pool_size", "Pool size", ["component", "database"], registry=registry
            ),
            queue_depth=Gauge(
                "queue_depth", "Messages waiting", ["component", "destination"], registry=registry
            ),
            volume_used=Gauge(
                "volume_used_ratio", "Storage used", ["component", "volume"], registry=registry
            ),
            certificate_days=Gauge(
                "certificate_expiry_days",
                "Days until the TLS certificate expires",
                ["component"],
                registry=registry,
            ),
        )
        if config.database:
            metrics.pool_size.labels(config.component_id, config.database).set(config.db_pool_size)
        metrics.certificate_days.labels(**component).set(365)
        return metrics


class JsonFormatter(logging.Formatter):
    def __init__(self, component: str) -> None:
        super().__init__()
        self.component = component

    def format(self, record: logging.LogRecord) -> str:
        return json.dumps(
            {
                "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)),
                "level": record.levelname.lower(),
                "component": self.component,
                "msg": record.getMessage(),
            }
        )


class Service:
    """The behaviour behind the endpoints, separate from HTTP for testing."""

    def __init__(self, config: ServiceConfig, client: httpx.AsyncClient, log: logging.Logger):
        self.config = config
        self.client = client
        self.log = log
        self.faults = Faults()
        self.metrics = Metrics.create(config)
        self.pool = asyncio.Semaphore(config.db_pool_size)
        self.pool_in_use = 0
        self.queues: dict[str, deque[QueuedMessage]] = {d: deque() for d in config.app_dependencies}
        self.ballast = bytearray(config.ballast_mi * 1024 * 1024)  # real working set (S2)
        for offset in range(0, len(self.ballast), 4096):
            self.ballast[offset] = 1  # touch every page so it counts as resident

    async def work(self) -> tuple[int, str]:
        if self.faults.unavailable:
            return 503, "service unavailable"
        for dependency in self.config.app_dependencies:
            if self.config.is_router:
                continue  # routers deliver through their queues
            code = await self._call(dependency)
            if code != 200:
                if dependency == AUTH_COMPONENT:
                    self.metrics.auth_errors.labels(self.config.component_id).inc()
                    self.log.warning("authentication via sso failed: upstream %s", code)
                    return 502, "auth upstream error"
                self.metrics.dependency_errors.labels(self.config.component_id, dependency).inc()
                self.log.warning("call to %s failed: %s", dependency, code)
                return 502, f"dependency {dependency} failed"
        if self.config.database and not await self._query():
            self.log.error(
                "database pool exhausted (%s connections to %s)",
                self.config.db_pool_size,
                self.config.database,
            )
            return 503, "database pool exhausted"
        if self.config.volume and (self.faults.volume_used_percent or 0) > 95:
            self.log.error("STORE failed: No space left on device (%s)", self.config.volume)
            return 507, "No space left on device"
        _burn_cpu(self.config.work_cpu_ms)
        if self.faults.extra_latency_ms:
            await asyncio.sleep(self.faults.extra_latency_ms / 1000)
        return 200, "ok"

    async def _call(self, dependency: str) -> int:
        try:
            response = await self.client.get(
                f"{self.config.url(dependency)}/work", timeout=self.config.dependency_timeout_s
            )
            return response.status_code
        except httpx.HTTPError:
            return 504

    async def _query(self) -> bool:
        assert self.config.database
        labels = (self.config.component_id, self.config.database)
        try:
            await asyncio.wait_for(self.pool.acquire(), timeout=1.0)
        except TimeoutError:
            return False
        self.pool_in_use += 1
        self.metrics.pool_in_use.labels(*labels).set(self.pool_in_use)
        try:
            await asyncio.sleep(self.config.db_query_ms / 1000)
        finally:
            self.pool_in_use -= 1
            self.metrics.pool_in_use.labels(*labels).set(self.pool_in_use)
            self.pool.release()
        return True

    def enqueue(self, message: QueuedMessage) -> None:
        if message.destination not in self.queues:
            raise ValueError(
                f"{message.destination!r} is not a dependency of {self.config.component_id}"
            )
        self.queues[message.destination].append(message)
        self._update_queue_metrics()

    async def drain_once(self) -> None:
        """Deliver the head of each queue; failures stay queued and are retried."""
        for destination, queue in self.queues.items():
            if not queue:
                continue
            code = await self._call(destination)
            if code == 200:
                queue.popleft()
            else:
                kind = MESSAGE_TYPES.get(destination, "message")
                self.log.warning(
                    "%s delivery to %s failed: %s (retrying)", kind, destination, _status_text(code)
                )
                self.metrics.dependency_errors.labels(self.config.component_id, destination).inc()
        self._update_queue_metrics()

    def _update_queue_metrics(self) -> None:
        for destination, queue in self.queues.items():
            self.metrics.queue_depth.labels(self.config.component_id, destination).set(len(queue))

    def apply_faults(self, faults: Faults) -> None:
        self.faults = faults
        component = self.config.component_id
        if self.config.volume:
            used = (faults.volume_used_percent or 0) / 100
            self.metrics.volume_used.labels(component, self.config.volume).set(used)
        days = faults.certificate_days_left
        self.metrics.certificate_days.labels(component).set(365 if days is None else days)
        self.log.info("faults set: %s", faults.model_dump(exclude_defaults=True))


def _burn_cpu(milliseconds: int) -> None:
    """Real CPU work, so a CPU limit throttles it (S6)."""
    deadline = time.perf_counter() + milliseconds / 1000
    while time.perf_counter() < deadline:
        pass


def _status_text(code: int) -> str:
    return {503: "503 Service Unavailable", 504: "504 Gateway Timeout"}.get(code, str(code))


def create_app(
    config: ServiceConfig, client: httpx.AsyncClient | None = None, admin_token: str | None = None
) -> FastAPI:
    log = logging.getLogger(f"aiops_sim.{config.component_id}")
    if not log.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter(config.component_id))
        log.addHandler(handler)
        log.setLevel(logging.INFO)
        log.propagate = False
    service = Service(config, client or httpx.AsyncClient(), log)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        drainer = asyncio.create_task(_drain_forever(service)) if config.is_router else None
        log.info("started %s %s", config.component_id, config.version)
        yield
        if drainer:
            drainer.cancel()

    app = FastAPI(title=f"demo {config.component_id}", lifespan=lifespan)
    app.state.service = service

    def require_admin(authorization: str | None = Header(default=None)) -> None:
        if not admin_token:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "admin token not configured")
        presented = (authorization or "").removeprefix("Bearer ")
        if not hmac.compare_digest(presented.encode(), admin_token.encode()):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid admin token")

    @app.get("/health")
    def health() -> Response:
        healthy = not service.faults.unavailable
        return Response("ok" if healthy else "unavailable", status_code=200 if healthy else 503)

    @app.get("/work")
    async def work() -> Response:
        started = time.perf_counter()
        code, detail = await service.work()
        service.metrics.requests.labels(config.component_id, str(code)).inc()
        service.metrics.latency.labels(config.component_id).observe(time.perf_counter() - started)
        return Response(detail, status_code=code)

    if config.is_router:

        @app.post("/messages", status_code=status.HTTP_202_ACCEPTED)
        def messages(message: QueuedMessage) -> dict[str, str]:
            try:
                service.enqueue(message)
            except ValueError as error:
                raise HTTPException(422, str(error)) from error
            return {"status": "queued"}

    @app.get("/metrics")
    def metrics() -> Response:
        return Response(generate_latest(service.metrics.registry), media_type=CONTENT_TYPE_LATEST)

    @app.get("/admin/faults", dependencies=[Depends(require_admin)])
    def get_faults() -> Faults:
        return service.faults

    @app.put("/admin/faults", dependencies=[Depends(require_admin)])
    def put_faults(faults: Faults) -> Faults:
        service.apply_faults(faults)
        return service.faults

    @app.delete("/admin/faults", dependencies=[Depends(require_admin)])
    def clear_faults() -> Faults:
        service.apply_faults(Faults())
        return service.faults

    return app


async def _drain_forever(service: Service) -> None:
    while True:
        await service.drain_once()
        await asyncio.sleep(0.1)


def create_app_from_env() -> FastAPI:
    return create_app(config_from_env(), admin_token=os.environ.get("AIOPS_ESTATE_ADMIN_TOKEN"))
