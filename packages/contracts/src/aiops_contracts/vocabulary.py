"""Shared vocabulary: enums that every service, the sim and the evals agree on.

These values appear in scenario files, LLM structured output, API payloads and
eval scoring, so changing one is a contract change across the whole system.
"""

from enum import IntEnum, StrEnum


class ClinicalTier(IntEnum):
    """1 = care delivery affected within minutes; 3 = non-clinical."""

    TIER_1 = 1
    TIER_2 = 2
    TIER_3 = 3


class Severity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ComponentKind(StrEnum):
    APPLICATION = "application"
    DATABASE = "database"
    VOLUME = "volume"
    NODE = "node"


class RootCauseCategory(StrEnum):
    BAD_CONFIG_CHANGE = "bad_config_change"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    CAPACITY = "capacity"
    CERTIFICATE = "certificate"
    INFRASTRUCTURE_FAULT = "infrastructure_fault"
    DEPENDENCY_DEGRADATION = "dependency_degradation"
    UNKNOWN = "unknown"


class CatalogueAction(StrEnum):
    """The only runtime actions the executor will ever perform (plan §6.5)."""

    RESTART_DEPLOYMENT = "restart_deployment"
    ROLLBACK_DEPLOYMENT = "rollback_deployment"
    SCALE_DEPLOYMENT = "scale_deployment"


class IncidentState(StrEnum):
    """Incident lifecycle (plan §7.5)."""

    OPEN = "open"
    INVESTIGATING = "investigating"
    AWAITING_APPROVAL = "awaiting_approval"
    MITIGATING = "mitigating"
    MITIGATED = "mitigated"
    RESOLVED = "resolved"
    RESOLVED_WITH_PROBLEM = "resolved_with_problem"


class FollowUp(StrEnum):
    """ITIL record opened after an incident: a Problem (cause remains) or a Change."""

    PROBLEM = "problem"
    CHANGE = "change"


class ToolName(StrEnum):
    """MCP read tools available to the investigation agent (plan §6.4)."""

    GET_SERVICE_HEALTH = "get_service_health"
    GET_TOPOLOGY = "get_topology"
    QUERY_METRICS = "query_metrics"
    SEARCH_LOGS = "search_logs"
    GET_RECENT_CHANGES = "get_recent_changes"
    GET_K8S_EVENTS = "get_k8s_events"
    SEARCH_RUNBOOKS = "search_runbooks"
    GET_SIMILAR_INCIDENTS = "get_similar_incidents"


class SignalKind(StrEnum):
    METRIC = "metric"
    LOG = "log"
    ALERT = "alert"
    DEPLOY = "deploy"
    K8S_EVENT = "k8s_event"


class VariantKind(StrEnum):
    """Eval variant families (plan §4.1)."""

    TIMING_NOISE = "timing_noise"
    MISSING_DATA = "missing_data"
    CONFLICTING_EVIDENCE = "conflicting_evidence"
    PROMPT_INJECTION = "prompt_injection"
    POISONED_RETRIEVAL = "poisoned_retrieval"
    PERMISSION_DENIED = "permission_denied"


class EvidenceSource(StrEnum):
    """Where a piece of evidence came from (plan §6.3)."""

    METRIC = "metric"
    LOG = "log"
    ALERT = "alert"
    DEPLOY = "deploy"
    K8S_EVENT = "k8s_event"
    CONFIG_DIFF = "config_diff"
    RUNBOOK = "runbook"
    TOPOLOGY = "topology"
    INCIDENT = "incident"


class Confidence(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Risk(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
