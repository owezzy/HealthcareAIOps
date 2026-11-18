"""The correlation rule: pure and deterministic (ADR-0005). The LLM never groups alerts.

An alert joins an open incident when its component is related to the
incident's root through the catalogue's dependency and hosting graph:

- the alert's component is the root, or downstream of it: it is a victim;
- the root is downstream of the alert's component: the alert is closer to
  the cause, so the incident is re-rooted to it (alerts can arrive in any
  order, as S6's shuffled variant does).

Victims can alert before their cause. Sibling victims (lis and pacs, both on
node-2) first open separate incidents; when the cause's alert arrives, every
open incident it explains is merged into one.

Otherwise the alert opens a new incident. Alerts without a component label
cannot be placed in the topology, so each opens its own incident.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

from aiops_contracts.catalogue import Catalogue

#: An incident stops attracting new alerts this long after its last one.
CORRELATION_WINDOW = timedelta(minutes=15)


@dataclass(frozen=True)
class OpenIncident:
    id: int
    root_component: str | None
    last_alert_at: datetime


@dataclass(frozen=True)
class Attach:
    incident_id: int
    #: Set when the alert is upstream of the current root and becomes the new root.
    new_root: str | None = None
    #: Other open incidents this alert explains; fold them into incident_id.
    merge: tuple[int, ...] = ()


@dataclass(frozen=True)
class Open:
    root_component: str | None


Decision = Attach | Open


def correlate(
    component: str | None,
    alert_at: datetime,
    open_incidents: list[OpenIncident],
    catalogue: Catalogue,
    window: timedelta = CORRELATION_WINDOW,
) -> Decision:
    if component is None or catalogue.get(component) is None:
        return Open(component)
    recent_first = sorted(
        (
            i
            for i in open_incidents
            if i.root_component is not None and alert_at - i.last_alert_at <= window
        ),
        key=lambda i: i.last_alert_at,
        reverse=True,
    )
    below = catalogue.dependents_of(component)
    # Incidents whose root is this component or upstream of it: the alert is a victim.
    explained_by = [
        i
        for i in recent_first
        if i.root_component == component or component in catalogue.dependents_of(i.root_component)
    ]
    # Incidents whose root is downstream of this component: the alert is their cause.
    explains = [i for i in recent_first if i.root_component in below]

    if explained_by:
        target = explained_by[0]
        return Attach(target.id, merge=tuple(i.id for i in explains if i.id != target.id))
    if explains:
        target, *rest = explains
        return Attach(target.id, new_root=component, merge=tuple(i.id for i in rest))
    return Open(component)
