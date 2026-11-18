import { Component, input } from '@angular/core';
import { IconComponent } from '../icon/icon.component';

/** C-16: explains a permission gate where the button lives, not in a toast. */
@Component({
    selector: 'app-role-note',
    imports: [IconComponent],
    template: `
        <div class="role-note" [attr.data-tone]="tone()">
            <app-icon
                [name]="tone() === 'deny' ? 'lock' : 'user'"
                [size]="14"
            />
            <span><ng-content /></span>
        </div>
    `,
})
export class RoleNoteComponent {
    readonly tone = input<'info' | 'deny'>('info');
}
