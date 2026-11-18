import { Component, input, output } from '@angular/core';
import { EvidenceRef } from 'app/shared/models/domain.models';

/** C-06: stable monospace evidence ID; opens the evidence drawer. */
@Component({
    selector: 'app-evidence-chip',
    template: `
        <button
            class="evidence-chip"
            type="button"
            [attr.aria-expanded]="expanded() || null"
            [attr.aria-label]="
                'Open evidence ' +
                evidence().id +
                (evidence().source ? ', ' + evidence().source : '')
            "
            (click)="open.emit(evidence())"
        >
            {{ evidence().id }}
            @if (showSource() && evidence().source) {
                <span class="ev-type">· {{ evidence().source }}</span>
            }
        </button>
    `,
})
export class EvidenceChipComponent {
    readonly evidence = input.required<EvidenceRef>();
    readonly showSource = input(true);
    readonly expanded = input(false);
    readonly open = output<EvidenceRef>();
}
