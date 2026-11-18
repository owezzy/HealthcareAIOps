# 0010: Frontend feature structure and NgRx SignalStore

- **Status:** Accepted
- **Date:** 2026-11-17

## Context
The web app starts from the Fuse Angular 22 template, which organises code as `modules/` and uses RxJS `ReplaySubject` services for state. The product screens (incident workspace, approval inbox, live scenario runs) share async state across components.

## Decision
- New code lives in `src/app/features/<feature>/` with `data-access/`, `pages/`, `ui/` and `<feature>.models.ts` (see docs/explanation/architecture.md).
- Shared or async feature state uses **NgRx SignalStore** (`@ngrx/signals`, version matched to Angular 22, added with the first feature that needs it). Local UI state uses component `signal()`. Single-component server data uses `httpResource`.
- `src/@fuse` is treated as vendor code and not edited.

## Consequences
- Predictable place for every piece of state; agents can find a feature's state in one file.
- Template services are migrated to signals only when touched.
