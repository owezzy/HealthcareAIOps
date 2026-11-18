# HTTP endpoints

Paths as each service serves them. In production only the web origin is public; nginx forwards `/api/copilotkit` to the runtime and `/api/` to the API. Nothing else is routed.

## API (port 8000)

| Method and path | Auth | Public | Response |
|---|---|---|---|
| `GET /health` | none | no | `{"status": "ok"}`: the process is up |
| `GET /ready` | none | no | `{"status": "ready"}`, or `503` if the database is unreachable |
| `POST /internal/usage` | `Authorization: Bearer <AIOPS_INTERNAL_TOKEN>` | no | `201 {"status": "recorded"}`, or `200 {"status": "duplicate"}` for a known `call_id` |
| `GET /api/budget/today` | none | yes | `BudgetStatus` for the current UTC day |

`POST /internal/usage` errors: `401` wrong or missing token, `503` no token configured, `422` invalid record (for example a metered call without token counts, or a timestamp without a time zone).

### `LlmUsage` (request body of `POST /internal/usage`)

| Field | Type | Notes |
|---|---|---|
| `call_id` | string | Unique per LLM call; the idempotency key |
| `thread_id` | string or null | Investigation thread |
| `provider` | string or null | |
| `model` | string | Model ID reported by the provider |
| `metered` | boolean | `false` when the provider reported no usage |
| `input_tokens`, `output_tokens`, `total_tokens` | integer or null | Required when metered; must be null when not |
| `cost_usd` | number or null | Null when the model has no price, and always null when not metered |
| `recorded_at` | ISO-8601 with time zone | |

### `BudgetStatus` (response of `GET /api/budget/today`)

| Field | Type | Notes |
|---|---|---|
| `day` | date | UTC |
| `cap_usd` | number | `AIOPS_DAILY_LLM_BUDGET_USD` |
| `call_cap` | integer | `AIOPS_DAILY_LLM_CALL_CAP` |
| `spent_usd` | number or null | Null when any call today was unpriced or unmetered |
| `state` | `ok`, `warn`, `exhausted`, `unknown` | `exhausted`: spend or calls reached a cap; the agent refuses runs and the console shows Replay mode. `warn`: either at 80% or more. `unknown`: spend unknown and no cap near |
| `exhausted_by` | `spend`, `calls` or null | Which cap was reached |
| `calls`, `unmetered_calls` | integer | |

The full schema is also served by FastAPI at `GET /docs` and `GET /openapi.json` on the API port.

## Agent (port 8123)

| Method and path | Response |
|---|---|
| `GET /health` | `{"status": "ok"}` |
| `POST /agent` | AG-UI run: a Server-Sent Events stream (`RUN_STARTED` … `RUN_FINISHED`). Called by the runtime only. If the budget is exhausted or cannot be read, the stream is `RUN_STARTED` then `RUN_ERROR` with `code` `budget_exhausted` or `budget_unavailable`, and no model is called |

## Copilot runtime (port 4000)

Served by CopilotKit under `/api/copilotkit`: `GET /info` (version and declared agents; used as the readiness probe), `POST /agent/:agentId/run`, `POST /agent/:agentId/connect` and the thread routes. The agent ID is `default`.

## Demo services (port 8080, namespace `aiops-estate`)

| Method and path | Response |
|---|---|
| `GET /health` | `200`, or `503` while toggled unavailable |
| `GET /work` | One unit of work: call application dependencies, use the database pool, write to the volume. `200`, `502` (dependency or SSO failed), `503` (pool exhausted or unavailable), `507` (volume full) |
| `POST /messages` | `interface-engine` only. `{"destination": "lis"}` queues a message; `202`, or `422` for a non-dependency |
| `GET /metrics` | Prometheus: `http_requests_total`, `http_request_duration_seconds`, `dependency_errors_total`, `auth_upstream_errors_total`, `db_pool_in_use`, `db_pool_size`, `queue_depth`, `volume_used_ratio`, `certificate_expiry_days`, `app_info` |
| `GET` / `PUT` / `DELETE /admin/faults` | Bearer `AIOPS_ESTATE_ADMIN_TOKEN`. Toggles: `unavailable`, `extra_latency_ms`, `volume_used_percent`, `certificate_days_left` |

Logs are JSON lines on stdout: `ts`, `level`, `component`, `msg`.

## Web (port 8080 in the image)

`GET /healthz` returns `ok` (liveness). Every other unknown path serves `index.html` (single-page app).
