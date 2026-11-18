"""Findings: the agent's typed output for one investigation (plan §6.3).

The agent never returns free text. It returns `Findings`, which the console
renders and the evals score. Two layers of checks guard it:

1. The model itself (Pydantic validators): every cited evidence ID exists in
   the findings' own evidence set, facts cite at least one item, the root
   cause points at an existing hypothesis, and no proposal rests on evidence flagged
   as a prompt injection.
2. `findings_errors(findings, catalogue)`: every component and action target
   exists, and every proposed action is valid for its target (ADR-0002,
   plan §6.5).

Both produce plain messages the agent gets back for its one repair attempt.
The schema avoids open-ended maps so it works with providers' strict
structured-output modes.
"""

from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from aiops_contracts.catalogue import Catalogue
from aiops_contracts.vocabulary import (
    CatalogueAction,
    Confidence,
    EvidenceSource,
    Risk,
    RootCauseCategory,
)

EVIDENCE_ID_PATTERN = r"^ev_[a-z0-9]{3,32}$"


class _Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Evidence(_Contract):
    """One observation the agent gathered through a tool. Stored, so it can be re-inspected."""

    id: str = Field(pattern=EVIDENCE_ID_PATTERN)
    source: EvidenceSource
    ref: str = Field(min_length=1, description="Query or document reference that reproduces it")
    observed_at: datetime
    summary: str = Field(min_length=1)

    @model_validator(mode="after")
    def _aware(self) -> Self:
        if self.observed_at.tzinfo is None:
            raise ValueError("observed_at must be timezone-aware")
        return self


class Fact(_Contract):
    """Observed, not inferred: carries evidence and no confidence."""

    statement: str = Field(min_length=1)
    evidence_ids: tuple[str, ...] = Field(min_length=1)


class Hypothesis(_Contract):
    component: str
    category: RootCauseCategory
    statement: str = Field(min_length=1)
    confidence: Confidence
    supporting_evidence: tuple[str, ...] = ()
    contradicting_evidence: tuple[str, ...] = ()


class ActionProposal(_Contract):
    """A catalogue action the agent recommends. Proposing never executes (ADR-0002)."""

    action: CatalogueAction
    target: str
    replicas: int | None = Field(default=None, ge=0, description="scale_deployment only")
    rationale: str = Field(min_length=1)
    risk: Risk
    expected_outcome: str = Field(min_length=1)
    rollback: str | None = None
    follow_up: str | None = None
    evidence_ids: tuple[str, ...] = Field(min_length=1)


class Findings(_Contract):
    incident_id: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    evidence: tuple[Evidence, ...]
    confirmed_facts: tuple[Fact, ...]
    hypotheses: tuple[Hypothesis, ...]
    root_cause_rank: int | None = Field(
        default=None,
        ge=1,
        description="Rank (1 = first) of the hypothesis established as the root cause; "
        "null when the root cause is not established",
    )
    clinical_impact: str = Field(min_length=1)
    missing_information: tuple[str, ...] = ()
    suspected_injection: tuple[str, ...] = Field(
        default=(), description="Evidence IDs whose content contained instructions"
    )
    proposals: tuple[ActionProposal, ...] = ()
    escalation: str | None = None

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        known = [e.id for e in self.evidence]
        if len(known) != len(set(known)):
            raise ValueError("duplicate evidence id in evidence")
        known_ids = set(known)

        def check(ids: tuple[str, ...], where: str) -> None:
            unknown = [i for i in ids if i not in known_ids]
            if unknown:
                raise ValueError(f"{where} cites unknown evidence {unknown}")

        for n, fact in enumerate(self.confirmed_facts, 1):
            check(fact.evidence_ids, f"fact {n}")
        for n, hypothesis in enumerate(self.hypotheses, 1):
            check(hypothesis.supporting_evidence, f"hypothesis {n} supporting")
            check(hypothesis.contradicting_evidence, f"hypothesis {n} contradicting")
        check(self.suspected_injection, "suspected_injection")
        for n, proposal in enumerate(self.proposals, 1):
            check(proposal.evidence_ids, f"proposal {n}")
            tainted = set(proposal.evidence_ids) & set(self.suspected_injection)
            if tainted:
                raise ValueError(
                    f"proposal {n} rests on evidence flagged as prompt injection {sorted(tainted)}"
                )
        if self.root_cause_rank is not None and self.root_cause_rank > len(self.hypotheses):
            raise ValueError(
                f"root_cause_rank {self.root_cause_rank} is not a hypothesis "
                f"(there are {len(self.hypotheses)})"
            )
        return self

    @property
    def root_cause(self) -> Hypothesis | None:
        """The hypothesis established as the root cause, if any."""
        if self.root_cause_rank is None:
            return None
        return self.hypotheses[self.root_cause_rank - 1]


def findings_errors(findings: Findings, catalogue: Catalogue) -> list[str]:
    """Problems with components and actions against the catalogue (empty means valid)."""
    errors: list[str] = []
    for n, hypothesis in enumerate(findings.hypotheses, 1):
        if catalogue.get(hypothesis.component) is None:
            errors.append(f"hypothesis {n} names unknown component {hypothesis.component!r}")
    for n, proposal in enumerate(findings.proposals, 1):
        errors.extend(
            f"proposal {n}: {problem}"
            for problem in catalogue.action_errors(
                proposal.action, proposal.target, proposal.replicas
            )
        )
    return errors


def parse_findings(raw: str | dict, catalogue: Catalogue) -> tuple[Findings | None, list[str]]:
    """Parse model output and validate it fully.

    Returns the findings (or None) and every problem found, as messages the
    agent can act on in its single repair attempt (plan §6.3).
    """
    try:
        findings = (
            Findings.model_validate_json(raw)
            if isinstance(raw, str)
            else Findings.model_validate(raw)
        )
    except ValidationError as error:
        return None, [_message(e) for e in error.errors()]
    errors = findings_errors(findings, catalogue)
    return (None, errors) if errors else (findings, [])


def _message(error: dict) -> str:
    location = ".".join(str(part) for part in error["loc"])
    return f"{location}: {error['msg']}" if location else error["msg"]
