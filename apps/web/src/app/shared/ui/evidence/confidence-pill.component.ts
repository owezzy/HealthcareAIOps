import { Component, input } from '@angular/core';
import { Confidence } from 'app/shared/models/domain.models';

/** C-07: three bars plus the word. Low is deliberately quiet, not alarming. */
@Component({
    selector: 'app-confidence-pill',
    template: `
        <span class="conf" [attr.data-conf]="level()">
            <span class="conf-bars" aria-hidden="true"
                ><i></i><i></i><i></i
            ></span>
            {{
                level() === 'high'
                    ? 'High'
                    : level() === 'medium'
                      ? 'Medium'
                      : 'Low'
            }}
            confidence
        </span>
    `,
})
export class ConfidencePillComponent {
    readonly level = input.required<Confidence>();
}
