import { Component, input } from '@angular/core';

/**
 * Stand-in for a console section whose feature has not been built yet.
 * Inputs come from route data (withComponentInputBinding). Each route swaps
 * this for its real feature as the work lands (plan §12, design spec §9).
 */
@Component({
    selector: 'app-feature-placeholder-page',
    template: `
        <h1 class="text-2xl font-semibold text-ops-text">{{ heading() }}</h1>
        <p class="mt-2 max-w-prose text-ops-text-2">{{ summary() }}</p>
        <p class="mt-4 font-mono text-sm text-ops-text-3">
            Arrives in {{ arrives() }}.
        </p>
    `,
})
export class FeaturePlaceholderPage {
    readonly heading = input.required<string>();
    readonly summary = input.required<string>();
    readonly arrives = input.required<string>();
}
