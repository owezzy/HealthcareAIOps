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
| `spent_usd` | number or null | Null when any call today was unpriced or unmetered |
| `state` | `ok`, `warn`, `exhausted`, `unknown` | `exhausted` switches the console to Replay mode |
| `calls`, `unmetered_calls` | integer | |

The full schema is also served by FastAPI at `GET /docs` and `GET /openapi.json` on the API port.

## Agent (port 8123)

| Method and path | Response |
|---|---|
| `GET /health` | `{"status": "ok"}` |
| `POST /agent` | AG-UI run: a Server-Sent Events stream (`RUN_STARTED` … `RUN_FINISHED`). Called by the runtime only |

## Copilot runtime (port 4000)

Served by CopilotKit under `/api/copilotkit`: `GET /info` (version and declared agents; used as the readiness probe), `POST /agent/:agentId/run`, `POST /agent/:agentId/connect` and the thread routes. The agent ID is `default`.

## Web (port 8080 in the image)

`GET /healthz` returns `ok` (liveness). Every other unknown path serves `index.html` (single-page app).
