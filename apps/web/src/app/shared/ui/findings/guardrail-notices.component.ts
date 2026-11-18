import { DatePipe } from '@angular/common';
import { Component, input, output } from '@angular/core';
import { EvidenceRef, InjectionFlag } from 'app/shared/models/domain.models';
import { EvidenceChipComponent } from '../evidence/evidence-chip.component';
import { IconComponent } from '../icon/icon.component';

/** C-12a: dashed border means "absent". Shown beside the findings, never as a toast. */
@Component({
    selector: 'app-missing-info',
    template: `
        <div class="missing">
            <div>
                <span class="mini-label">Missing information</span>
                @for (item of items(); track item) {
                    <p>{{ item }}</p>
                }
            </div>
            <span class="mini-pill">limits certainty</span>
        </div>
    `,
})
export class MissingInfoComponent {
    readonly items = input.required<string[]>();
}

/** C-12b: red border means "hostile input contained". The evidence stays inspectable. */
@Component({
    selector: 'app-injection-notice',
    imports: [EvidenceChipComponent, IconComponent, DatePipe],
    template: `
        <div class="injection" role="note">
            <app-icon name="shield" [size]="16" />
            <div>
                <strong>Prompt injection — treated as data</strong>
                <p>{{ flag().summary }}</p>
                <div class="evidence-list">
                    <app-evidence-chip
                        [evidence]="flag().evidence"
                        (open)="evidenceOpen.emit($event)"
                    />
                    <span class="mini-pill"
                        >detected
                        {{ flag().detectedAt | date: 'HH:mm:ss' }}</span
                    >
                </div>
            </div>
        </div>
    `,
})
export class InjectionNoticeComponent {
    readonly flag = input.required<InjectionFlag>();
    readonly evidenceOpen = output<EvidenceRef>();
}
