import { provideHttpClient, withXhr } from '@angular/common/http';
import { ApplicationConfig } from '@angular/core';
import { provideAnimations } from '@angular/platform-browser/animations';
import {
    PreloadAllModules,
    provideRouter,
    withComponentInputBinding,
    withInMemoryScrolling,
    withPreloading,
} from '@angular/router';
import { provideCopilotKit } from '@copilotkit/angular';
import { provideFuse } from '@fuse';
import { appRoutes } from 'app/app.routes';

export const appConfig: ApplicationConfig = {
    providers: [
        provideAnimations(),
        provideHttpClient(withXhr()),
        provideRouter(
            appRoutes,
            withPreloading(PreloadAllModules),
            withInMemoryScrolling({ scrollPositionRestoration: 'enabled' }),
            withComponentInputBinding()
        ),

        // CopilotKit (ADR-0004). Same-origin path: Vite proxies it in dev,
        // ingress routes it in production, so there is no CORS or per-env URL.
        provideCopilotKit({
            runtimeUrl: new URL('/api/copilotkit', window.location.origin).href,
        }),

        // Fuse library services (splash screen, media watcher, overlays).
        // The console's look comes from src/styles/tokens.css, not Fuse themes.
        provideFuse({
            fuse: {
                layout: 'empty',
                scheme: 'dark',
                screens: {
                    sm: '600px',
                    md: '960px',
                    lg: '1280px',
                    xl: '1440px',
                },
                theme: 'theme-default',
                themes: [{ id: 'theme-default', name: 'Default' }],
            },
        }),
    ],
};
