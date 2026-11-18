import { Component, input, output } from '@angular/core';
import { EvidenceRef, Fact } from 'app/shared/models/domain.models';
import { EvidenceChipComponent } from '../evidence/evidence-chip.component';

/** C-10: observed, not inferred. Solid card with its own evidence row and no confidence pill. */
@Component({
    selector: 'app-fact-row',
    imports: [EvidenceChipComponent],
    template: `
        <div class="fact">
            <span class="fact-tag">FACT</span>
            <div class="fact-body">
                <p>{{ fact().statement }}</p>
                <div class="evidence-list">
                    @for (ref of fact().evidence; track ref.id) {
                        <app-evidence-chip
                            [evidence]="ref"
                            (open)="evidenceOpen.emit($event)"
                        />
                    }
                </div>
            </div>
        </div>
    `,
})
export class FactRowComponent {
    readonly fact = input.required<Fact>();
    readonly evidenceOpen = output<EvidenceRef>();
}
