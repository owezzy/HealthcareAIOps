"""The pure correlation rule against the real catalogue and scenarios."""

import itertools
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from aiops_api.correlation.domain import Attach, Open, OpenIncident, correlate
from aiops_contracts.catalogue import load_catalogue
from aiops_contracts.scenarios import load_scenarios

SIM = Path(__file__).resolve().parents[3] / "sim"
CATALOGUE = load_catalogue(SIM / "services.yaml")
SCENARIOS = {s.id: s for s in load_scenarios(SIM / "scenarios")}
T0 = datetime(2026, 11, 18, 9, 0, tzinfo=UTC)


def group(components: list[str], spacing: timedelta = timedelta(seconds=10)) -> list[dict]:
    """Run alerts through the rule in order; return each incident's component set and root."""
    incidents: dict[int, dict] = {}
    for n, component in enumerate(components):
        at = T0 + n * spacing
        open_ = [OpenIncident(i, v["root"], v["last"]) for i, v in incidents.items()]
        decision = correlate(component, at, open_, CATALOGUE)
        if isinstance(decision, Open):
            incidents[max(incidents, default=-1) + 1] = {
                "root": decision.root_component,
                "components": {component},
                "last": at,
            }
        else:
            incident = incidents[decision.incident_id]
            for merged in decision.merge:
                incident["components"] |= incidents.pop(merged)["components"]
            incident["components"].add(component)
            incident["last"] = at
            if decision.new_root:
                incident["root"] = decision.new_root
    return list(incidents.values())


def alert_components(scenario_id: str) -> list[str]:
    return [s.component for s in SCENARIOS[scenario_id].expected_signals if s.kind == "alert"]


def test_s6_alert_storm_is_one_incident_rooted_at_sso_in_any_order() -> None:
    components = alert_components("S6")
    assert len(components) == 6 and "sso" in components
    for order in itertools.permutations(components):
        incidents = group(list(order))
        assert len(incidents) == 1, order
        assert incidents[0]["root"] == "sso", order


def test_s1_alerts_are_one_incident_rooted_at_ehr_api() -> None:
    incidents = group(["ehr-api", "ehr-api", "patient-portal"])
    assert [(i["root"], len(i["components"])) for i in incidents] == [("ehr-api", 2)]


def test_s5_node_failure_groups_its_hosted_services_under_the_node() -> None:
    incidents = group(["lis", "interface-engine", "pacs", "node-2"])
    assert len(incidents) == 1 and incidents[0]["root"] == "node-2"


def test_unrelated_components_open_separate_incidents() -> None:
    # pacs and ehr-api share sso as a dependency, but neither depends on the other.
    incidents = group(["pacs", "ehr-api"])
    assert sorted(i["root"] for i in incidents) == ["ehr-api", "pacs"]


def test_alerts_after_the_window_open_a_new_incident() -> None:
    incidents = group(["ehr-api", "ehr-api"], spacing=timedelta(minutes=16))
    assert len(incidents) == 2


def test_unknown_or_missing_component_opens_its_own_incident() -> None:
    open_ = [OpenIncident(1, "sso", T0)]
    assert correlate(None, T0, open_, CATALOGUE) == Open(None)
    assert correlate("mainframe", T0, open_, CATALOGUE) == Open("mainframe")


@pytest.mark.parametrize(
    ("component", "root", "expected"),
    [
        ("ehr-api", "sso", Attach(1)),  # victim of the root
        ("sso", "ehr-api", Attach(1, new_root="sso")),  # upstream: re-root
        ("lis", "node-2", Attach(1)),  # hosted on the root node
    ],
)
def test_attach_decisions(component, root, expected) -> None:
    assert correlate(component, T0, [OpenIncident(1, root, T0)], CATALOGUE) == expected


def test_cause_arriving_last_merges_the_incidents_it_explains() -> None:
    open_ = [OpenIncident(1, "lis", T0), OpenIncident(2, "pacs", T0 + timedelta(seconds=5))]
    decision = correlate("node-2", T0 + timedelta(seconds=10), open_, CATALOGUE)
    assert decision == Attach(2, new_root="node-2", merge=(1,))
