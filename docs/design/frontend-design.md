# Frontend design specification

Implementation spec for `apps/web`, derived from the OpenDesign mockups in
[`mockups/`](mockups/). Open `mockups/index.html` (screens),
`mockups/system-states.html` (degraded states) and
`mockups/component-sheet.html` (components and rules) in a browser. Code
structure follows [`../explanation/architecture.md`](../explanation/architecture.md) and ADR-0010.

**Source of truth:** the mockups for look and layout, this document for
behaviour, and `aiops_contracts` for data. Where they disagree, §7 records the
resolution.

---

## 1. Design principles (from the component sheet, §09)

1. **Facts before inferences.** Facts sit above hypotheses in solid rows with direct evidence. A hypothesis never appears above the fact that contradicts it.
2. **Actions stay human.** The agent drafts and recommends; only an Approver triggers execution. Every gated action shows a risk label, a countdown, a rollback line and an audit hash.
3. **One accent, one meaning.** Teal marks agent provenance, focus and links only. Success and severity use green, amber and red, always paired with a word or glyph.
4. **Nothing hides on failure.** Missing evidence, budget exhaustion, unavailable models and rejected approvals render in place with a plain-language reason and a next step. No toasts for anything that matters.
5. **Triage labels never travel alone.** Severity, tier and status each pair a glyph or code with a word, and each has a distinct shape. The order is always severity → tier → status, then monospace identifiers.

## 2. Visual foundation

### 2.1 Typography

| Role | Font | Weights |
|---|---|---|
| UI | Geist (fallback Inter, system) | 400, 500, 600 |
| IDs, queries, metrics, logs, hashes | JetBrains Mono | 400, 500, 600 |

Self-host both fonts in `apps/web/public/fonts` rather than loading from Google Fonts at runtime.

### 2.2 Design tokens

The full token set is in `mockups/assets/console.css` (`:root` for dark, `[data-theme="light"]` for light). Copy those two blocks verbatim into `apps/web/src/styles/tokens.css`; they are the contract. Key groups:

| Group | Tokens | Notes |
|---|---|---|
| Surfaces | `--bg`, `--bg-2`, `--panel`, `--panel-2`, `--panel-3`, `--surface-hover` | Dark is primary: `--bg #0a0c10`, `--panel #11151b` |
| Lines | `--line`, `--line-2`, `--line-3` | Borders do the work in light mode |
| Text | `--text`, `--text-2`, `--text-3` | |
| Accent (agent provenance, focus, links) | `--accent`, `--accent-text`, `--accent-bg`, `--accent-line` | Dark `#48d3c0`, light `#0d8074` |
| AI containers | `--ai-bg`, `--ai-line` | `color-mix` of accent into panel |
| Severity | `--sev-{critical,high,medium,low}`, `-text`, `-bg` | Never used for anything but severity |
| Success | `--ok`, `--ok-text`, `--ok-bg` | |
| Tier | `--tier-line`, `--tier-text`, `--tier-bg` | Deliberately neutral: tier is context, not urgency |
| Shape and motion | `--radius 8px`, `--radius-sm 5px`, `--dur 160ms`, `--ease cubic-bezier(0.22,1,0.36,1)` | |
| Layout | `--nav-w 228px` (64px collapsed under the narrow breakpoint) | |

**Tailwind:** extend `tailwind.config.js` so utilities resolve to the variables (e.g. `colors: { panel: 'var(--panel)', 'sev-high': 'var(--sev-high)' }`). Never hard-code hex values in components.

**Theme switching:** set `data-theme="light"` on `<html>`. Both themes meet WCAG AA; nothing is inverted by hand.

**Fuse and Angular Material:** product screens are built with Tailwind and these tokens. Material/CDK is used only for primitives (overlay, menu, dialog, drawer focus trap), restyled through the tokens. The Fuse layout shell is replaced by the console shell in §3.

## 3. Application shell

| Element | Behaviour |
|---|---|
| Left nav (`--nav-w`) | Incidents, Approvals (count badge), Problems & Changes, Scenarios, Evals, Audit. `aria-current="page"` on the active item; collapses to icons at narrow widths |
| Top bar | Environment badge **"DEMO · synthetic data · hh-demo-01"**, LLM budget meter (C-17), role switcher (C-18), theme toggle, user |
| Global banners | Replay mode and AI-unavailable banners sit under the top bar and persist while the condition holds |

Shell state (current user, role, budget, replay mode, AI availability) lives in a `SessionStore` in `core/session/`.

