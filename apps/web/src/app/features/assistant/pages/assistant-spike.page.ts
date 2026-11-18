import { Component } from '@angular/core';
import { CopilotChat } from '@copilotkit/angular';

/**
 * ADR-0004 spike: proves Angular -> copilot-runtime -> LangGraph agent over AG-UI.
 * Replaced by the incident-scoped assistant panel (docs/design/frontend-design.md §4.1).
 */
@Component({
    selector: 'app-assistant-spike-page',
    imports: [CopilotChat],
    template: `
        <main class="flex h-screen flex-col gap-4 p-6">
            <header>
                <h1 class="text-xl font-semibold">
                    CopilotKit spike (ADR-0004)
                </h1>
                <p class="text-secondary">
                    Angular → copilot-runtime (/api/copilotkit) → LangGraph
                    agent over AG-UI
                </p>
            </header>
            <copilot-chat
                class="min-h-0 flex-1 overflow-hidden rounded border"
            />
        </main>
    `,
})
export class AssistantSpikePage {}
