# 0004: CopilotKit integration path for Angular 22

- **Status:** Accepted (spike, bead HealthcareAIOps-tq4)
- **Date:** 2026-11-17

## Context
The frontend is Angular 22; the agent is Python LangGraph. CopilotKit speaks the AG-UI protocol. We needed to know whether CopilotKit supports Angular 22 and which connection path is supported without the paid CopilotKit Intelligence service.

## Options considered
1. **`@copilotkit/angular` + TypeScript Copilot runtime proxying to the Python agent over AG-UI.**
2. `@copilotkit/angular` with `selfManagedAgents` (browser → agent directly, no runtime). The docs conflict: one page calls it "the supported configuration option", another says direct connections are "not recommended for production and are not officially supported", and an Intelligence callout lists it under the Enterprise plan.
3. Fallback: a hand-built Angular chat panel consuming AG-UI/SSE.

## Decision
Option 1.

| Layer | Package | Version (pinned) |
|---|---|---|
| Angular UI | `@copilotkit/angular` (`provideCopilotKit`, `<copilot-chat>`) | 0.6.0 (peer: Angular ^22, CDK ^22) |
| Runtime | `@copilotkit/runtime` (`/v2`, `/v2/node`: `CopilotRuntime`, `createCopilotNodeListener`) | 1.88.0 |
| Runtime → agent | `@ag-ui/client` (`HttpAgent`) | 1.0.2 (matches the runtime's own dependency) |
| Agent | `ag-ui-langgraph` (`LangGraphAgent`, `add_langgraph_fastapi_endpoint`) | 0.0.47 |
| Graph | `langgraph` with a checkpointer (required by ag-ui-langgraph) | 1.2.x |

Wiring:

```text
Browser (Angular, same origin)
  └─ /api/copilotkit  ── Vite dev proxy (dev) / ingress (prod)
       └─ services/copilot-runtime :4000   CopilotRuntime, SSE mode, no Intelligence
            └─ HttpAgent → services/agent :8123/agent   LangGraph over AG-UI
```

- The runtime runs **without Intelligence** (SSE mode, in-memory runner). Nothing is sent to CopilotKit's hosted services. CLI and runtime telemetry are disabled via `COPILOTKIT_TELEMETRY_DISABLED=1`.
- The browser only ever calls its own origin. The agent is not exposed publicly; in K3s it is reachable only from the runtime (network policy).
- The Python `copilotkit` package is not needed; `ag_ui_langgraph.LangGraphAgent` is sufficient.

## Findings relevant to later work
- `provideCopilotKit` accepts `headers` (record or async builder per request): this is how the user's JWT reaches the runtime and is forwarded to the agent (plan §7.1). The runtime forwards `authorization` and `x-*` headers to agents.
- `@copilotkit/angular` exports `injectInterrupt()`, which binds to LangGraph `interrupt()`: the approval step (plan §6.2) can surface in the chat as well as in the approval inbox. Approval authority still lives in the API, not the chat.
- The runtime exposes `GET /api/copilotkit/info` for readiness probes and `npx copilotkit@latest verify --expect-runtime oss` for wiring checks.

## Spike evidence
Run on 2026-11-17 (macOS, Node 24.19, Python 3.14):

| Check | Result |
|---|---|
| Agent speaks AG-UI (`services/agent/tests/test_spike_transport.py`) | Pass: `RUN_STARTED` … `RUN_FINISHED`, echo text present, no `RUN_ERROR` |
| Runtime `GET /api/copilotkit/info` | Pass: version 1.88.0, agent `default` declared, `mode: sse`, `telemetryDisabled: true` |
| Full run through runtime → agent (`POST /api/copilotkit/agent/default/run`) | Pass: `RUN_STARTED, STEP_STARTED, STATE_SNAPSHOT, STEP_FINISHED, MESSAGES_SNAPSHOT, RUN_FINISHED` |
| Vite dev proxy `/api/copilotkit` → runtime | Pass: `/info` reachable through `:5173` |
| Runtime typecheck (`tsc --noEmit`) | Pass |
| Angular production build with `provideCopilotKit` + `<copilot-chat>` | Pass (after the stylesheet fix below) |
| Browser render and send of a chat message at `/spike/assistant` | Pass (manual check, 2026-11-18) |

Issue found and fixed: `@copilotkit/angular/styles.css` uses native CSS `@layer`, which the template's Tailwind v3 PostCSS pass rejects. The stylesheet is served as a plain `<link>` by a small Vite plugin (`copilotkitStyles()` in `apps/web/vite.config.mts`) instead of being imported through PostCSS. Revisit when the app moves to Tailwind v4.

The spike node returns a whole message (no LLM), so text arrives as `MESSAGES_SNAPSHOT` rather than `TEXT_MESSAGE_CONTENT` deltas. Token streaming is exercised when the real LLM node lands in week 3.

The runtime logs that thread listing needs `identifyUser`; wire it to the demo JWT (ADR-0007) so users only see their own threads.

## Consequences
- One extra deployable (`services/copilot-runtime`, Node), justified: it is CopilotKit's supported path and keeps the agent off the public network.
- CopilotKit's Angular package is young (0.x; first release 2026-06). Versions are pinned exactly; upgrades are deliberate and re-run the spike checks.
