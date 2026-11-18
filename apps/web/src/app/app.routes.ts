import { Route } from '@angular/router';
import { ConsoleShellComponent } from 'app/layout/console/console-shell.component';

/**
 * Console routes (docs/design/frontend-design.md §3-4). Public demo: no auth
 * guard until demo authentication lands (ADR-0007). Each placeholder is
 * replaced by its feature's lazy routes as the feature is built.
 */
export const appRoutes: Route[] = [
    { path: '', pathMatch: 'full', redirectTo: 'incidents' },
    {
        path: '',
        component: ConsoleShellComponent,
        children: [
            {
                path: 'incidents',
                title: 'Incidents · Healthcare AIOps',
                loadComponent: placeholder,
                data: section(
                    'Incidents',
                    'Incident queue and the investigation workspace: timeline, correlated alerts, AI findings and blast radius.',
                    'weeks 3-7'
                ),
            },
            {
                path: 'approvals',
                title: 'Approvals · Healthcare AIOps',
                loadComponent: placeholder,
                data: section(
                    'Approvals',
                    'Pending action requests with risk, rollback, evidence and an expiry countdown. Only approvers can decide.',
                    'week 5'
                ),
            },
            {
                path: 'problems',
                title: 'Problems & Changes · Healthcare AIOps',
                loadComponent: placeholder,
                data: section(
                    'Problems & Changes',
                    'Follow-up records for causes that remain after service is restored, and drafted change requests.',
                    'week 5'
                ),
            },
            {
                path: 'scenarios',
                title: 'Scenarios · Healthcare AIOps',
                loadComponent: placeholder,
                data: section(
                    'Scenarios',
                    'Run S1-S6 against the simulated estate and follow the pipeline live.',
                    'week 7'
                ),
            },
            {
                path: 'evals',
                title: 'Evals · Healthcare AIOps',
                loadComponent: placeholder,
                data: section(
                    'Evals',
                    'Agent evaluation report: accuracy, safety, rule baseline and the three-model comparison.',
                    'week 6'
                ),
            },
            {
                path: 'audit',
                title: 'Audit · Healthcare AIOps',
                loadComponent: placeholder,
                data: section(
                    'Audit',
                    'Append-only record of every agent run, tool call, approval and execution.',
                    'week 5'
                ),
            },
            {
                path: 'dev/components',
                title: 'Components · Healthcare AIOps',
                loadComponent: () =>
                    import(
                        'app/features/dev-components/component-sheet.page'
                    ).then((m) => m.ComponentSheetPage),
            },
        ],
    },
    {
        path: 'spike/assistant',
        title: 'CopilotKit spike · Healthcare AIOps',
        loadChildren: () => import('app/features/assistant/assistant.routes'),
    },
    { path: '**', redirectTo: 'incidents' },
];

function placeholder() {
    return import('app/layout/console/feature-placeholder.page').then(
        (m) => m.FeaturePlaceholderPage
    );
}

function section(heading: string, summary: string, arrives: string) {
    return { heading, summary, arrives };
}
