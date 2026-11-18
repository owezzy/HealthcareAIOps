import { Component, computed, input } from '@angular/core';
import { BudgetState } from 'app/core/session/session.models';

/**
 * C-17: today's LLM budget. The bar shows the nearer of two limits, spend
 * against its cap or calls against the call cap; at 100% the console enters
 * Replay mode. When spend is unknown (unpriced model, unmetered call, API
 * unreachable) the label shows calls against the call cap, never "$0.00".
 */
@Component({
    selector: 'app-budget-meter',
    host: {
        role: 'meter',
        'aria-label': 'LLM budget',
        'aria-valuemin': '0',
        'aria-valuemax': '100',
        '[attr.aria-valuenow]': 'percent()',
        '[attr.aria-valuetext]': 'label()',
    },
    template: `
        <span class="budget-label">LLM budget</span>
        <span class="budget-track" aria-hidden="true">
            <span
                class="budget-fill"
                [attr.data-tone]="state()"
                [style.width.%]="percent()"
            ></span>
        </span>
        <span class="budget-value">{{ label() }}</span>
    `,
    styleUrl: './budget-meter.component.css',
})
export class BudgetMeterComponent {
    readonly spentUsd = input.required<number | null>();
    readonly capUsd = input.required<number>();
    readonly calls = input.required<number>();
    readonly callCap = input.required<number>();
    /** Nearer limit as a fraction, 0 to 1 (SessionStore.budgetRatio). */
    readonly ratio = input.required<number>();
    readonly state = input.required<BudgetState>();

    protected readonly percent = computed(() => Math.round(this.ratio() * 100));
    protected readonly label = computed(() => {
        const spent = this.spentUsd();
        return spent === null
            ? `${this.calls()} / ${this.callCap()} calls`
            : `$${spent.toFixed(2)} / $${this.capUsd().toFixed(2)}`;
    });
}
