# Configuration

Every service reads its configuration from environment variables at start-up.

## API (`services/api`)

| Variable | Default | Meaning |
|---|---|---|
| `AIOPS_DATABASE_URL` | `postgresql+psycopg://aiops:aiops@localhost:5432/aiops` | SQLAlchemy URL of the API database. Also used by `make migrate` |
| `AIOPS_INTERNAL_TOKEN` | *(unset)* | Service token for `/internal/*`. **Unset means every internal call is refused** (fail closed) |
| `AIOPS_DAILY_LLM_BUDGET_USD` | `5.0` | Daily LLM spend cap. Must be positive. `exhausted` at or above it, `warn` from 80% |
| `AIOPS_CATALOGUE` | `sim/services.yaml` | Component catalogue used by the correlator (topology) |
| `AIOPS_DAILY_LLM_CALL_CAP` | `300` | Daily cap on model calls. Must be positive. Bounds models whose cost is unknown; `exhausted` at or above it, `warn` from 80% |

## Agent (`services/agent`)

| Variable | Default | Meaning |
|---|---|---|
| `AIOPS_API_URL` | *(unset)* | API base URL. LLM usage records are posted to `<url>/internal/usage`, and `<url>/api/budget/today` is checked before every run. Unset: usage stays in memory and the budget is **not enforced** |
| `AIOPS_INTERNAL_TOKEN` | *(unset)* | Must match the API's token. If this or `AIOPS_API_URL` is unset, usage is kept in memory only and a warning is logged |
| `AIOPS_MODEL_PRICES` | `config/model-prices.yaml` | Price table for LLM cost. A missing file or unpriced model records cost as unknown |
| `AIOPS_LLM_MODEL` | `fake:echo` (`make dev`: `ollama:nemotron-3-nano:4b`) | `<provider>:<model id>`. Providers: `openai`, `deepseek`, `qwen`, `ollama` and `fake` (keyless, local). Ollama model IDs keep their own colons, e.g. `ollama:<name>:cloud`. An unknown provider or missing key stops the agent at start-up |
| `AIOPS_LLM_BASE_URL` | provider default | Overrides the provider endpoint: another DashScope region, or an Ollama daemon other than `http://localhost:11434/v1` (needed in the cluster) |
| `AIOPS_LLM_TIMEOUT_SECONDS` | `60` (Ollama: `300`) | Per-request timeout for the model. Local models need minutes, not seconds |
| `OPENAI_API_KEY` | *(unset)* | Required for `openai:*` |
| `DEEPSEEK_API_KEY` | *(unset)* | Required for `deepseek:*` (endpoint `https://api.deepseek.com`) |
| `DASHSCOPE_API_KEY` | *(unset)* | Required for `qwen:*` (endpoint `https://dashscope-intl.aliyuncs.com/compatible-mode/v1`) |

## Demo services (`sim`, image `healthcare-aiops-estate`)

One image runs every simulated hospital service; `COMPONENT_ID` picks which. The fault injector changes the tuning values through real rollouts.

| Variable | Default | Meaning |
|---|---|---|
| `COMPONENT_ID` | *(required)* | Catalogue application: `sso`, `ehr-api`, `interface-engine`, `lis`, `pacs`, `patient-portal` |
| `AIOPS_CATALOGUE` | `sim/services.yaml` | Catalogue file; dependencies come from it |
| `AIOPS_ESTATE_ADMIN_TOKEN` | *(unset)* | Bearer token for `/admin/faults`. Unset: the admin endpoints refuse every call |
| `DB_POOL_SIZE` | `50` | Connection pool to the component's database (S1 lowers it) |
| `DB_QUERY_MS` | `20` | Time each request holds a pool connection |
| `WORK_CPU_MS` | `2` | Real CPU work per request (S6 throttles it) |
| `BALLAST_MI` | `0` | Resident memory held for the process lifetime (S2 sets a limit below it) |
| `DEPENDENCY_TIMEOUT_S` | `2` | Timeout for calls to dependencies |
| `APP_VERSION` | `v1.0.0` | Reported as `app_info`; a changed version is a deploy |
| `PEER_URL_PATTERN` | `http://{id}:8080` | How to reach another component |
| `RATE_PER_SECOND` | `2` | Load generator only: requests per second |

## Copilot runtime (`services/copilot-runtime`)

| Variable | Default | Meaning |
|---|---|---|
| `PORT` | `4000` | Listen port |
| `AGENT_URL` | `http://localhost:8123/agent` | AG-UI endpoint of the agent |
| `ALLOWED_ORIGINS` | `http://localhost:5173` | Comma-separated CORS origins. Same-origin traffic through the proxy does not need it |
| `COPILOTKIT_TELEMETRY_DISABLED` | `1` (set by the npm scripts and the image) | Turns off CopilotKit telemetry |

## Web dev server (`apps/web`, Vite)

| Variable | Default | Meaning |
|---|---|---|
| `COPILOT_RUNTIME_ORIGIN` | `http://localhost:4000` | Proxy target for `/api/copilotkit` |
| `AIOPS_API_ORIGIN` | `http://localhost:8000` | Proxy target for `/api` |

In production, nginx in the web image does the same routing ([`apps/web/nginx.conf`](../../apps/web/nginx.conf)).

## Tests

| Variable | Meaning |
|---|---|
| `AIOPS_TEST_DATABASE_URL` | Postgres for the API adapter tests (CI sets it). Unset: the tests start a throwaway cluster with the local `initdb` and `pg_ctl`, or skip if Postgres is not installed |

## Files

| File | Meaning |
|---|---|
| `config/model-prices.yaml` | USD per million input and output tokens, keyed by the model ID the provider reports. Empty until model versions are pinned (ADR-0008) |
| `sim/services.yaml` | The simulated estate: components, tiers, dependencies |
| `sim/scenarios/*.yaml` | Scenarios S1–S6. See [Scenario file format](scenario-format.md) |
