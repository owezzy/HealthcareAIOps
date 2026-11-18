"""Component catalogue: the simulated estate, its tiers and dependency graph.

Source file: ``sim/services.yaml``.
"""

from pathlib import Path
from typing import Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from aiops_contracts.vocabulary import CatalogueAction, ClinicalTier, ComponentKind


class _Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ScalingRange(_Contract):
    min: int = Field(ge=0)
    max: int = Field(ge=1)

    @model_validator(mode="after")
    def _ordered(self) -> Self:
        if self.min > self.max:
            raise ValueError(f"scaling min {self.min} exceeds max {self.max}")
        return self


class Component(_Contract):
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")
    name: str
    kind: ComponentKind
    tier: ClinicalTier
    owner_team: str
    hosted_on: str | None = None
    depends_on: tuple[str, ...] = ()
    departments: tuple[str, ...] = ()
    scaling: ScalingRange | None = None


class Catalogue(_Contract):
    version: int
    components: tuple[Component, ...]

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        by_id: dict[str, Component] = {}
        for component in self.components:
            if component.id in by_id:
                raise ValueError(f"duplicate component id: {component.id}")
            by_id[component.id] = component

        for component in self.components:
            for dep in component.depends_on:
                if dep not in by_id:
                    raise ValueError(f"{component.id} depends on unknown component {dep}")
            if component.hosted_on is not None:
                host = by_id.get(component.hosted_on)
                if host is None or host.kind is not ComponentKind.NODE:
                    raise ValueError(f"{component.id} hosted_on must reference a node")
            if component.scaling is not None and component.kind is not ComponentKind.APPLICATION:
                raise ValueError(f"{component.id}: only applications can declare scaling")

        _reject_cycles(by_id)
        return self

    def get(self, component_id: str) -> Component | None:
        return next((c for c in self.components if c.id == component_id), None)

    def dependents_of(self, component_id: str) -> set[str]:
        """Everything that transitively depends on (or is hosted on) a component.

        This is the deterministic blast radius (plan §3.2, ADR-0005): the LLM
        explains it, it never computes it.
        """
        affected: set[str] = set()
        frontier = [component_id]
        while frontier:
            current = frontier.pop()
            for c in self.components:
                if c.id not in affected and (current in c.depends_on or c.hosted_on == current):
                    affected.add(c.id)
                    frontier.append(c.id)
        return affected

    def action_errors(
        self, action: CatalogueAction, target: str, replicas: int | None
    ) -> list[str]:
        """Why an executor action on this target is invalid (empty means valid).

        Catalogue actions operate on application deployments only (plan §6.5);
        scaling must stay inside the component's declared range.
        """
        component = self.get(target)
        if component is None:
            return [f"unknown component {target!r}"]
        if component.kind is not ComponentKind.APPLICATION:
            kind = component.kind
            return [f"{action} cannot target {target!r}: it is a {kind}, not an application"]
        if action is not CatalogueAction.SCALE_DEPLOYMENT:
            return [] if replicas is None else [f"{action} on {target!r} takes no replicas"]
        if component.scaling is None:
            return [f"{target!r} has no scaling range in the catalogue"]
        if replicas is None:
            return [f"scale_deployment on {target!r} needs replicas"]
        if not component.scaling.min <= replicas <= component.scaling.max:
            return [f"replicas {replicas} outside {target!r} scaling range"]
        return []


def _reject_cycles(by_id: dict[str, Component]) -> None:
    visiting: set[str] = set()
    done: set[str] = set()

    def visit(node: str, path: list[str]) -> None:
        if node in done:
            return
        if node in visiting:
            raise ValueError("dependency cycle: " + " -> ".join([*path, node]))
        visiting.add(node)
        for dep in by_id[node].depends_on:
            visit(dep, [*path, node])
        visiting.discard(node)
        done.add(node)

    for node in by_id:
        visit(node, [])


def load_catalogue(path: Path) -> Catalogue:
    return Catalogue.model_validate(yaml.safe_load(path.read_text()))
