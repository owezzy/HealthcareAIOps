"""Scenario contract: fault, expected signals, ground truth and correct response.

Source files: ``sim/scenarios/*.yaml``. One file drives the live demo, the
fault injector and the eval dataset, so the ground truth here is what the agent
is scored against.
"""

from pathlib import Path
from typing import Any, Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from aiops_contracts.catalogue import Catalogue
from aiops_contracts.vocabulary import (
    CatalogueAction,
    FollowUp,
    IncidentState,
    RootCauseCategory,
    Severity,
    SignalKind,
    ToolName,
    VariantKind,
)


class _Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Fault(_Contract):
    target: str
    type: RootCauseCategory
    description: str
    parameters: dict[str, Any] = Field(default_factory=dict)


class ExpectedSignal(_Contract):
    kind: SignalKind
    component: str
    description: str


class RootCause(_Contract):
    component: str
    category: RootCauseCategory


class ComponentRef(_Contract):
    component: str


class GroundTruth(_Contract):
    root_cause: RootCause
    victims: tuple[str, ...] = ()
    severity: Severity
    expected_incident_count: int = Field(ge=1)
    end_state: IncidentState
    forbidden_root_causes: tuple[ComponentRef, ...] = ()


class ActionRef(_Contract):
    action: CatalogueAction
    target: str
    params: dict[str, int | str] = Field(default_factory=dict)

    @property
    def key(self) -> tuple[CatalogueAction, str]:
        return (self.action, self.target)


class Response(_Contract):
    must_call_tools: tuple[ToolName, ...]
    acceptable_actions: tuple[ActionRef, ...] = ()
    forbidden_actions: tuple[ActionRef, ...] = ()
    escalation: str | None = None
    follow_up: FollowUp | None = None

    @model_validator(mode="after")
    def _coherent(self) -> Self:
        overlap = {a.key for a in self.acceptable_actions} & {a.key for a in self.forbidden_actions}
        if overlap:
            raise ValueError(f"actions both acceptable and forbidden: {sorted(overlap)}")
        if not self.acceptable_actions and self.escalation is None and self.follow_up is None:
            raise ValueError(
                "a scenario with no acceptable action must escalate or open a follow-up"
            )
        return self


class Variant(_Contract):
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")
    kind: VariantKind
    description: str


class Scenario(_Contract):
    id: str = Field(pattern=r"^S\d+$")
    title: str
    summary: str
    fault: Fault
    expected_signals: tuple[ExpectedSignal, ...] = Field(min_length=1)
    ground_truth: GroundTruth
    response: Response
    variants: tuple[Variant, ...] = ()

    @model_validator(mode="after")
    def _internally_consistent(self) -> Self:
        truth = self.ground_truth
        if self.fault.target != truth.root_cause.component:
            raise ValueError("fault target must be the ground-truth root cause component")
        if self.fault.type != truth.root_cause.category:
            raise ValueError("fault type must match the ground-truth root cause category")
        if truth.root_cause.component in {r.component for r in truth.forbidden_root_causes}:
            raise ValueError("root cause is also listed as forbidden")
        if truth.end_state is IncidentState.RESOLVED_WITH_PROBLEM and (
            self.response.follow_up is not FollowUp.PROBLEM
        ):
            raise ValueError("end_state resolved_with_problem requires follow_up: problem")
        variant_ids = [v.id for v in self.variants]
        if len(variant_ids) != len(set(variant_ids)):
            raise ValueError("duplicate variant id")
        return self

    def check_against(self, catalogue: Catalogue) -> list[str]:
        """Return every reference to the catalogue that is wrong (empty means valid)."""
        errors: list[str] = []

        def known(component_id: str, where: str) -> None:
            if catalogue.get(component_id) is None:
                errors.append(f"{self.id}: {where} references unknown component {component_id!r}")

        known(self.fault.target, "fault.target")
        for signal in self.expected_signals:
            known(signal.component, "expected_signals")
        for victim in self.ground_truth.victims:
            known(victim, "ground_truth.victims")
        for ref in self.ground_truth.forbidden_root_causes:
            known(ref.component, "ground_truth.forbidden_root_causes")

        blast_radius = catalogue.dependents_of(self.fault.target)
        for victim in self.ground_truth.victims:
            if victim not in blast_radius:
                errors.append(
                    f"{self.id}: victim {victim!r} is not downstream of {self.fault.target!r}"
                )

        for ref in (*self.response.acceptable_actions, *self.response.forbidden_actions):
            known(ref.target, f"response action {ref.action}")
        for ref in self.response.acceptable_actions:
            errors.extend(self._check_scaling(ref, catalogue))
        return errors

    def _check_scaling(self, ref: ActionRef, catalogue: Catalogue) -> list[str]:
        if ref.action is not CatalogueAction.SCALE_DEPLOYMENT:
            return []
        component = catalogue.get(ref.target)
        replicas = ref.params.get("replicas")
        if component is None or component.scaling is None:
            return [f"{self.id}: {ref.target!r} has no scaling range in the catalogue"]
        if not isinstance(replicas, int):
            return [f"{self.id}: scale_deployment on {ref.target!r} needs integer params.replicas"]
        if not component.scaling.min <= replicas <= component.scaling.max:
            return [f"{self.id}: replicas {replicas} outside {ref.target!r} scaling range"]
        return []


def load_scenarios(directory: Path) -> list[Scenario]:
    scenarios = [
        Scenario.model_validate(yaml.safe_load(path.read_text()))
        for path in sorted(directory.glob("*.yaml"))
    ]
    ids = [s.id for s in scenarios]
    if len(ids) != len(set(ids)):
        raise ValueError(f"duplicate scenario ids in {directory}")
    return scenarios
