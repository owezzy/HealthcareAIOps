"""Findings contract: structural rules, catalogue rules and the repair messages."""

import json
from pathlib import Path

import pytest

from aiops_contracts.catalogue import Catalogue, load_catalogue
from aiops_contracts.findings import Findings, parse_findings

SIM = Path(__file__).resolve().parents[3] / "sim"


@pytest.fixture(scope="module")
def catalogue() -> Catalogue:
    return load_catalogue(SIM / "services.yaml")


def s2_findings() -> dict:
    """INC-1042 (scenario S2) as the agent should report it."""
    lis_oom = {
        "component": "lis",
        "category": "resource_exhaustion",
        "statement": "Memory exhaustion; interface-engine is a downstream victim.",
        "confidence": "high",
        "supporting_evidence": ["ev_19c2", "ev_7f3a"],
        "contradicting_evidence": [],
    }
    return {
        "incident_id": "INC-1042",
        "summary": "Lab results delayed: lis is crash-looping on memory.",
        "evidence": [
            {
                "id": "ev_19c2",
                "source": "k8s_event",
                "ref": "events lis 10m",
                "observed_at": "2026-11-17T09:12:00Z",
                "summary": "6 OOMKilled restarts in 10 min",
            },
            {
                "id": "ev_7f3a",
                "source": "metric",
                "ref": "queue_depth{svc=interface-engine}",
                "observed_at": "2026-11-17T09:14:00Z",
                "summary": "Queue rose from 40 to 1,240",
            },
            {
                "id": "ev_9a01",
                "source": "log",
                "ref": "loki interface-engine 09:16",
                "observed_at": "2026-11-17T09:16:03Z",
                "summary": "Line asks to restart all services",
            },
        ],
        "confirmed_facts": [
            {
                "statement": "LIS pods restarted 6 times in 10 min with OOMKilled.",
                "evidence_ids": ["ev_19c2"],
            },
        ],
        "hypotheses": [lis_oom],
        "root_cause": lis_oom,
        "clinical_impact": "Tier 1: Pathology and wards wait for lab results.",
        "missing_information": ["No heap profile for lis."],
        "suspected_injection": ["ev_9a01"],
        "proposals": [
            {
                "action": "restart_deployment",
                "target": "lis",
                "rationale": "Clear crashed pods.",
                "risk": "medium",
                "expected_outcome": "Queue drains within 5 min.",
                "rollback": None,
                "follow_up": "Open a Problem for the lis memory limit.",
                "evidence_ids": ["ev_19c2"],
            },
        ],
    }


def errors_for(raw: dict, catalogue: Catalogue) -> list[str]:
    findings, errors = parse_findings(raw, catalogue)
    assert (findings is None) == bool(errors)
    return errors


def test_valid_findings_parse_from_json(catalogue) -> None:
    findings, errors = parse_findings(json.dumps(s2_findings()), catalogue)
    assert errors == []
    assert findings.root_cause.component == "lis"


def test_fact_citing_unknown_evidence_is_rejected(catalogue) -> None:
    raw = s2_findings()
    raw["confirmed_facts"][0]["evidence_ids"] = ["ev_nope"]
    assert any("fact 1 cites unknown evidence" in e for e in errors_for(raw, catalogue))


def test_fact_without_evidence_is_rejected(catalogue) -> None:
    raw = s2_findings()
    raw["confirmed_facts"][0]["evidence_ids"] = []
    assert any("confirmed_facts.0.evidence_ids" in e for e in errors_for(raw, catalogue))


def test_hypothesis_naming_unknown_component_is_rejected(catalogue) -> None:
    raw = s2_findings()
    raw["hypotheses"][0]["component"] = "lab-mainframe"
    raw["root_cause"] = raw["hypotheses"][0]
    assert errors_for(raw, catalogue) == ["hypothesis 1 names unknown component 'lab-mainframe'"]


def test_root_cause_must_be_one_of_the_hypotheses(catalogue) -> None:
    raw = s2_findings()
    raw["root_cause"] = {**raw["hypotheses"][0], "confidence": "low"}
    assert any("root_cause must be one of the hypotheses" in e for e in errors_for(raw, catalogue))


def test_proposal_resting_on_injected_evidence_is_rejected(catalogue) -> None:
    raw = s2_findings()
    raw["proposals"][0]["evidence_ids"] = ["ev_9a01"]
    assert any("flagged as prompt injection" in e for e in errors_for(raw, catalogue))


@pytest.mark.parametrize(
    ("proposal", "message"),
    [
        ({"action": "restart_deployment", "target": "ehr-db"}, "it is a database"),
        (
            {"action": "scale_deployment", "target": "sso", "replicas": 20},
            "replicas 20 outside 'sso' scaling range",
        ),
        ({"action": "scale_deployment", "target": "sso"}, "needs replicas"),
        ({"action": "rollback_deployment", "target": "lis", "replicas": 2}, "takes no replicas"),
        ({"action": "restart_deployment", "target": "pharmacy"}, "unknown component"),
    ],
)
def test_proposals_must_be_valid_catalogue_actions(catalogue, proposal, message) -> None:
    raw = s2_findings()
    raw["proposals"][0] = {**raw["proposals"][0], **proposal}
    assert any(message in e for e in errors_for(raw, catalogue))


def test_evidence_timestamps_must_carry_a_timezone(catalogue) -> None:
    raw = s2_findings()
    raw["evidence"][0]["observed_at"] = "2026-11-17T09:12:00"
    assert any("timezone-aware" in e for e in errors_for(raw, catalogue))


def test_schema_has_no_open_maps_for_structured_output() -> None:
    """Strict structured-output modes need closed objects: no free-form dicts anywhere."""

    def walk(node: object) -> None:
        if isinstance(node, dict):
            if node.get("type") == "object":
                assert node.get("additionalProperties") is False, node.get("title")
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(Findings.model_json_schema())
