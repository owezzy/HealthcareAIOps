import { Component, input, output } from '@angular/core';
import { EvidenceRef, Hypothesis } from 'app/shared/models/domain.models';
import { ConfidencePillComponent } from '../evidence/confidence-pill.component';
import { EvidenceChipComponent } from '../evidence/evidence-chip.component';

/**
 * C-11: outlined card with a confidence pill. Supporting and contradicting
 * evidence always show as two columns, even when empty: silence is information.
 * Weak (low-confidence) hypotheses stay visible with their counter-evidence.
 */
@Component({
    selector: 'app-hypothesis-card',
    imports: [ConfidencePillComponent, EvidenceChipComponent],
    template: `
        <article
            class="hypo"
            [attr.data-tone]="hypothesis().confidence === 'low' ? 'weak' : null"
        >
            <div class="hypo-head">
                <span class="hypo-tag">HYPOTHESIS {{ rank() }}</span>
                <app-confidence-pill [level]="hypothesis().confidence" />
            </div>
            <p>
                <span class="mono">{{ hypothesis().component }}</span> ·
                <span class="mono">{{ hypothesis().category }}</span
                >: {{ hypothesis().statement }}
            </p>
            <div class="hypo-ev">
                <div>
                    <span
                        class="mini-label"
                        [attr.data-tone]="
                            hypothesis().supporting.length ? 'ok' : null
                        "
                    >
                        Supporting{{
                            hypothesis().supporting.length
                                ? ' · ' + hypothesis().supporting.length
                                : ''
                        }}
                    </span>
                    @if (hypothesis().supporting.length) {
                        <div class="evidence-list">
                            @for (
                                ref of hypothesis().supporting;
                                track ref.id
                            ) {
                                <app-evidence-chip
                                    [evidence]="ref"
                                    [showSource]="false"
                                    (open)="evidenceOpen.emit($event)"
                                />
                            }
                        </div>
                    } @else {
                        <p class="sm dim">None recorded.</p>
                    }
                </div>
                <div>
                    <span
                        class="mini-label"
                        [attr.data-tone]="
                            hypothesis().contradicting.length ? 'bad' : null
                        "
                    >
                        Contradicting{{
                            hypothesis().contradicting.length
                                ? ' · ' + hypothesis().contradicting.length
                                : ''
                        }}
                    </span>
                    @if (hypothesis().contradicting.length) {
                        <div class="evidence-list">
                            @for (
                                ref of hypothesis().contradicting;
                                track ref.id
                            ) {
                                <app-evidence-chip
                                    [evidence]="ref"
                                    (open)="evidenceOpen.emit($event)"
                                />
                            }
                        </div>
                    } @else {
                        <p class="sm dim">None recorded.</p>
                    }
                </div>
            </div>
        </article>
    `,
})
export class HypothesisCardComponent {
    readonly hypothesis = input.required<Hypothesis>();
    readonly rank = input.required<number>();
    readonly evidenceOpen = output<EvidenceRef>();
}
