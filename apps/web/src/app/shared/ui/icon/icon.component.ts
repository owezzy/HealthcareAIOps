import { Component, computed, input } from '@angular/core';

type Shape =
    | { kind: 'path'; d: string }
    | { kind: 'circle'; cx: number; cy: number; r: number }
    | { kind: 'rect'; x: number; y: number; w: number; h: number; rx: number };

const p = (...d: string[]): Shape[] =>
    d.map((path) => ({ kind: 'path', d: path }));
const c = (cx: number, cy: number, r: number): Shape => ({
    kind: 'circle',
    cx,
    cy,
    r,
});

/** Stroke icons from the design system (docs/design/mockups/index.html symbol sprite). */
const ICONS = {
    incidents: p(
        'M10.3 3.9 2.5 17.4A2 2 0 0 0 4.2 20.4h15.6a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z',
        'M12 9v4',
        'M12 17h.01'
    ), // same glyph as sev-high, as in the mockup nav
    approvals: [
        { kind: 'rect', x: 3.2, y: 3.2, w: 17.6, h: 17.6, rx: 3 },
        ...p('m7.8 12.2 2.8 2.8 5.6-6.4'),
    ],
    problems: [
        { kind: 'circle', cx: 7, cy: 6, r: 2.4 },
        { kind: 'circle', cx: 7, cy: 18, r: 2.4 },
        { kind: 'circle', cx: 17, cy: 9, r: 2.4 },
        ...p('M7 8.4v7.2', 'M17 11.4c0 3.2-2.2 4.2-5.4 4.2H7'),
    ],
    scenarios: p('M8.5 5.5v13L19 12 8.5 5.5Z'),
    evals: p('M4 20V11.5', 'M10 20V4.5', 'M16 20v-5.5', 'M22 20H2'),
    audit: p(
        'M8.5 6h12.5',
        'M8.5 12h12.5',
        'M8.5 18h12.5',
        'M3.5 6h.01',
        'M3.5 12h.01',
        'M3.5 18h.01'
    ),
    activity: p('M3 12h3.8l2.4-7 4 14 2.5-7H21'),
    flask: p(
        'M9.2 3h5.6',
        'M10 3v5.2l-5.6 9.4A2 2 0 0 0 6.2 20.7h11.6a2 2 0 0 0 1.8-3.1L14 8.2V3',
        'M7.4 15h9.2'
    ),
    sun: [
        { kind: 'circle', cx: 12, cy: 12, r: 4.2 },
        ...p(
            'M12 2.4v2.2M12 19.4v2.2M2.4 12h2.2M19.4 12h2.2M5.2 5.2l1.6 1.6M17.2 17.2l1.6 1.6M18.8 5.2l-1.6 1.6M6.8 17.2l-1.6 1.6'
        ),
    ],
    moon: p('M20.4 14.6A8.6 8.6 0 1 1 9.4 3.6a6.9 6.9 0 0 0 11 11Z'),
    menu: p('M3.5 6.5h17', 'M3.5 12h17', 'M3.5 17.5h17'),
    close: p('M18 6 6 18', 'M6 6l12 12'),
    'chevron-down': p('m6 9.5 6 6 6-6'),
    check: p('m5 12.5 4.2 4.2L19 6.8'),
    'sev-critical': p(
        'M8.2 2.5h7.6l5.7 5.7v7.6l-5.7 5.7H8.2l-5.7-5.7V8.2l5.7-5.7Z',
        'M12 7.5v5',
        'M12 16.2h.01'
    ),
    'sev-high': p(
        'M10.3 3.9 2.5 17.4A2 2 0 0 0 4.2 20.4h15.6a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z',
        'M12 9v4',
        'M12 17h.01'
    ),
    'sev-medium': p(
        'M12 2.6 21.4 12 12 21.4 2.6 12 12 2.6Z',
        'M12 7.8v4.6',
        'M12 16.2h.01'
    ),
    'sev-low': [c(12, 12, 9), c(12, 12, 2.4)],
    circle: [c(12, 12, 8.5)],
    search: [c(11, 11, 6.8), ...p('m16.2 16.2 4.3 4.3')],
    lock: [
        { kind: 'rect', x: 4.5, y: 10, w: 15, h: 10, rx: 2 },
        ...p('M8 10V7.2a4 4 0 0 1 8 0V10'),
    ],
    shield: p('M12 2.8 20 6v6c0 5-3.4 8.3-8 9.2C7.4 20.3 4 17 4 12V6l8-3.2Z'),
    'shield-check': p(
        'M12 2.8 20 6v6c0 5-3.4 8.3-8 9.2C7.4 20.3 4 17 4 12V6l8-3.2Z',
        'm8.6 12 2.4 2.4 4.4-4.8'
    ),
    'x-circle': [c(12, 12, 9), ...p('m9 9 6 6', 'm15 9-6 6')],
    'check-circle': [c(12, 12, 9), ...p('m8 12 2.7 2.7L16.4 9')],
    sparkle: p(
        'M11.4 3 13 8.5l5.4 1.6L13 11.7 11.4 17 9.7 11.7 4.3 10.1 9.7 8.5 11.4 3Z',
        'M18.6 14.5 19.4 17l2.4.8-2.4.8-.8 2.4-.8-2.4-2.4-.8 2.4-.8.8-2.5Z'
    ),
    wrench: p(
        'M14.6 6.2a4.6 4.6 0 0 0-5.9 5.9L3.4 17.4a1.8 1.8 0 0 0 0 2.5l.7.7a1.8 1.8 0 0 0 2.5 0l5.3-5.3a4.6 4.6 0 0 0 5.9-5.9l-2.6 2.6-2.6-2.6 2-3.2Z'
    ),
    clock: [c(12, 12, 8.7), ...p('M12 7.2v5.2l3.2 1.9')],
    user: [
        c(12, 8, 3.8),
        ...p('M4.5 20.5c0-4.2 3.4-6.4 7.5-6.4s7.5 2.2 7.5 6.4'),
    ],
} satisfies Record<string, Shape[]>;

export type IconName = keyof typeof ICONS;

/** Decorative by default (aria-hidden); pair it with visible text or an aria-label. */
@Component({
    selector: 'app-icon',
    host: { class: 'inline-flex shrink-0', 'aria-hidden': 'true' },
    template: `
        <svg
            [attr.width]="size()"
            [attr.height]="size()"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="1.8"
            stroke-linecap="round"
            stroke-linejoin="round"
        >
            @for (shape of shapes(); track $index) {
                @switch (shape.kind) {
                    @case ('path') {
                        <path [attr.d]="shape.d" />
                    }
                    @case ('circle') {
                        <circle
                            [attr.cx]="shape.cx"
                            [attr.cy]="shape.cy"
                            [attr.r]="shape.r"
                        />
                    }
                    @case ('rect') {
                        <rect
                            [attr.x]="shape.x"
                            [attr.y]="shape.y"
                            [attr.width]="shape.w"
                            [attr.height]="shape.h"
                            [attr.rx]="shape.rx"
                        />
                    }
                }
            }
        </svg>
    `,
})
export class IconComponent {
    readonly name = input.required<IconName>();
    readonly size = input(16);
    protected readonly shapes = computed<Shape[]>(() => ICONS[this.name()]);
}