## 4. Screens

| # | Screen | Mockup (`data-view`) | Route | Feature | State |
|---|---|---|---|---|---|
| 1 | Incident queue | `queue` | `/incidents` | `incidents` | `IncidentsStore` (list, filters, summary strip) |
| 2 | Incident workspace | `workspace` | `/incidents/:id` | `incidents` | `IncidentWorkspaceStore` (incident, timeline, findings stream, evidence) |
| 3 | Evidence drawer | drawer in `workspace` | `/incidents/:id?evidence=ev_7f3a` | `incidents` | Workspace store; deep-linkable through the query parameter |
| 4 | Approval inbox and detail | `approvals` | `/approvals`, `/approvals/:id` | `approvals` | `ApprovalsStore` (pending list, server-driven expiry, decide) |
| 5 | Approval as Viewer | `approvals` with role = viewer | same | `approvals` | Gating from `SessionStore.role` |
| 6 | Execution and verification | `verification` | `/incidents/:id/verification` | `incidents` | Workspace store |
| 7 | Problems and Changes | `problems` | `/problems`, `/changes/:id` | `problems-changes` | `httpResource` (read-mostly) |
| 8 | Scenario launcher and live pipeline | `scenarios` | `/scenarios` | `scenarios` | `ScenarioRunStore` (SSE progress, queue position) |
| 9 | Eval report | `evals` | `/evals` | `evals` | `httpResource` (static report JSON) |
| 10 | Audit log | `audit` | `/audit` | `audit` | `httpResource` with paging and filters |
| 11 | System states | `system-states.html` | n/a (states of screens 1–2) | `incidents`, `core/session` | See §6 |

The CopilotKit panel is a right-hand column inside the incident workspace, in feature `assistant`, scoped to the open incident (pending ADR-0004).

### 4.1 Incident workspace layout

- **Header:** title, severity → tier → status, lifecycle stepper (C-05), IDs in monospace.
- **Left column:** timeline (alerts, agent steps, tool calls, human actions) and correlated alerts.
- **Centre:** AI findings panel with a provenance header (C-09), then fact rows (C-10), hypotheses (C-11, C-11b), gaps and guardrails (C-12), and the recommended action card (C-13). Blast radius with affected departments sits below.
- **Right:** CopilotKit assistant.

## 5. Component inventory (`src/app/shared/ui/`)

Component codes match the component sheet.

| Code | Component | Selector | Inputs (signal) | Key rules |
|---|---|---|---|---|
| C-01 | Severity badge | `app-severity-badge` | `severity: Severity` | Distinct glyph per level (octagon, triangle, diamond, target) plus the word |
| C-02 | Tier badge | `app-tier-badge` | `tier: ClinicalTier \| 'infra'` | Neutral colours; monospace code; infra uses a dashed border |
| C-03 | Status pill | `app-status-pill` | `state: IncidentState \| 'rejected'` | Pill shape; only "Awaiting approval" gets amber |
| C-05 | Lifecycle stepper | `app-lifecycle-stepper` | `state`, `followUp?` | One rail, scrolls horizontally, `aria-current="step"`, only glow in the system |
| C-06 | Evidence chip | `app-evidence-chip` | `id`, `source?` | Monospace ID; opens the drawer; accent on hover/focus, never severity |
| C-07 | Confidence pill | `app-confidence-pill` | `level` | Three bars plus the word; low is quiet, not alarming |
| C-08 | Findings skeleton | `app-findings-skeleton` | `committed`, `total` | "streaming · 2 of 4 facts committed"; **no action card until facts commit** |
| C-09 | Provenance header | `app-provenance-header` | `model`, `promptVersion`, `streamedAt` | Mandatory; the timestamp is the run time, not the view time |
| C-10 | Fact row | `app-fact-row` | `fact: Fact` | Solid card, own evidence row, no confidence pill |
| C-11 | Hypothesis card | `app-hypothesis-card` | `hypothesis`, `rank` | Supporting and contradicting columns always shown ("None recorded."); weak ones lose the fill but stay visible |
| C-12 | Gap and guardrail notes | `app-missing-info`, `app-injection-notice` | items | Dashed border = absent; red border = hostile input contained |
| C-13 | Action card | `app-action-card` | `proposal`, `approval`, `role` | The only accent-tinted card; always shows rationale, expected outcome, rollback, follow-up and evidence |
| C-14 | Approval countdown | `app-approval-countdown` | `expiresAt` (server time) | Amber under 15 min, critical under 1 min; at expiry shows "re-request required" |
| C-15 | Outcome banner | `app-outcome-banner` | `outcome`, `hash` | Shown once at the top of the approval detail; the hash is truncated and expandable to 64 characters |
| C-16 | Role note | `app-role-note` | `role`, `required` | Explains gating where the button is, not in a toast |
| C-17 | Budget meter | `app-budget-meter` | `spent`, `cap` | Normal, warning and exhausted; exhausted flips the console to Replay mode |
| C-18 | Role switcher | `app-role-switcher` | role list | Each option states what it can and cannot do; switching changes permissions, never data |

