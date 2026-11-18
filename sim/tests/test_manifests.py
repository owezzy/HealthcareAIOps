"""The committed estate manifests are exactly what the catalogue generates."""

from pathlib import Path

import yaml

from aiops_contracts.catalogue import load_catalogue
from aiops_sim.manifests import render

ROOT = Path(__file__).resolve().parents[2]
CATALOGUE = load_catalogue(ROOT / "sim/services.yaml")


def test_committed_manifests_match_the_catalogue() -> None:
    committed = (ROOT / "deploy/estate/estate.yaml").read_text()
    assert committed == render(CATALOGUE), (
        "deploy/estate/estate.yaml is stale: uv run python -m aiops_sim.manifests "
        "> deploy/estate/estate.yaml"
    )


def test_placement_follows_hosted_on() -> None:
    deployments = {
        d["metadata"]["name"]: d["spec"]["template"]["spec"]
        for d in yaml.safe_load_all(render(CATALOGUE))
        if d and d["kind"] == "Deployment"
    }
    on_node2 = {
        c.id for c in CATALOGUE.components if c.hosted_on == "node-2" and c.id in deployments
    }
    for name, spec in deployments.items():
        keys = {t["key"] for t in spec["tolerations"]}
        assert ("aiops.io/estate" in keys) == (name in on_node2), name
        assert {"node.kubernetes.io/not-ready", "node.kubernetes.io/unreachable"} <= keys
        assert all(
            t.get("tolerationSeconds") == 30
            for t in spec["tolerations"]
            if t["key"].startswith("node.kubernetes.io/")
        )
        assert spec["containers"][0]["resources"]["limits"]["memory"]
