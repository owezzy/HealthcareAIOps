# Make targets

Run from the repository root. `make help` prints the same list.

| Target | What it does |
|---|---|
| `make install` | Runs `install-py`, `install-runtime`, `install-web` and `install-hooks` |
| `make install-py` | `uv sync`: the Python workspace (contracts, API, agent) and dev tools |
| `make install-runtime` | `npm ci` in `services/copilot-runtime` |
| `make install-web` | `npm ci` in `apps/web` |
| `make install-hooks` | `npm ci` at the root: ESLint, Prettier, lint-staged and the husky Git hooks |
| `make db` | Starts Postgres 18 from `compose.yaml` (Docker) and waits until it is healthy |
| `make migrate` | `alembic upgrade head` for the API, against `AIOPS_DATABASE_URL` |
| `make dev` | Runs `api`, `correlator`, `agent`, `runtime` and `web` in parallel; Ctrl-C stops all five |
| `make correlator` | Correlation worker: turns queued alerts into incidents |
| `make api` | API on port 8000, with reload |
| `make agent` | Agent on port 8123 (AG-UI at `/agent`), with reload |
| `make runtime` | CopilotKit runtime on port 4000 (`/api/copilotkit`), with reload |
| `make web` | Angular dev server on port 5173; proxies `/api/copilotkit` and `/api` |
| `make test` | Python tests. API adapter tests start a throwaway Postgres if `AIOPS_TEST_DATABASE_URL` is not set |
| `make lint` | Ruff, ESLint and the runtime type-check |
| `make format` | Ruff fix and format, then Prettier |
| `make scenario S=<id>` | Inject a scenario's fault into the live estate (run on `owezzy-db`) |
| `make scenario-reset` | Undo the active scenario |
| `make scenario-status` | Show the active scenario |
| `make manifests` | Regenerate `deploy/estate/estate.yaml` from `sim/services.yaml` (a test fails if you forget) |
| `make build` | Production build of the Angular app |
| `make check` | `lint`, `test` and `build`: what CI runs |

## Variables

| Variable | Default | Used by |
|---|---|---|
| `API_PORT` | `8000` | `api`, and the default `AIOPS_API_URL` |
| `AGENT_PORT` | `8123` | `agent` |

The Makefile also exports development defaults for `AIOPS_DATABASE_URL`, `AIOPS_INTERNAL_TOKEN` and `AIOPS_API_URL`. A value already set in your shell wins. See [Configuration](configuration.md).
