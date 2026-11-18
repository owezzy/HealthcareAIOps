import { Component, computed, input, signal } from '@angular/core';
import { IconComponent } from '../icon/icon.component';

/**
 * C-15: the approval outcome, announced once at the top of the approval
 * detail. The approval hash is truncated for display and expands to all 64 characters.
 */
@Component({
    selector: 'app-outcome-banner',
    imports: [IconComponent],
    template: `
        <div
            class="approval-status-banner"
            role="status"
            [attr.data-tone]="outcome() === 'rejected' ? 'deny' : null"
        >
            <app-icon
                [name]="outcome() === 'rejected' ? 'x-circle' : 'check-circle'"
                [size]="14"
            />
            {{ detail() }}
        </div>
        @if (hash(); as fullHash) {
            <div class="hash-row">
                <button
                    class="hash-value"
                    type="button"
                    [attr.aria-expanded]="expanded()"
                    [attr.aria-label]="
                        expanded()
                            ? 'Approval hash ' + fullHash
                            : 'Show full approval hash'
                    "
                    (click)="expanded.set(!expanded())"
                >
                    {{ expanded() ? fullHash : shortHash() }}
                </button>
            </div>
        }
    `,
})
export class OutcomeBannerComponent {
    readonly outcome = input.required<'executed' | 'rejected'>();
    readonly detail = input.required<string>();
    readonly hash = input<string | null>(null);

    protected readonly expanded = signal(false);
    protected readonly shortHash = computed(() => {
        const hash = this.hash() ?? '';
        return hash.length > 24
            ? `${hash.slice(0, 16)}…${hash.slice(-8)}`
            : hash;
    });
}
