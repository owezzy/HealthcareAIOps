import { KeyValuePipe } from '@angular/common';
import { Component, computed, input, output, signal } from '@angular/core';
import { DemoRole, ROLE_OPTIONS } from 'app/core/session/session.models';
import {
    ActionProposal,
    Approval,
    EvidenceRef,
} from 'app/shared/models/domain.models';
import { EvidenceChipComponent } from '../evidence/evidence-chip.component';
import { IconComponent } from '../icon/icon.component';
import { ApprovalCountdownComponent } from './approval-countdown.component';
import { RoleNoteComponent } from './role-note.component';

/**
 * C-13: the only accent-tinted card. Inert until a human with the Approver
 * role approves it; never hides the rollback or follow-up to look confident.
 * Backend authorization is authoritative: this only reflects it (plan §7).
 */
@Component({
    selector: 'app-action-card',
    imports: [
        EvidenceChipComponent,
        IconComponent,
        ApprovalCountdownComponent,
        RoleNoteComponent,
        KeyValuePipe,
    ],
    template: `
        <section class="action-card" [attr.aria-labelledby]="titleId()">
            <div class="action-head">
                <span class="find-head" [id]="titleId()"
                    ><app-icon name="wrench" [size]="13" />Recommended
                    action</span
                >
                <span class="spacer"></span>
                <span class="risk" [attr.data-risk]="proposal().risk">
                    <app-icon name="shield" [size]="12" />Risk ·
                    {{ proposal().risk }}
                </span>
                <app-approval-countdown
                    [expiresAt]="approval().expiresAt"
                    (expired)="expired.set(true)"
                />
            </div>
            <div class="action-body">
                <div class="action-mainline">
                    <span class="action-name">{{ proposal().action }}</span>
                    <span class="action-target">
                        on <span class="svc">{{ proposal().target }}</span>
                        @for (
                            param of proposal().params | keyvalue;
                            track param.key
                        ) {
                            · {{ param.key }} {{ param.value }}
                        }
                    </span>
                </div>
                <dl class="kv-grid">
                    <dt>Rationale</dt>
                    <dd>{{ proposal().rationale }}</dd>
                    <dt>Expected</dt>
                    <dd>{{ proposal().expectedOutcome }}</dd>
                    <dt>Rollback</dt>
                    <dd>
                        {{ proposal().rollback ?? 'No rollback available.' }}
                    </dd>
                    <dt>Follow-up</dt>
                    <dd>{{ proposal().followUp ?? 'None.' }}</dd>
                    <dt>Evidence</dt>
                    <dd>
                        <div class="evidence-list">
                            @for (ref of proposal().evidence; track ref.id) {
                                <app-evidence-chip
                                    [evidence]="ref"
                                    [showSource]="false"
                                    (open)="evidenceOpen.emit($event)"
                                />
                            }
                        </div>
                    </dd>
                </dl>
                <div class="action-footer">
                    <button
                        class="btn btn-primary"
                        type="button"
                        [attr.aria-disabled]="!canDecide() || null"
                        (click)="canDecide() && approve.emit(approval())"
                    >
                        <app-icon name="shield-check" [size]="14" />Approve
                        &amp; execute
                    </button>
                    <button
                        class="btn"
                        type="button"
                        (click)="review.emit(approval())"
                    >
                        Review approval record
                    </button>
                    <span class="push"></span>
                    <span class="mono xs dim">{{ approval().id }}</span>
                </div>
                @if (expired()) {
                    <app-role-note tone="deny"
                        >This approval expired. The agent must re-request
                        it.</app-role-note
                    >
                } @else if (role() !== 'approver') {
                    <app-role-note
                        [tone]="role() === 'viewer' ? 'deny' : 'info'"
                    >
                        You are viewing as <strong>{{ roleLabel() }}</strong
                        >. Approval requires an Approver.
                    </app-role-note>
                }
            </div>
        </section>
    `,
})
export class ActionCardComponent {
    readonly proposal = input.required<ActionProposal>();
    readonly approval = input.required<Approval>();
    readonly role = input.required<DemoRole>();

    readonly approve = output<Approval>();
    readonly review = output<Approval>();
    readonly evidenceOpen = output<EvidenceRef>();

    protected readonly expired = signal(false);
    protected readonly canDecide = computed(
        () => this.role() === 'approver' && !this.expired()
    );
    protected readonly titleId = computed(() => `action-${this.approval().id}`);
    protected readonly roleLabel = computed(
        () =>
            ROLE_OPTIONS.find((option) => option.role === this.role())?.label ??
            this.role()
    );
}
