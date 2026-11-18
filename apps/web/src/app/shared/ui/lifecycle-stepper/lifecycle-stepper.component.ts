import { Component, computed, input } from '@angular/core';
import { IncidentState } from 'app/shared/models/domain.models';
import { IconComponent } from '../icon/icon.component';

const STEPS: { state: IncidentState; label: string }[] = [
    { state: 'open', label: 'Open' },
    { state: 'investigating', label: 'Investigating' },
    { state: 'awaiting_approval', label: 'Awaiting approval' },
    { state: 'mitigating', label: 'Mitigating' },
    { state: 'mitigated', label: 'Mitigated' },
    { state: 'resolved', label: 'Resolved' },
];

/**
 * C-05: one rail, six fixed states. Done steps show a check, the current step
 * is ringed (aria-current="step"), future steps are numbered. "Resolved with
 * problem" ends on Resolved and names the follow-up (design spec §7 row 2).
 */
@Component({
    selector: 'app-lifecycle-stepper',
    imports: [IconComponent],
    template: `
        <ol
            class="stepper"
            [attr.aria-label]="'Incident status: ' + currentLabel()"
        >
            @for (step of steps(); track step.state; let last = $last) {
                <li
                    class="step"
                    [attr.data-state]="
                        step.status === 'future' ? null : step.status
                    "
                    [attr.aria-current]="
                        step.status === 'current' ? 'step' : null
                    "
                >
                    <span class="step-dot">
                        @if (step.status === 'future') {
                            <span class="num">{{ step.number }}</span>
                        } @else if (
                            step.status === 'current' &&
                            step.state === 'awaiting_approval'
                        ) {
                            <app-icon name="lock" [size]="11" />
                        } @else {
                            <app-icon name="check" [size]="11" />
                        }
                    </span>
                    {{ step.label }}
                </li>
                @if (!last) {
                    <li
                        class="step-line"
                        role="presentation"
                        aria-hidden="true"
                    ></li>
                }
            }
        </ol>
    `,
})
export class LifecycleStepperComponent {
    readonly state = input.required<IncidentState>();
    /** e.g. "Problem PRB-208"; shown on the last step for resolved_with_problem. */
    readonly followUp = input<string | null>(null);

    protected readonly steps = computed(() => {
        const state = this.state();
        const current = state === 'resolved_with_problem' ? 'resolved' : state;
        const currentIndex = STEPS.findIndex((step) => step.state === current);
        return STEPS.map((step, index) => ({
            ...step,
            number: index + 1,
            label:
                step.state === 'resolved' &&
                state === 'resolved_with_problem' &&
                this.followUp()
                    ? `Resolved · ${this.followUp()}`
                    : step.label,
            status:
                index < currentIndex
                    ? 'done'
                    : index === currentIndex
                      ? 'current'
                      : 'future',
        }));
    });

    protected readonly currentLabel = computed(
        () =>
            this.steps().find((step) => step.status === 'current')?.label ?? ''
    );
}
