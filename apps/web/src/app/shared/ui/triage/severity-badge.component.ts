import { Component, computed, input } from '@angular/core';
import { Severity } from 'app/shared/models/domain.models';
import { IconComponent, IconName } from '../icon/icon.component';

const LABELS: Record<Severity, string> = {
    critical: 'Critical',
    high: 'High',
    medium: 'Medium',
    low: 'Low',
};

/** C-01: distinct glyph per level plus the word, so it survives greyscale and colour blindness. */
@Component({
    selector: 'app-severity-badge',
    imports: [IconComponent],
    template: `
        <span class="sev" [attr.data-sev]="severity()">
            <app-icon [name]="icon()" [size]="12" />{{ label() }}
        </span>
    `,
})
export class SeverityBadgeComponent {
    readonly severity = input.required<Severity>();
    protected readonly label = computed(() => LABELS[this.severity()]);
    protected readonly icon = computed<IconName>(
        () => `sev-${this.severity()}`
    );
}
