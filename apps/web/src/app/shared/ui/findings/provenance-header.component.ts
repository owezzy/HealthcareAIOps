import { DatePipe } from '@angular/common';
import { Component, input } from '@angular/core';
import { IconComponent } from '../icon/icon.component';

/**
 * C-09: every AI panel names its model and prompt version. "streamed" is the
 * run's timestamp, not the view's; re-opening an incident does not reset it.
 */
@Component({
    selector: 'app-provenance-header',
    imports: [IconComponent, DatePipe],
    template: `
        <div class="ai-head">
            <span class="ai-badge"
                ><app-icon name="sparkle" [size]="12" />AI findings</span
            >
            <span class="model-tag"
                >{{ model() }} · prompt {{ promptVersion() }}</span
            >
            <span class="spacer"></span>
            @if (streamedAt(); as at) {
                <span class="ai-stream">streamed {{ at | date: 'HH:mm' }}</span>
            } @else {
                <span class="ai-stream">streaming…</span>
            }
        </div>
    `,
})
export class ProvenanceHeaderComponent {
    readonly model = input.required<string>();
    readonly promptVersion = input.required<string>();
    readonly streamedAt = input<string | null>(null);
}
