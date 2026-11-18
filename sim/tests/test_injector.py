"""Fault injector: plans come from the scenario files; one scenario at a time; exact undo."""

import json
from pathlib import Path

import httpx
import pytest

from aiops_contracts.catalogue import load_catalogue
from aiops_contracts.scenarios import load_scenarios
from aiops_sim import admin
from aiops_sim.injector import (
    InjectorError,
    apply_scenario,
    load_plans,
    plan_for,
    reset_scenario,
)

SIM = Path(__file__).resolve().parents[1]
PLANS = load_plans(SIM)
CATALOGUE = load_catalogue(SIM / "services.yaml")
SCENARIOS = {s.id: s for s in load_scenarios(SIM / "scenarios")}


class FakeCluster:
    """Records commands and keeps the namespace annotation like kubectl would."""

    def __init__(self, fail_on: str | None = None) -> None:
        self.commands: list[list[str]] = []
        self.active: str | None = None
        self.fail_on = fail_on

    def __call__(self, command: list[str]) -> str:
        if command[:3] == ["kubectl", "get", "namespace"]:
            return self.active or ""
        self.commands.append(command)
        if command[:2] == ["kubectl", "annotate"]:
            value = command[4]
            self.active = None if value.endswith("-") else value.split("=", 1)[1]
            return ""
        if self.fail_on and self.fail_on in " ".join(command):
            raise InjectorError(f"{self.fail_on} failed")
        return ""

    def faults(self) -> list[str]:
        return [" ".join(c) for c in self.commands if c[:2] != ["kubectl", "annotate"]]


def test_every_scenario_has_a_plan_and_an_undo() -> None:
    assert sorted(PLANS) == ["S1", "S2", "S3", "S4", "S5", "S6"]
    for plan in PLANS.values():
        assert plan.apply and plan.undo


@pytest.mark.parametrize(
    ("scenario", "apply", "undo"),
    [
        (
            "S1",
            "set env deployment/ehr-api DB_POOL_SIZE=5 APP_VERSION=v2.3.1",
            "set env deployment/ehr-api DB_POOL_SIZE=50 APP_VERSION=v2.3.0",
        ),
        (
            "S2",
            "set resources deployment/lis --requests=memory=96Mi --limits=memory=96Mi",
            "set resources deployment/lis --requests=memory=128Mi --limits=memory=160Mi",
        ),
        (
            "S3",
            "exec deployment/pacs -- python -m aiops_sim.admin set volume_used_percent=96",
            "exec deployment/pacs -- python -m aiops_sim.admin clear",
        ),
        (
            "S4",
            "exec deployment/patient-portal -- python -m aiops_sim.admin set "
            "certificate_days_left=5",
            "exec deployment/patient-portal -- python -m aiops_sim.admin clear",
        ),
        ("S5", "docker pause aiops-node-2", "docker unpause aiops-node-2"),
        (
            "S6",
            "set resources deployment/sso --limits=cpu=50m",
            "set resources deployment/sso --limits=cpu=250m",
        ),
    ],
)
def test_plans_follow_the_scenario_parameters(scenario, apply, undo) -> None:
    plan = PLANS[scenario]
    assert any(apply in " ".join(c) for c in plan.apply)
    assert any(undo in " ".join(c) for c in plan.undo)


def test_s6_surge_is_undone_before_the_cpu_limit() -> None:
    undo = [" ".join(c) for c in PLANS["S6"].undo]
    assert "RATE_PER_SECOND=2" in undo[0] and "cpu=250m" in undo[1]


def test_apply_then_reset_runs_the_exact_inverse() -> None:
    cluster = FakeCluster()
    apply_scenario(PLANS["S2"], cluster)
    assert cluster.active == "S2"
    assert reset_scenario(PLANS, cluster) == "S2"
    assert cluster.active is None
    assert cluster.faults() == [" ".join(c) for c in PLANS["S2"].apply + PLANS["S2"].undo]


def test_only_one_scenario_at_a_time() -> None:
    cluster = FakeCluster()
    apply_scenario(PLANS["S1"], cluster)
    with pytest.raises(InjectorError, match="S1 is active"):
        apply_scenario(PLANS["S3"], cluster)


def test_a_failed_apply_can_still_be_reset() -> None:
    cluster = FakeCluster(fail_on="set resources")
    with pytest.raises(InjectorError):
        apply_scenario(PLANS["S6"], cluster)
    assert cluster.active == "S6"  # marked before acting
    cluster.fail_on = None
    assert reset_scenario(PLANS, cluster) == "S6"


def test_reset_tolerates_a_node_that_is_already_running() -> None:
    cluster = FakeCluster()
    apply_scenario(PLANS["S5"], cluster)
    cluster.fail_on = "docker unpause"
    assert reset_scenario(PLANS, cluster) == "S5"
    assert cluster.active is None


def test_reset_with_nothing_active_does_nothing() -> None:
    cluster = FakeCluster()
    assert reset_scenario(PLANS, cluster) is None
    assert cluster.commands == []


def test_unsupported_parameters_are_refused() -> None:
    raw = SCENARIOS["S4"].model_dump(mode="json")
    raw["fault"]["parameters"]["melt_the_datacentre"] = True
    scenario = type(SCENARIOS["S4"]).model_validate(raw)
    with pytest.raises(InjectorError, match="melt_the_datacentre"):
        plan_for(scenario, CATALOGUE)


def test_only_node_2_can_be_failed() -> None:
    raw = SCENARIOS["S5"].model_dump(mode="json")
    raw["fault"]["target"] = raw["ground_truth"]["root_cause"]["component"] = "node-3"
    raw["ground_truth"]["victims"] = ["patient-portal"]
    scenario = type(SCENARIOS["S5"]).model_validate(raw)
    with pytest.raises(InjectorError, match="only node-2 is a real node"):
        plan_for(scenario, CATALOGUE)


def test_admin_cli_merges_with_current_faults_and_sends_the_token(monkeypatch, capsys) -> None:
    monkeypatch.setenv("AIOPS_ESTATE_ADMIN_TOKEN", "t0ken")
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(
            (
                request.method,
                request.headers["authorization"],
                json.loads(request.content) if request.content else None,
            )
        )
        if request.method == "GET":
            return httpx.Response(200, json={"unavailable": False, "extra_latency_ms": 250})
        return httpx.Response(200, json={})

    assert admin.main(["set", "volume_used_percent=96"], httpx.MockTransport(handler)) == 0
    method, auth, body = seen[-1]
    assert (method, auth) == ("PUT", "Bearer t0ken")
    assert body == {"unavailable": False, "extra_latency_ms": 250, "volume_used_percent": "96"}
    assert admin.main(["bogus"], httpx.MockTransport(handler)) == 2
