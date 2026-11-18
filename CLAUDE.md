# Project Instructions for AI Agents

This file provides instructions and context for AI coding agents working on this project.

<!-- BEGIN BEADS INTEGRATION v:1 profile:minimal hash:1105d646 -->
## Beads Issue Tracker

This project uses **bd (beads)** for issue tracking. Run `bd prime` to see full workflow context and commands.

### Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --claim  # Claim work
bd close <id>         # Complete work
```

### Rules

- Use `bd` for ALL task tracking — do NOT use TodoWrite, TaskCreate, or markdown TODO lists
- Run `bd prime` for detailed command reference and session close protocol
- Use `bd remember` for persistent knowledge — do NOT use MEMORY.md files

**Architecture in one line:** issues live in a local Dolt DB; sync uses `refs/dolt/data` on your git remote; `.beads/issues.jsonl` is a passive export. See https://github.com/gastownhall/beads/blob/main/docs/core-concepts/sync-concepts.md for details and anti-patterns.

## Agent Context Profiles

The managed Beads block is task-tracking guidance, not permission to override repository, user, or orchestrator instructions.

- **Conservative (default)**: Use `bd` for task tracking. Do not run git commits, git pushes, or Dolt remote sync unless explicitly asked. At handoff, report changed files, validation, and suggested next commands.
- **Minimal**: Keep tool instruction files as pointers to `bd prime`; use the same conservative git policy unless active instructions say otherwise.
- **Team-maintainer**: Only when the repository explicitly opts in, agents may close beads, run quality gates, commit, and push as part of session close. A current "do not commit" or "do not push" instruction still wins.

## Session Completion

This protocol applies when ending a Beads implementation workflow. It is subordinate to explicit user, repository, and orchestrator instructions.

1. **File issues for remaining work** - Create beads for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **Handle git/sync by active profile**:
   ```bash
   # Conservative/minimal/default: report status and proposed commands; wait for approval.
   git status

   # Team-maintainer opt-in only, unless current instructions forbid it:
   git pull --rebase
   git push
   git status
   ```
5. **Hand off** - Summarize changes, validation, issue status, and any blocked sync/commit/push step

**Critical rules:**
- Explicit user or orchestrator instructions override this Beads block.
- Do not commit or push without clear authority from the active profile or the current user request.
- If a required sync or push is blocked, stop and report the exact command and error.
<!-- END BEADS INTEGRATION -->


## Project map (read first)

- **What and why:** `docs/explanation/healthcare-aiops-plan.md`. **How the code is organised:** `docs/explanation/architecture.md` (start with its "Where does X go?" table). **Decisions:** `docs/adr/`.
- Scenario ground truth: `sim/services.yaml`, `sim/scenarios/*.yaml`. Shared schemas: `packages/contracts` (`aiops_contracts`).
- Frontend: `apps/web` (Angular 22, Fuse template). New screens go in `src/app/features/<feature>/`; do not edit `src/@fuse`. UI spec: `docs/design/frontend-design.md`; mockups: `docs/design/mockups/index.html`.

## Build & Test

All commands live in the root `Makefile`:

```bash
make install   # uv sync + npm ci for the runtime and web app
make dev       # agent :8123 + runtime :4000 + web :5173 together (Ctrl-C stops all)
make test      # Python tests
make lint      # ruff + runtime typecheck
make check     # lint + test + Angular build (what CI runs)
make help      # every target, incl. agent/runtime/web/api individually
```

## Conventions

- **Git flow:** work on `feature/<name>` from `develop`; never commit to `main` directly. Releases: `docs/how-to/cut-a-release.md`.
- **Commits:** Conventional Commits, enforced by the `commit-msg` hook (Commitizen). Version and changelog via `uv run cz bump`.
- **Docs:** Diátaxis layout under `docs/` (index: `docs/README.md`). Update reference pages when you change make targets, env vars or endpoints.

## Non-negotiable invariants

- The agent never gets an execution tool; only `services/executor` executes approved actions (ADR-0002).
- Blast radius and correlation are deterministic code, not LLM output (ADR-0005).
- Services never import each other; they share `aiops_contracts` only. Inner layers (`domain`, `use_cases`) never import frameworks or adapters (ADR-0011).
- Synthetic data only. No patient data, ever.
