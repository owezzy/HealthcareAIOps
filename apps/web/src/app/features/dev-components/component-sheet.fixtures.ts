import {
    ActionProposal,
    Fact,
    Hypothesis,
    InjectionFlag,
} from 'app/shared/models/domain.models';

/**
 * INC-1042 "Lab results delayed" sample (scenario S2), used only by the
 * /dev/components sheet. Real screens read the API; never import this elsewhere.
 */
export const SAMPLE_FACTS: Fact[] = [
    {
        statement: 'LIS pods restarted 6 times in 10 min with OOMKilled.',
        evidence: [{ id: 'ev_19c2', source: 'k8s_event' }],
    },
    {
        statement:
            'Interface engine queue rose from 40 to 1,240 starting 09:06.',
        evidence: [{ id: 'ev_7f3a', source: 'metric' }],
    },
];

export const SAMPLE_HYPOTHESES: Hypothesis[] = [
    {
        component: 'lis',
        category: 'resource_exhaustion',
        statement:
            'memory exhaustion; interface-engine is a downstream victim.',
        confidence: 'high',
        supporting: [{ id: 'ev_19c2' }, { id: 'ev_7f3a' }, { id: 'ev_2b10' }],
        contradicting: [],
    },
    {
        component: 'interface-engine',
        category: 'bad_config_change',
        statement: 'misconfiguration.',
        confidence: 'low',
        supporting: [],
        contradicting: [{ id: 'ev_44de', source: 'config_diff' }],
    },
];

export const SAMPLE_INJECTION: InjectionFlag = {
    evidence: { id: 'ev_9a01', source: 'log' },
    summary:
        'Log line instructed a restart of all services. Guardrail flagged it, ignored it, excluded it from tools.',
    detectedAt: '2026-11-17T09:16:03Z',
};

export const SAMPLE_PROPOSAL: ActionProposal = {
    action: 'restart_deployment',
    target: 'lis',
    params: {},
    rationale:
        'Memory exhaustion is causing OOMKilled restarts; a rollout restart clears crashed pods and re-queues workers.',
    risk: 'medium',
    expectedOutcome:
        'Queue drains within 5 min; LIS 503 rate returns below 1%.',
    rollback: 'None needed; restart is stateless.',
    followUp: 'Open Problem PRB-208 for the lis memory limit.',
    evidence: [{ id: 'ev_19c2' }, { id: 'ev_7f3a' }, { id: 'ev_2b10' }],
};

export const SAMPLE_APPROVAL_HASH =
    '9f2c4e1a7b0d63f58a1c2e4b6d8f0a1c3e5b7d9f1a3c5e7b9d1f3a5c71e4d7b9f';
