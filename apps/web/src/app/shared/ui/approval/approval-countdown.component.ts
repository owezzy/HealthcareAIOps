import {
    Component,
    DestroyRef,
    computed,
    effect,
    inject,
    input,
    output,
    signal,
} from '@angular/core';
import { IconComponent } from '../icon/icon.component';

const ONE_MINUTE_MS = 60_000;

/**
 * C-14: time left on an approval, always derived from the server's expiresAt
 * (plan §7.2) so two approvers never disagree on the deadline. Amber by default,
 * critical under one minute, "re-request required" once expired. Screen readers
 * hear thresholds only, not every tick.
 */
@Component({
    selector: 'app-approval-countdown',
    imports: [IconComponent],
    template: `
        @if (remainingMs() > 0) {
            <span
                class="countdown"
                [attr.data-tone]="remainingMs() < oneMinute ? 'warn' : null"
            >
                <app-icon name="clock" [size]="12" />
                <span class="sr-only">expires in</span>
                <span class="countdown-value">{{ display() }}</span>
            </span>
        } @else {
            <span class="mini-pill">expired → re-request required</span>
        }
        <span class="sr-only" aria-live="polite">{{ announcement() }}</span>
    `,
})
export class ApprovalCountdownComponent {
    /** ISO-8601 server expiry. */
    readonly expiresAt = input.required<string>();
    readonly expired = output<void>();

    protected readonly oneMinute = ONE_MINUTE_MS;
    private readonly now = signal(Date.now());

    protected readonly remainingMs = computed(() =>
        Math.max(0, Date.parse(this.expiresAt()) - this.now())
    );

    protected readonly display = computed(() => {
        const totalSeconds = Math.ceil(this.remainingMs() / 1000);
        const minutes = Math.floor(totalSeconds / 60);
        const seconds = totalSeconds % 60;
        return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
    });

    protected readonly announcement = computed(() => {
        const ms = this.remainingMs();
        if (ms === 0) return 'Approval expired. Re-request required.';
        if (ms < ONE_MINUTE_MS) return 'Less than one minute left to approve.';
        return '';
    });

    constructor() {
        const timer = setInterval(() => this.now.set(Date.now()), 1000);
        inject(DestroyRef).onDestroy(() => clearInterval(timer));

        let announcedExpiry = false;
        effect(() => {
            if (this.remainingMs() === 0 && !announcedExpiry) {
                announcedExpiry = true;
                this.expired.emit();
            }
        });
    }
}
