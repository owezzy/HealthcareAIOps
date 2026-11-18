"""Kubernetes manifests for the estate, generated from sim/services.yaml.

    uv run python -m aiops_sim.manifests > deploy/estate/estate.yaml

A test fails if the committed file differs from this output, so placement,
limits and tolerations can never drift from the catalogue (ADR-0013).
"""

import sys
from pathlib import Path
from typing import Any

import yaml

from aiops_contracts.catalogue import Catalogue, load_catalogue
from aiops_contracts.vocabulary import ComponentKind

NAMESPACE = "aiops-estate"
IMAGE = "healthcare-aiops-estate"  # the demo overlay maps this to GHCR
SIMULATED_NODE = "node-2"  # the only catalogue node that is a separate K3s node
ESTATE_TAINT = {
    "key": "aiops.io/estate",
    "operator": "Equal",
    "value": "only",
    "effect": "NoSchedule",
}
#: S5: leave a failed node after 30 s instead of the default 300 s.
FAST_EVICTION = [
    {
        "key": f"node.kubernetes.io/{reason}",
        "operator": "Exists",
        "effect": "NoExecute",
        "tolerationSeconds": 30,
    }
    for reason in ("not-ready", "unreachable")
]

#: Per-component tuning; each value is what a scenario's fault changes.
TUNING: dict[str, dict[str, str]] = {
    "ehr-api": {"DB_POOL_SIZE": "50", "APP_VERSION": "v2.3.0"},  # S1 rolls to v2.3.1, pool 5
    "lis": {"BALLAST_MI": "80"},  # S2 lowers the memory limit below this working set
    "sso": {"WORK_CPU_MS": "5"},  # S6 throttles CPU under a login surge
}
#: Memory request/limit in MiB. Python + FastAPI idles around 45-55 MiB.
MEMORY = {"lis": (128, 160)}
DEFAULT_MEMORY = (48, 96)
LOADGEN_MEMORY = (32, 64)


def render(catalogue: Catalogue) -> str:
    apps = [c for c in catalogue.components if c.kind is ComponentKind.APPLICATION]
    documents: list[dict[str, Any]] = [
        {"apiVersion": "v1", "kind": "Namespace", "metadata": {"name": NAMESPACE}},
        _quota(apps),
        _same_namespace_only(),
    ]
    for component in apps:
        documents += [_deployment(component.id, component.hosted_on), _service(component.id)]
    documents.append(_loadgen())
    header = (
        "# GENERATED from sim/services.yaml by `python -m aiops_sim.manifests`. "
        "Do not edit by hand.\n"
    )
    return header + "---\n".join(yaml.safe_dump(d, sort_keys=False) for d in documents)


def _quota(apps: list) -> dict[str, Any]:
    requests = sum(MEMORY.get(a.id, DEFAULT_MEMORY)[0] for a in apps) + LOADGEN_MEMORY[0]
    limits = sum(MEMORY.get(a.id, DEFAULT_MEMORY)[1] for a in apps) + LOADGEN_MEMORY[1]
    # Room for one rolling update (S1) on top of the steady state.
    return {
        "apiVersion": "v1",
        "kind": "ResourceQuota",
        "metadata": {"name": "estate", "namespace": NAMESPACE},
        "spec": {
            "hard": {
                "requests.memory": f"{requests + 64}Mi",
                "limits.memory": f"{limits + 128}Mi",
                "limits.cpu": "3",
                "pods": "12",
            }
        },
    }


def _same_namespace_only() -> dict[str, Any]:
    return {
        "apiVersion": "networking.k8s.io/v1",
        "kind": "NetworkPolicy",
        "metadata": {"name": "estate-internal", "namespace": NAMESPACE},
        "spec": {
            "podSelector": {},
            "policyTypes": ["Ingress"],
            "ingress": [{"from": [{"podSelector": {}}]}],
        },
    }


def _container(
    name: str, env: dict[str, str], memory: tuple[int, int], command: list[str] | None = None
) -> dict[str, Any]:
    container: dict[str, Any] = {
        "name": name,
        "image": IMAGE,
        "env": [{"name": k, "value": v} for k, v in env.items()],
        "resources": {
            "requests": {"cpu": "10m", "memory": f"{memory[0]}Mi"},
            "limits": {"cpu": "250m", "memory": f"{memory[1]}Mi"},
        },
        "securityContext": {"allowPrivilegeEscalation": False, "runAsNonRoot": True},
    }
    if command:
        container["command"] = command
    else:
        container["ports"] = [{"name": "http", "containerPort": 8080}]
        container["env"].append(
            {
                "name": "AIOPS_ESTATE_ADMIN_TOKEN",
                "valueFrom": {
                    "secretKeyRef": {"name": "estate-admin", "key": "token", "optional": True}
                },
            }
        )
        probe = {"httpGet": {"path": "/health", "port": "http"}, "periodSeconds": 10}
        container["readinessProbe"] = probe
        container["livenessProbe"] = {**probe, "periodSeconds": 20, "failureThreshold": 3}
    return container


def _deployment(component_id: str, hosted_on: str | None) -> dict[str, Any]:
    labels = {"app": component_id, "aiops.io/component": component_id}
    spec: dict[str, Any] = {
        "containers": [
            _container(
                component_id,
                {"COMPONENT_ID": component_id, **TUNING.get(component_id, {})},
                MEMORY.get(component_id, DEFAULT_MEMORY),
            )
        ],
        "tolerations": list(FAST_EVICTION),
    }
    if hosted_on == SIMULATED_NODE:
        spec["tolerations"].insert(0, ESTATE_TAINT)
        spec["affinity"] = {
            "nodeAffinity": {
                "preferredDuringSchedulingIgnoredDuringExecution": [
                    {
                        "weight": 100,
                        "preference": {
                            "matchExpressions": [
                                {
                                    "key": "kubernetes.io/hostname",
                                    "operator": "In",
                                    "values": [SIMULATED_NODE],
                                }
                            ]
                        },
                    }
                ]
            }
        }
    return {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {"name": component_id, "namespace": NAMESPACE, "labels": labels},
        "spec": {
            "replicas": 1,
            "selector": {"matchLabels": {"app": component_id}},
            "template": {"metadata": {"labels": labels}, "spec": spec},
        },
    }


def _service(component_id: str) -> dict[str, Any]:
    return {
        "apiVersion": "v1",
        "kind": "Service",
        "metadata": {"name": component_id, "namespace": NAMESPACE},
        "spec": {
            "selector": {"app": component_id},
            "ports": [{"name": "http", "port": 8080, "targetPort": "http"}],
        },
    }


def _loadgen() -> dict[str, Any]:
    container = _container(
        "loadgen",
        {"RATE_PER_SECOND": "2"},
        LOADGEN_MEMORY,
        command=["python", "-m", "aiops_sim.loadgen"],
    )
    return {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {"name": "loadgen", "namespace": NAMESPACE},
        "spec": {
            "replicas": 1,
            "selector": {"matchLabels": {"app": "loadgen"}},
            "template": {
                "metadata": {"labels": {"app": "loadgen"}},
                "spec": {"containers": [container], "tolerations": list(FAST_EVICTION)},
            },
        },
    }


if __name__ == "__main__":
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("sim/services.yaml")
    sys.stdout.write(render(load_catalogue(path)))