Inputs use the TypeScript client generated from the API's OpenAPI schema, so enums match `aiops_contracts.vocabulary` exactly.

## 6. System states

| State | Trigger | Rendering |
|---|---|---|
| Replay mode | Budget meter at 100% (`SessionStore.replayMode`) | Persistent banner; agent tools stop; recorded runs shown; reads stay available |
| AI unavailable | Agent health check fails | Workspace still shows alerts, correlation, timeline and blast radius; findings panel reads "AI investigation unavailable. Core monitoring continues." |
| Empty queue | Filters match nothing | Empty state naming the active filters, with a "clear filters" action |
| Findings streaming | Agent run in progress | Labelled skeletons (C-08); the action card is withheld until the facts commit |
| Denied action | Role lacks permission | Disabled button with a role note (C-16); the attempt is written to the audit log |

## 7. Mockup vs domain model: resolutions

Rows 1–3 and 5 are implemented in `apps/web` (role copy, stepper end state, tier labels, server-driven countdown). Row 4 needs real run metadata; row 6 waits for the week-6 eval report.

The mockups were generated from the design prompt before the scenario contracts existed. Where they disagree, implement the resolution below and correct the mockup in the next OpenDesign pass.

| # | Mockup says | Domain says | Resolution |
|---|---|---|---|
| 1 | Role switcher: Operator "can investigate and **execute**" | Only an Approver's approval triggers the executor (ADR-0002, plan §7.3) | Operator copy: "Can investigate and request actions. Cannot approve." |
| 2 | Lifecycle stepper has six states ending at "Resolved" | `IncidentState` also has `resolved_with_problem`; rejection returns to `investigating` | The final step renders "Resolved · Problem PRB-208" when `followUp = problem`. Rejection is a status pill and a timeline entry, not a stepper state |
| 3 | Tier labels: "T2 supporting", "T3 office" | Plan §3.1: T2 = degraded workflow with a workaround, T3 = non-clinical or patient convenience | Labels: "Tier 1 · clinical", "Tier 2 · workaround exists", "Tier 3 · non-clinical" |
| 4 | Provenance shows `ops-agent-3.1 · prompt v12` | Models are OpenAI, DeepSeek and Qwen (ADR-0008) | Show the real provider/model ID and prompt version from the run record |
| 5 | Countdown ticks locally in the demo | Approvals bind to server expiry (plan §7.2) | Always derive from server `expiresAt`; tick locally only between server syncs |
| 6 | Eval figures (83% vs 52%, $0.042 …) | Placeholders until the week-6 eval run | Load from the eval report JSON; never hard-code numbers |

## 8. Accessibility

- WCAG AA contrast in both themes (token sets are already tuned for it).
- Status is never conveyed by colour alone: a glyph or word is always present.
- Visible focus uses the accent ring. The evidence drawer and dialogs trap focus and restore it on close (CDK).
- The lifecycle stepper uses `aria-current="step"`; nav items use `aria-current="page"`.
- Countdowns announce only at thresholds (15 min, 1 min, expired) through a polite live region, not every second.
- Respect `prefers-reduced-motion`; the only motion is 160 ms state transitions.

## 9. Build order

1. Tokens, fonts and the console shell, with `SessionStore`, the role switcher and the budget meter, replacing the Fuse example routes.
2. The shared UI components (§5), each with a Storybook-free demo route `/dev/components` that mirrors the component sheet. This doubles as a visual regression check. **Done:** components live in `src/app/shared/ui/`; their CSS is ported once into `src/styles/components.css` because they nest.
3. Incident queue and workspace, read-only, against mock data shaped by the generated API client.
4. Approvals with role gating.
5. Scenarios, evals, audit, problems and changes.
6. The CopilotKit panel, once ADR-0004 is decided.
