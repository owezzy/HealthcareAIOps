import { CdkMenu, CdkMenuItemRadio, CdkMenuTrigger } from '@angular/cdk/menu';
import { ConnectedPosition } from '@angular/cdk/overlay';
import { Component, computed, model } from '@angular/core';
import { DemoRole, ROLE_OPTIONS } from 'app/core/session/session.models';
import { IconComponent } from '../icon/icon.component';

/**
 * C-18: demo role switcher. Each option says what the role can and cannot do;
 * switching changes permission gates, never data.
 */
@Component({
    selector: 'app-role-switcher',
    imports: [CdkMenuTrigger, CdkMenu, CdkMenuItemRadio, IconComponent],
    template: `
        <button
            class="role-btn"
            type="button"
            [cdkMenuTriggerFor]="menu"
            [cdkMenuPosition]="positions"
            [attr.aria-label]="
                'Demo role: ' + current().label + '. Change role'
            "
        >
            <span class="role-meta">
                <span class="role-word">Role</span>
                <span class="role-name">{{ current().label }}</span>
            </span>
            <app-icon name="chevron-down" [size]="14" />
        </button>

        <ng-template #menu>
            <div class="menu" cdkMenu aria-label="Switch demo role">
                @for (option of options; track option.role) {
                    <button
                        class="menu-item"
                        type="button"
                        cdkMenuItemRadio
                        [cdkMenuItemChecked]="option.role === role()"
                        (cdkMenuItemTriggered)="role.set(option.role)"
                    >
                        <strong>
                            {{ option.label }}
                            @if (option.role === role()) {
                                <app-icon
                                    class="check"
                                    name="check"
                                    [size]="13"
                                />
                            }
                        </strong>
                        <span>{{ option.description }}</span>
                    </button>
                }
            </div>
        </ng-template>
    `,
    styleUrl: './role-switcher.component.css',
})
export class RoleSwitcherComponent {
    readonly role = model.required<DemoRole>();

    protected readonly options = ROLE_OPTIONS;
    protected readonly current = computed(
        () =>
            ROLE_OPTIONS.find((option) => option.role === this.role()) ??
            ROLE_OPTIONS[0]
    );
    protected readonly positions: ConnectedPosition[] = [
        {
            originX: 'end',
            originY: 'bottom',
            overlayX: 'end',
            overlayY: 'top',
            offsetY: 6,
        },
    ];
}
