/**
 * Wire shape of aiops_contracts.findings.Findings (snake_case, as the API
 * serves it) and the mapping to the view models in domain.models.ts.
 *
 * Keep in step with packages/contracts/src/aiops_contracts/findings.py until
 * these types are generated from the API's OpenAPI schema.
 */
import {
    ActionProposal,
    CatalogueAction,
    Confidence,
    EvidenceRef,
    EvidenceSource,
    Fact,
    Hypothesis,
    InjectionFlag,
    Risk,
} from './domain.models';

/** Mirrors aiops_contracts.vocabulary.RootCauseCategory. */
export type RootCauseCategory =
    | 'bad_config_change'
    | 'resource_exhaustion'
    | 'capacity'
    | 'certificate'
    | 'infrastructure_fault'
    | 'dependency_degradation'
    | 'unknown';

export interface EvidenceWire {
    id: string;
    source: EvidenceSource;
    ref: string;
    observed_at: string;
    summary: string;
}

export interface FactWire {
    statement: string;
    evidence_ids: string[];
}

export interface HypothesisWire {
    component: string;
    category: RootCauseCategory;
    statement: string;
    confidence: Confidence;
    supporting_evidence: string[];
    contradicting_evidence: string[];
}

export interface ActionProposalWire {
    action: CatalogueAction;
    target: string;
    replicas: number | null;
    rationale: string;
    risk: Risk;
    expected_outcome: string;
    rollback: string | null;
    follow_up: string | null;
    evidence_ids: string[];
}

export interface FindingsWire {
    incident_id: string;
    summary: string;
    evidence: EvidenceWire[];
    confirmed_facts: FactWire[];
    hypotheses: HypothesisWire[];
    root_cause: HypothesisWire | null;
    clinical_impact: string;
    missing_information: string[];
    suspected_injection: string[];
    proposals: ActionProposalWire[];
    escalation: string | null;
}

/** Findings as the console renders them: evidence IDs resolved to typed chips. */
export interface FindingsView {
    incidentId: string;
    summary: string;
    facts: Fact[];
    hypotheses: Hypothesis[];
    rootCause: Hypothesis | null;
    clinicalImpact: string;
    missingInformation: string[];
    injections: InjectionFlag[];
    proposals: ActionProposal[];
    escalation: string | null;
}

/** The view shows action parameters as key/value pairs; replicas is the only one today. */
function actionParams(proposal: ActionProposalWire): ActionProposal['params'] {
    const params: ActionProposal['params'] = {};
    if (proposal.replicas !== null) {
        params['replicas'] = proposal.replicas;
    }
    return params;
}

export function toFindingsView(wire: FindingsWire): FindingsView {
    const evidence = new Map(wire.evidence.map((e) => [e.id, e]));
    const ref = (id: string): EvidenceRef => ({
        id,
        source: evidence.get(id)?.source,
    });
    const refs = (ids: string[]): EvidenceRef[] => ids.map(ref);
    const hypothesis = (h: HypothesisWire): Hypothesis => ({
        component: h.component,
        category: h.category,
        statement: h.statement,
        confidence: h.confidence,
        supporting: refs(h.supporting_evidence),
        contradicting: refs(h.contradicting_evidence),
    });

    return {
        incidentId: wire.incident_id,
        summary: wire.summary,
        facts: wire.confirmed_facts.map((f) => ({
            statement: f.statement,
            evidence: refs(f.evidence_ids),
        })),
        hypotheses: wire.hypotheses.map(hypothesis),
        rootCause: wire.root_cause ? hypothesis(wire.root_cause) : null,
        clinicalImpact: wire.clinical_impact,
        missingInformation: wire.missing_information,
        injections: wire.suspected_injection.map((id) => ({
            evidence: ref(id),
            summary: evidence.get(id)?.summary ?? '',
            detectedAt: evidence.get(id)?.observed_at ?? '',
        })),
        proposals: wire.proposals.map((p) => ({
            action: p.action,
            target: p.target,
            params: actionParams(p),
            rationale: p.rationale,
            risk: p.risk,
            expectedOutcome: p.expected_outcome,
            rollback: p.rollback,
            followUp: p.follow_up,
            evidence: refs(p.evidence_ids),
        })),
        escalation: wire.escalation,
    };
}
