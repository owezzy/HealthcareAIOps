import 'zone.js';

import '@fontsource-variable/geist';
import '@fontsource-variable/jetbrains-mono';
import './@fuse/styles/main.scss';
import './@fuse/styles/tailwind.scss';
import './@fuse/styles/themes.scss';
import './styles/components.css';
import './styles/styles.scss';
import './styles/tailwind.scss';
import './styles/tokens.css';
import './styles/vendors.scss';
// CopilotKit's stylesheet is linked by the copilotkitStyles() Vite plugin, not imported here.

import { provideZoneChangeDetection } from '@angular/core';
import { bootstrapApplication } from '@angular/platform-browser';
import { AppComponent } from 'app/app.component';
import { appConfig } from 'app/app.config';

bootstrapApplication(AppComponent, {
    ...appConfig,
    providers: [provideZoneChangeDetection(), ...appConfig.providers],
}).catch((err) => console.error(err));
