import angular from '@analogjs/vite-plugin-angular';
import autoprefixer from 'autoprefixer';
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import tailwindcss from 'tailwindcss';
import { defineConfig, type Plugin } from 'vite';

const projectRoot = dirname(fileURLToPath(import.meta.url));

/**
 * Serves CopilotKit's prebuilt stylesheet as a plain <link>, bypassing PostCSS.
 * It is compiled with native CSS `@layer`, which this app's Tailwind v3 PostCSS
 * pass rejects ("@layer base is used but no matching @tailwind base").
 */
function copilotkitStyles(): Plugin {
    const href = '/vendor/copilotkit.css';
    const css = () =>
        readFileSync(
            createRequire(import.meta.url).resolve(
                '@copilotkit/angular/styles.css'
            )
        );
    return {
        name: 'copilotkit-styles',
        configureServer(server) {
            server.middlewares.use(href, (_req, res) => {
                res.setHeader('Content-Type', 'text/css');
                res.end(css());
            });
        },
        generateBundle() {
            this.emitFile({
                type: 'asset',
                fileName: href.slice(1),
                source: css(),
            });
        },
        transformIndexHtml: {
            order: 'post',
            handler: () => [
                {
                    tag: 'link',
                    attrs: { rel: 'stylesheet', href },
                    injectTo: 'head-prepend',
                },
            ],
        },
    };
}

export default defineConfig({
    root: resolve(projectRoot, 'src'),
    publicDir: resolve(projectRoot, 'public'),
    resolve: {
        mainFields: ['module'],
        tsconfigPaths: true,
    },
    plugins: [
        angular({ tsconfig: resolve(projectRoot, 'tsconfig.app.json') }),
        copilotkitStyles(),
    ],
    css: {
        postcss: {
            plugins: [
                tailwindcss({
                    config: resolve(projectRoot, 'tailwind.config.js'),
                }),
                autoprefixer(),
            ],
        },
        preprocessorOptions: {
            scss: {
                loadPaths: [resolve(projectRoot, 'src/@fuse/styles')],
            },
        },
    },
    server: {
        proxy: {
            // copilot-runtime (services/copilot-runtime); ingress does the same in production.
            '/api/copilotkit':
                process.env.COPILOT_RUNTIME_ORIGIN ?? 'http://localhost:4000',
            // Domain API (services/api). Listed after /api/copilotkit: first match wins.
            '/api': process.env.AIOPS_API_ORIGIN ?? 'http://localhost:8000',
        },
    },
    build: {
        outDir: resolve(projectRoot, 'dist/fuse'),
        emptyOutDir: true,
        target: 'es2022',
    },
});
