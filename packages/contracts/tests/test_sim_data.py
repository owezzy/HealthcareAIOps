"""Validates the real sim/ data files and the contract rules that guard them."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from aiops_contracts.catalogue import Catalogue, load_catalogue
from aiops_contracts.scenarios import Scenario, load_scenarios

SIM = Path(__file__).resolve().parents[3] / "sim"


@pytest.fixture(scope="module")
def catalogue() -> Catalogue:
    return load_catalogue(SIM / "services.yaml")


@pytest.fixture(scope="module")
def scenarios() -> list[Scenario]:
    return load_scenarios(SIM / "scenarios")


def test_catalogue_has_the_six_planned_applications(catalogue: Catalogue) -> None:
    apps = {c.id for c in catalogue.components if c.kind == "application"}
    assert apps == {"sso", "ehr-api", "interface-engine", "lis", "pacs", "patient-portal"}


def test_all_six_scenarios_load(scenarios: list[Scenario]) -> None:
    assert [s.id for s in scenarios] == ["S1", "S2", "S3", "S4", "S5", "S6"]


def test_scenarios_reference_the_catalogue_consistently(
    scenarios: list[Scenario], catalogue: Catalogue
) -> None:
    errors = [e for s in scenarios for e in s.check_against(catalogue)]
    assert errors == []


def test_blast_radius_is_computed_from_dependencies_and_hosting(catalogue: Catalogue) -> None:
    assert catalogue.dependents_of("lis") == {"interface-engine"}
    assert catalogue.dependents_of("node-2") >= {"interface-engine", "lis", "pacs"}
    assert catalogue.dependents_of("sso") >= {"ehr-api", "lis", "pacs", "patient-portal"}


def test_dependency_cycle_is_rejected() -> None:
    def component(cid: str, deps: list[str]) -> dict:
        return {
            "id": cid,
            "name": cid,
            "kind": "application",
            "tier": 1,
            "owner_team": "t",
            "depends_on": deps,
        }

    with pytest.raises(ValidationError, match="dependency cycle"):
        Catalogue.model_validate(
            {"version": 1, "components": [component("a", ["b"]), component("b", ["a"])]}
        )


def test_action_cannot_be_both_acceptable_and_forbidden(scenarios: list[Scenario]) -> None:
    raw = scenarios[0].model_dump(mode="json")
    raw["response"]["forbidden_actions"].append(raw["response"]["acceptable_actions"][0])
    with pytest.raises(ValidationError, match="both acceptable and forbidden"):
        Scenario.model_validate(raw)


def test_scale_outside_catalogue_range_is_reported(
    scenarios: list[Scenario], catalogue: Catalogue
) -> None:
    raw = next(s for s in scenarios if s.id == "S6").model_dump(mode="json")
    raw["response"]["acceptable_actions"][0]["params"]["replicas"] = 20
    errors = Scenario.model_validate(raw).check_against(catalogue)
    assert any("outside 'sso' scaling range" in e for e in errors)
