import { HttpClient } from '@angular/common/http';
import { DOCUMENT, computed, effect, inject } from '@angular/core';
import {
    patchState,
    signalStore,
    withComputed,
    withHooks,
    withMethods,
    withState,
} from '@ngrx/signals';
import { rxMethod } from '@ngrx/signals/rxjs-interop';
import {
    catchError,
    interval,
    map,
    of,
    pipe,
    startWith,
    switchMap,
} from 'rxjs';
import {
    AgentStatus,
    BudgetStatusResponse,
    DemoRole,
    LlmBudget,
    Theme,
} from './session.models';

/**
 * Console-wide session state: demo role, theme, LLM budget, agent status
 * (docs/design/frontend-design.md §3, ADR-0010).
 *
 * Role and theme are per-viewer conveniences kept in localStorage. The budget
 * is polled from the API (ADR-0008); it reads "unknown" until the first answer
 * and whenever the API cannot say what has been spent.
 */
interface SessionState {
    role: DemoRole;
    theme: Theme;
    budget: LlmBudget;
    agentStatus: AgentStatus;
}

const STORAGE_KEY = 'aiops.session';
const BUDGET_URL = '/api/budget/today';
const BUDGET_POLL_MS = 30_000;

const initialState: SessionState = {
    role: 'approver',
    theme: 'dark',
    budget: {
        spentUsd: null,
        capUsd: 5,
        calls: 0,
        callCap: 300,
        state: 'unknown',
    },
    agentStatus: 'unknown',
};

export const SessionStore = signalStore(
    { providedIn: 'root' },
    withState(initialState),
    withComputed(({ role, budget }) => ({
        /** How close the nearer limit is: spend against its cap, or calls against theirs. */
        budgetRatio: computed(() => {
            const { spentUsd, capUsd, calls, callCap } = budget();
            const spend =
                spentUsd === null || capUsd <= 0 ? 0 : spentUsd / capUsd;
            const callShare = callCap <= 0 ? 0 : calls / callCap;
            return Math.min(Math.max(spend, callShare), 1);
        }),
        /** Budget exhausted: agent tools stop, recorded runs are shown (§6). */
        replayMode: computed(() => budget().state === 'exhausted'),
        canRequestActions: computed(() => role() !== 'viewer'),
        canApprove: computed(() => role() === 'approver'),
    })),
    withMethods((store, http = inject(HttpClient)) => ({
        setRole(role: DemoRole): void {
            patchState(store, { role });
        },
        toggleTheme(): void {
            patchState(store, {
                theme: store.theme() === 'dark' ? 'light' : 'dark',
            });
        },
        setAgentStatus(agentStatus: AgentStatus): void {
            patchState(store, { agentStatus });
        },
        /** Refreshes the budget on every emission of the trigger. */
        pollBudget: rxMethod<unknown>(
            pipe(
                switchMap(() =>
                    http.get<BudgetStatusResponse>(BUDGET_URL).pipe(
                        map(
                            (status): LlmBudget => ({
                                spentUsd: status.spent_usd,
                                capUsd: status.cap_usd,
                                calls: status.calls,
                                callCap: status.call_cap,
                                state: status.state,
                            })
                        ),
                        // API unreachable: spend is unknown, never assumed to be zero.
                        catchError(() =>
                            of<LlmBudget>({
                                ...store.budget(),
                                spentUsd: null,
                                state: 'unknown',
                            })
                        )
                    )
                ),
                map((budget) => patchState(store, { budget }))
            )
        ),
    })),
    withHooks((store) => {
        const document = inject(DOCUMENT);
        return {
            onInit(): void {
                patchState(store, readPreferences());
                store.pollBudget(interval(BUDGET_POLL_MS).pipe(startWith(0)));

                effect(() => {
                    const theme = store.theme();
                    document.documentElement.dataset['theme'] = theme;
                    // Fuse/Material components key off a scheme class on <body>.
                    document.body.classList.toggle('dark', theme === 'dark');
                    document.body.classList.toggle('light', theme === 'light');
                });

                effect(() =>
                    writePreferences({
                        role: store.role(),
                        theme: store.theme(),
                    })
                );
            },
        };
    })
);

type Preferences = Pick<SessionState, 'role' | 'theme'>;

function readPreferences(): Partial<Preferences> {
    try {
        const raw = localStorage.getItem(STORAGE_KEY);
        if (!raw) return {};
        const parsed: unknown = JSON.parse(raw);
        if (typeof parsed !== 'object' || parsed === null) return {};
        const { role, theme } = parsed as Record<string, unknown>;
        return {
            ...(role === 'viewer' || role === 'operator' || role === 'approver'
                ? { role }
                : {}),
            ...(theme === 'dark' || theme === 'light' ? { theme } : {}),
        };
    } catch {
        return {};
    }
}

function writePreferences(preferences: Preferences): void {
    try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(preferences));
    } catch {
        // Storage unavailable (private mode, blocked): preferences stay in memory.
    }
}
