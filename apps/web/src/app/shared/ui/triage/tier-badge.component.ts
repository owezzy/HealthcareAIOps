import { Component, computed, input } from '@angular/core';
import { ClinicalTier } from 'app/shared/models/domain.models';

/** Tier wording from plan §3.1 (design spec §7 row 3). */
const LABELS: Record<ClinicalTier, string> = {
    1: 'Tier 1 · clinical',
    2: 'Tier 2 · workaround exists',
    3: 'Tier 3 · non-clinical',
};

/** C-02: neutral by design. Tier is context, not urgency; infra sits outside the ladder. */
@Component({
    selector: 'app-tier-badge',
    template: `
        <span
            class="tier"
            [attr.data-tier]="tier() === 'infra' ? 'infra' : null"
        >
            <span class="tier-code">{{ code() }}</span
            >{{ label() }}
        </span>
    `,
})
export class TierBadgeComponent {
    readonly tier = input.required<ClinicalTier | 'infra'>();
    protected readonly code = computed(() =>
        this.tier() === 'infra' ? '—' : `T${this.tier()}`
    );
    protected readonly label = computed(() => {
        const tier = this.tier();
        return tier === 'infra' ? 'Infra' : LABELS[tier];
    });
}
