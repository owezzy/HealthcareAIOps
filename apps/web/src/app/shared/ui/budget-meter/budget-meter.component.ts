import { Component, computed, input } from '@angular/core';
import { BudgetState } from 'app/core/session/session.models';

/**
 * C-17: daily LLM spend against its cap. At 100% the console enters Replay mode.
 * Unknown spend (unpriced model, unmetered call, API unreachable) says so
 * instead of showing $0.00.
 */
@Component({
    selector: 'app-budget-meter',
    host: {
        role: 'meter',
        'aria-label': 'LLM budget',
        'aria-valuemin': '0',
        '[attr.aria-valuemax]': 'capUsd()',
        '[attr.aria-valuenow]': 'spentUsd()',
        '[attr.aria-valuetext]': 'label()',
    },
    template: `
        <span class="budget-label">LLM budget</span>
        <span class="budget-track" aria-hidden="true">
            <span
                class="budget-fill"
                [attr.data-tone]="state()"
                [style.width.%]="fillPercent()"
            ></span>
        </span>
        <span class="budget-value">{{ label() }}</span>
    `,
    styleUrl: './budget-meter.component.css',
})
export class BudgetMeterComponent {
    readonly spentUsd = input.required<number | null>();
    readonly capUsd = input.required<number>();
    readonly ratio = input.required<number>();
    readonly state = input.required<BudgetState>();

    protected readonly fillPercent = computed(() =>
        this.state() === 'unknown' ? 100 : this.ratio() * 100
    );
    protected readonly label = computed(() => {
        const spent = this.spentUsd();
        const cap = `$${this.capUsd().toFixed(2)}`;
        return spent === null
            ? `unknown / ${cap}`
            : `$${spent.toFixed(2)} / ${cap}`;
    });
}
