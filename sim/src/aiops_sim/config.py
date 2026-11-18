"""What one demo service is: its component, its dependencies and its tuning.

Dependencies come from sim/services.yaml, so the estate's call graph is the
catalogue's dependency graph. Tuning comes from environment variables, which
the fault injector changes through real Kubernetes rollouts.
"""

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from aiops_contracts.catalogue import Catalogue, load_catalogue
from aiops_contracts.vocabulary import ComponentKind

DEFAULT_CATALOGUE = Path("sim/services.yaml")
AUTH_COMPONENT = "sso"
#: Components that queue and route messages instead of serving them inline.
ROUTERS = frozenset({"interface-engine"})


@dataclass(frozen=True)
class ServiceConfig:
    component_id: str
    #: Applications this service calls over HTTP on every request.
    app_dependencies: tuple[str, ...]
    #: A database it holds a connection pool to (simulated in-process).
    database: str | None
    #: A storage volume it writes to (simulated in-process).
    volume: str | None
    version: str = "v1.0.0"
    db_pool_size: int = 50
    db_query_ms: int = 20
    work_cpu_ms: int = 2
    ballast_mi: int = 0
    dependency_timeout_s: float = 2.0
    #: Base URL pattern for calling another component, e.g. http://{id}:8080
    url_pattern: str = "http://{id}:8080"

    @property
    def is_router(self) -> bool:
        return self.component_id in ROUTERS

    def url(self, component_id: str) -> str:
        return self.url_pattern.format(id=component_id)


def build_config(
    component_id: str, catalogue: Catalogue, env: Mapping[str, str] = os.environ
) -> ServiceConfig:
    component = catalogue.get(component_id)
    if component is None or component.kind is not ComponentKind.APPLICATION:
        raise ValueError(f"{component_id!r} is not an application in the catalogue")

    def kind_of(dep: str) -> ComponentKind:
        found = catalogue.get(dep)
        assert found is not None  # the catalogue validates its own references
        return found.kind

    apps = tuple(d for d in component.depends_on if kind_of(d) is ComponentKind.APPLICATION)
    databases = [d for d in component.depends_on if kind_of(d) is ComponentKind.DATABASE]
    volumes = [d for d in component.depends_on if kind_of(d) is ComponentKind.VOLUME]

    def number(name: str, default: float) -> float:
        value = env.get(name)
        return float(value) if value not in (None, "") else default

    return ServiceConfig(
        component_id=component_id,
        app_dependencies=apps,
        database=databases[0] if databases else None,
        volume=volumes[0] if volumes else None,
        version=env.get("APP_VERSION", "v1.0.0"),
        db_pool_size=int(number("DB_POOL_SIZE", 50)),
        db_query_ms=int(number("DB_QUERY_MS", 20)),
        work_cpu_ms=int(number("WORK_CPU_MS", 2)),
        ballast_mi=int(number("BALLAST_MI", 0)),
        dependency_timeout_s=number("DEPENDENCY_TIMEOUT_S", 2.0),
        url_pattern=env.get("PEER_URL_PATTERN", "http://{id}:8080"),
    )


def config_from_env(env: Mapping[str, str] = os.environ) -> ServiceConfig:
    catalogue = load_catalogue(Path(env.get("AIOPS_CATALOGUE", str(DEFAULT_CATALOGUE))))
    return build_config(env["COMPONENT_ID"], catalogue, env)
