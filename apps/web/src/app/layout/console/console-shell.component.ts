import { Component, inject, signal } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { DemoRole } from 'app/core/session/session.models';
import { SessionStore } from 'app/core/session/session.store';
import { BudgetMeterComponent } from 'app/shared/ui/budget-meter/budget-meter.component';
import { IconComponent, IconName } from 'app/shared/ui/icon/icon.component';
import { RoleSwitcherComponent } from 'app/shared/ui/role-switcher/role-switcher.component';

interface NavItem {
    path: string;
    label: string;
    icon: IconName;
}

/** Primary navigation, in the order of docs/design/frontend-design.md §3. */
const NAV_ITEMS: readonly NavItem[] = [
    { path: '/incidents', label: 'Incidents', icon: 'incidents' },
    { path: '/approvals', label: 'Approvals', icon: 'approvals' },
    { path: '/problems', label: 'Problems & Changes', icon: 'problems' },
    { path: '/scenarios', label: 'Scenarios', icon: 'scenarios' },
    { path: '/evals', label: 'Evals', icon: 'evals' },
    { path: '/audit', label: 'Audit', icon: 'audit' },
];

/**
 * Console shell: sidebar, top bar (env badge, budget meter, role switcher,
 * theme toggle), persistent status banners and the feature outlet.
 */
@Component({
    selector: 'app-console-shell',
    imports: [
        RouterOutlet,
        RouterLink,
        RouterLinkActive,
        IconComponent,
        BudgetMeterComponent,
        RoleSwitcherComponent,
    ],
    host: {
        class: 'app',
        '[class.nav-open]': 'navOpen()',
        '(document:keydown.escape)': 'navOpen.set(false)',
    },
    templateUrl: './console-shell.component.html',
    styleUrl: './console-shell.component.css',
})
export class ConsoleShellComponent {
    protected readonly session = inject(SessionStore);
    protected readonly navItems = NAV_ITEMS;
    protected readonly navOpen = signal(false);

    protected setRole(role: DemoRole): void {
        this.session.setRole(role);
    }
}
