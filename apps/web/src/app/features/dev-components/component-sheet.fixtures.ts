import {
    FindingsWire,
    toFindingsView,
} from 'app/shared/models/findings.contract';

/**
 * INC-1042 "Lab results delayed" (scenario S2) in the API's wire format,
 * mapped to view models exactly as real screens will do. Used only by the
 * /dev/components sheet; real screens read the API.
 */
const S2_FINDINGS: FindingsWire = {
    incident_id: 'INC-1042',
    summary: 'Lab results delayed: lis is crash-looping on memory.',
    evidence: [
        {
            id: 'ev_19c2',
            source: 'k8s_event',
            ref: 'events lis 10m',
            observed_at: '2026-11-17T09:12:00Z',
            summary: '6 OOMKilled restarts in 10 min',
        },
        {
            id: 'ev_7f3a',
            source: 'metric',
            ref: 'queue_depth{svc="interface-engine"}',
            observed_at: '2026-11-17T09:14:00Z',
            summary: 'Queue rose from 40 to 1,240',
        },
        {
            id: 'ev_2b10',
            source: 'metric',
            ref: 'http_errors{svc="lis",code="503"}',
            observed_at: '2026-11-17T09:14:30Z',
            summary: 'LIS 503 rate at 38%',
        },
        {
            id: 'ev_44de',
            source: 'config_diff',
            ref: 'interface-engine config 24h',
            observed_at: '2026-11-17T09:15:00Z',
            summary: 'No interface-engine changes in 24 h',
        },
        {
            id: 'ev_9a01',
            source: 'log',
            ref: 'loki interface-engine 09:16',
            observed_at: '2026-11-17T09:16:03Z',
            summary:
                'Log line instructed a restart of all services. Guardrail flagged it, ignored it, excluded it from tools.',
        },
    ],
    confirmed_facts: [
        {
            statement: 'LIS pods restarted 6 times in 10 min with OOMKilled.',
            evidence_ids: ['ev_19c2'],
        },
        {
            statement:
                'Interface engine queue rose from 40 to 1,240 starting 09:06.',
            evidence_ids: ['ev_7f3a'],
        },
    ],
    hypotheses: [
        {
            component: 'lis',
            category: 'resource_exhaustion',
            statement:
                'memory exhaustion; interface-engine is a downstream victim.',
            confidence: 'high',
            supporting_evidence: ['ev_19c2', 'ev_7f3a', 'ev_2b10'],
            contradicting_evidence: [],
        },
        {
            component: 'interface-engine',
            category: 'bad_config_change',
            statement: 'misconfiguration.',
            confidence: 'low',
            supporting_evidence: [],
            contradicting_evidence: ['ev_44de'],
        },
    ],
    root_cause_rank: 1,
    clinical_impact: 'Tier 1: Pathology and wards wait for lab results.',
    missing_information: ['No heap profile available for lis.'],
    suspected_injection: ['ev_9a01'],
    proposals: [
        {
            action: 'restart_deployment',
            target: 'lis',
            replicas: null,
            rationale:
                'Memory exhaustion is causing OOMKilled restarts; a rollout restart clears crashed pods and re-queues workers.',
            risk: 'medium',
            expected_outcome:
                'Queue drains within 5 min; LIS 503 rate returns below 1%.',
            rollback: 'None needed; restart is stateless.',
            follow_up: 'Open Problem PRB-208 for the lis memory limit.',
            evidence_ids: ['ev_19c2', 'ev_7f3a', 'ev_2b10'],
        },
    ],
    escalation: null,
};

export const SAMPLE_FINDINGS = toFindingsView(S2_FINDINGS);

export const SAMPLE_APPROVAL_HASH =
    '9f2c4e1a7b0d63f58a1c2e4b6d8f0a1c3e5b7d9f1a3c5e7b9d1f3a5c71e4d7b9f';
