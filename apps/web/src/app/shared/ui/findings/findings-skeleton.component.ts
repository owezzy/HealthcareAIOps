import { Component, input } from '@angular/core';

/**
 * C-08: while findings stream, show labelled skeletons. The action card is
 * withheld until the fact set commits, so no action is offered on partial evidence.
 */
@Component({
    selector: 'app-findings-skeleton',
    template: `
        <div class="grid gap-2" role="status" aria-live="polite">
            <span class="ai-stream" style="color: var(--accent)">
                streaming · {{ committed() }} of {{ total() }} facts committed
            </span>
            @for (row of rows; track row) {
                <div
                    class="skeleton"
                    [style.height.px]="14"
                    [style.width.%]="row"
                ></div>
            }
            <span class="mini-pill"
                >action withheld until evidence commits</span
            >
        </div>
    `,
})
export class FindingsSkeletonComponent {
    readonly committed = input.required<number>();
    readonly total = input.required<number>();
    protected readonly rows = [92, 78, 64];
}
