/**
 * Domain view models shared by UI components.
 *
 * Mirrors packages/contracts (aiops_contracts.vocabulary) and the Findings
 * schema in docs/explanation/healthcare-aiops-plan.md §6.3. Replace with types generated
 * from the API's OpenAPI schema once the API serves them; do not let the two drift.
 */

export type Severity = 'critical' | 'high' | 'medium' | 'low';

export type ClinicalTier = 1 | 2 | 3;

export type IncidentState =
    | 'open'
    | 'investigating'
    | 'awaiting_approval'
    | 'mitigating'
    | 'mitigated'
    | 'resolved'
    | 'resolved_with_problem';

export type Confidence = 'low' | 'medium' | 'high';

export type Risk = 'low' | 'medium' | 'high';

export type EvidenceSource =
    | 'metric'
    | 'log'
    | 'alert'
    | 'deploy'
    | 'k8s_event'
    | 'config_diff'
    | 'runbook'
    | 'topology'
    | 'incident';

export type CatalogueAction =
    | 'restart_deployment'
    | 'rollback_deployment'
    | 'scale_deployment';

/** A citation of one evidence item, as shown on chips. */
export interface EvidenceRef {
    id: string;
    source?: EvidenceSource;
}

export interface Fact {
    statement: string;
    evidence: EvidenceRef[];
}

export interface Hypothesis {
    component: string;
    category: string;
    statement: string;
    confidence: Confidence;
    supporting: EvidenceRef[];
    contradicting: EvidenceRef[];
}

export interface ActionProposal {
    action: CatalogueAction;
    target: string;
    params: Record<string, string | number>;
    rationale: string;
    risk: Risk;
    expectedOutcome: string;
    rollback: string | null;
    followUp: string | null;
    evidence: EvidenceRef[];
}

export interface Approval {
    id: string;
    /** ISO-8601 server expiry; countdowns derive from this, never from local state. */
    expiresAt: string;
}

export interface InjectionFlag {
    evidence: EvidenceRef;
    summary: string;
    detectedAt: string;
}
