/**
 * Demo roles (plan §7.3, ADR-0007). Switching role changes permission gates,
 * never data. Will be generated from the API's OpenAPI schema once auth lands.
 */
export type DemoRole = 'viewer' | 'operator' | 'approver';

export interface RoleOption {
    role: DemoRole;
    label: string;
    description: string;
}

/** What each role can and cannot do, shown in the role switcher (C-18). */
export const ROLE_OPTIONS: readonly RoleOption[] = [
    {
        role: 'viewer',
        label: 'Viewer',
        description: 'Read-only. Cannot approve anything.',
    },
    {
        role: 'operator',
        label: 'Operator',
        description: 'Can investigate and request actions. Cannot approve.',
    },
    {
        role: 'approver',
        label: 'Approver',
        description: 'Can grant or reject infrastructure actions.',
    },
];

export type Theme = 'dark' | 'light';

/** Agent availability as last observed; 'unknown' until the first health check. */
export type AgentStatus = 'unknown' | 'up' | 'down';

/** Mirrors aiops_contracts.usage.BudgetState. */
export type BudgetState = 'ok' | 'warn' | 'exhausted' | 'unknown';

/** Today's LLM spend as the console shows it (GET /api/budget/today). */
export interface LlmBudget {
    /** null when spend is unknown (unpriced model or a call that reported no usage). */
    spentUsd: number | null;
    capUsd: number;
    /** Model calls today, and the daily call cap that bounds unknown spend. */
    calls: number;
    callCap: number;
    state: BudgetState;
}

/** Wire shape of aiops_contracts.usage.BudgetStatus. */
export interface BudgetStatusResponse {
    day: string;
    cap_usd: number;
    call_cap: number;
    spent_usd: number | null;
    state: BudgetState;
    exhausted_by: 'spend' | 'calls' | null;
    calls: number;
    unmetered_calls: number;
}
