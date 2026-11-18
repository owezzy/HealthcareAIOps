import { Component, inject, signal } from '@angular/core';
import { SessionStore } from 'app/core/session/session.store';
import { EvidenceRef } from 'app/shared/models/domain.models';
import { ActionCardComponent } from 'app/shared/ui/approval/action-card.component';
import { ApprovalCountdownComponent } from 'app/shared/ui/approval/approval-countdown.component';
import { OutcomeBannerComponent } from 'app/shared/ui/approval/outcome-banner.component';
import { RoleNoteComponent } from 'app/shared/ui/approval/role-note.component';
import { ConfidencePillComponent } from 'app/shared/ui/evidence/confidence-pill.component';
import { EvidenceChipComponent } from 'app/shared/ui/evidence/evidence-chip.component';
import { FactRowComponent } from 'app/shared/ui/findings/fact-row.component';
import { FindingsSkeletonComponent } from 'app/shared/ui/findings/findings-skeleton.component';
import {
    InjectionNoticeComponent,
    MissingInfoComponent,
} from 'app/shared/ui/findings/guardrail-notices.component';
import { HypothesisCardComponent } from 'app/shared/ui/findings/hypothesis-card.component';
import { ProvenanceHeaderComponent } from 'app/shared/ui/findings/provenance-header.component';
import { LifecycleStepperComponent } from 'app/shared/ui/lifecycle-stepper/lifecycle-stepper.component';
import { SeverityBadgeComponent } from 'app/shared/ui/triage/severity-badge.component';
import { StatusPillComponent } from 'app/shared/ui/triage/status-pill.component';
import { TierBadgeComponent } from 'app/shared/ui/triage/tier-badge.component';
import {
    SAMPLE_APPROVAL_HASH,
    SAMPLE_FACTS,
    SAMPLE_HYPOTHESES,
    SAMPLE_INJECTION,
    SAMPLE_PROPOSAL,
} from './component-sheet.fixtures';

/**
 * Living component sheet (design spec §5, §9 step 2): every shared component
 * with INC-1042 sample data. Mirrors docs/design/mockups/component-sheet.html
 * and doubles as a visual regression page. Switch roles in the top bar to see gating.
 */
@Component({
    selector: 'app-component-sheet-page',
    imports: [
        SeverityBadgeComponent,
        TierBadgeComponent,
        StatusPillComponent,
        LifecycleStepperComponent,
        EvidenceChipComponent,
        ConfidencePillComponent,
        FindingsSkeletonComponent,
        ProvenanceHeaderComponent,
        FactRowComponent,
        HypothesisCardComponent,
        MissingInfoComponent,
        InjectionNoticeComponent,
        ActionCardComponent,
        ApprovalCountdownComponent,
        OutcomeBannerComponent,
        RoleNoteComponent,
    ],
    templateUrl: './component-sheet.page.html',
    styles: `
        section {
            display: grid;
            gap: 12px;
            margin-bottom: 28px;
        }
        h2 {
            font-size: 13px;
            font-weight: 600;
        }
        .row {
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            gap: 8px;
        }
        .code {
            font-family: var(--mono);
            font-size: 10px;
            color: var(--text-3);
        }
        .grid-2 {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
            gap: 12px;
        }
        .stack {
            display: grid;
            gap: 8px;
            align-content: start;
        }
    `,
})
export class ComponentSheetPage {
    protected readonly session = inject(SessionStore);

    protected readonly facts = SAMPLE_FACTS;
    protected readonly hypotheses = SAMPLE_HYPOTHESES;
    protected readonly injection = SAMPLE_INJECTION;
    protected readonly proposal = SAMPLE_PROPOSAL;
    protected readonly approvalHash = SAMPLE_APPROVAL_HASH;

    // Expiry is relative to page load so the countdowns are live.
    private readonly loadedAt = Date.now();
    protected readonly approval = {
        id: 'APR-77',
        expiresAt: new Date(this.loadedAt + 12 * 60_000 + 40_000).toISOString(),
    };
    protected readonly nearlyExpired = new Date(
        this.loadedAt + 48_000
    ).toISOString();

    protected readonly lastEvent = signal('none yet');

    protected onEvidence(ref: EvidenceRef): void {
        this.lastEvent.set(`open evidence ${ref.id}`);
    }
}
