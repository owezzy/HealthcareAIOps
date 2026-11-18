import { Component, computed, input } from '@angular/core';
import { IncidentState } from 'app/shared/models/domain.models';
import { IconComponent, IconName } from '../icon/icon.component';

type StatusKey = IncidentState | 'rejected';

const STATUS: Record<
    StatusKey,
    { label: string; icon: IconName; tone: string | null }
> = {
    open: { label: 'Open', icon: 'circle', tone: null },
    investigating: {
        label: 'Investigating',
        icon: 'search',
        tone: 'investigating',
    },
    awaiting_approval: {
        label: 'Awaiting approval',
        icon: 'lock',
        tone: 'awaiting',
    },
    mitigating: { label: 'Mitigating', icon: 'wrench', tone: 'investigating' },
    mitigated: { label: 'Mitigated', icon: 'shield-check', tone: 'mitigated' },
    resolved: { label: 'Resolved', icon: 'check-circle', tone: 'resolved' },
    resolved_with_problem: {
        label: 'Resolved · problem open',
        icon: 'check-circle',
        tone: 'resolved',
    },
    rejected: { label: 'Rejected', icon: 'x-circle', tone: 'rejected' },
};

/** C-03: pill shape for human workflow state. Only "Awaiting approval" is amber. */
@Component({
    selector: 'app-status-pill',
    imports: [IconComponent],
    template: `
        <span class="status" [attr.data-status]="status().tone">
            <app-icon [name]="status().icon" [size]="12" />{{ status().label }}
        </span>
    `,
})
export class StatusPillComponent {
    readonly state = input.required<StatusKey>();
    protected readonly status = computed(() => STATUS[this.state()]);
}
