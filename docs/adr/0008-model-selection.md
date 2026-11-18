# 0008: Model comparison and default model

- **Status:** Proposed (exact versions pinned at the first full eval run)
- **Date:** 2026-11-17

## Context
Hiring panels value evidence-based model choice. All candidates expose OpenAI-compatible chat APIs with tool calling.

## Decision
Compare **OpenAI** (closed frontier), **DeepSeek** (open-weight) and **Qwen** (open-weight) on the full eval suite: accuracy, safety, cost per investigation, p50/p95 latency. One client abstraction; model is configuration. The demo default is the best safety-then-accuracy result within the cost cap.

To record here: exact model IDs, provider endpoints, structured-output support, data-handling terms per provider (all data is synthetic).

## Consequences
Model swaps are config changes; prompt changes are re-evaluated on all three.

## Token usage capture (implemented)
- Every chat-model call is recorded by `aiops_agent.usage.UsageRecorder`, a LangChain callback set once in the AG-UI agent's config (ag-ui-langgraph merges it into every run). Records use `aiops_contracts.usage.LlmUsage`: thread, provider, model, input/output/total tokens, cost.
- Cost uses `config/model-prices.yaml`. Fill it from each provider's published prices when versions are pinned; an unpriced model records `cost_usd: null` (unknown, never guessed).
- **Requirement for every provider client:** runs stream over AG-UI, so the client must report usage while streaming (for LangChain `ChatOpenAI`, including OpenAI-compatible DeepSeek and Qwen endpoints, set `stream_usage=True`). A call that ends without usage is counted as `unmetered_calls` and makes the day's cost unknown instead of understated.
- The agent posts each record to the API (`POST /internal/usage`, service token, idempotent on `call_id`, bounded retries; a record that still fails is logged in full for replay). Without `AIOPS_API_URL` it keeps records in memory and warns.
- The API stores records in Postgres (`llm_usage`, Alembic migration 0001, with a check constraint that metered rows have token counts and unmetered rows have none) and serves `GET /api/budget/today` (`BudgetStatus`: `ok`, `warn` at 80%, `exhausted`, or `unknown`). The console polls it every 30 s; `exhausted` turns on Replay mode.
- **Enforced (2026-11-18):** the agent checks `GET /api/budget/today` before every AG-UI run (cached 10 s) and refuses with `RUN_ERROR` when it is `exhausted`; the model is never called. The budget is exhausted by spend (`AIOPS_DAILY_LLM_BUDGET_USD`) **or** by calls (`AIOPS_DAILY_LLM_CALL_CAP`, default 300). The call cap is the decision on unknown spend: runs with unknown cost are allowed, but never unlimited.
- If the budget cannot be read (API down, bad response), the agent **fails closed** and refuses the run (`budget_unavailable`). Failures are not cached, so runs resume as soon as the API answers.

## Provider configuration (implemented)
`aiops_agent.llm` builds every provider with LangChain `ChatOpenAI` and `stream_usage=True`; `AIOPS_LLM_MODEL=<provider>:<model id>` selects it. The default `fake:echo` model streams and reports usage without keys.

| Provider | Endpoint | Key | Structured output | Verified so far |
|---|---|---|---|---|
| `openai` | client default | `OPENAI_API_KEY` | `json_schema`, strict | Contract tests against a fake endpoint |
| `deepseek` | `https://api.deepseek.com` | `DEEPSEEK_API_KEY` | tool calling | Third-party docs: OpenAI-compatible, usage on streams with `include_usage`. `json_schema` not confirmed by official docs |
| `qwen` | `https://dashscope-intl.aliyuncs.com/compatible-mode/v1` | `DASHSCOPE_API_KEY` | tool calling | Alibaba docs: OpenAI-compatible; `json_schema` only on some models; streamed usage not confirmed |
| `ollama` | `http://localhost:11434/v1` (override with `AIOPS_LLM_BASE_URL`) | none | `json_schema`, not strict | Contract tests only. On 2026-11-18 the local daemon (0.40.16) reported `nemotron-3-nano:30b` retired on 2026-11-09 (suggesting `glm-5.3-flash:cloud`), and every `:cloud` model required Ollama usage credits |

- The strict schema comes from `aiops_contracts.schema.strict_json_schema`: every object closed, every property required (optional ones nullable), unsupported keywords removed. Output is always re-validated with `parse_findings`, whichever method produced it.
- Verify each provider with a real key before the first eval: one streamed call (expect a metered usage record) and one structured call. If a provider ignores `include_usage`, its calls show up as unmetered and the budget reads "unknown".

- Ollama `:cloud` models are billed as Ollama credits with no per-token price in `config/model-prices.yaml`, so their cost records as unknown. The daily call cap (budget enforcement) is what limits them.

## Local development model: NVIDIA Nemotron 3 Nano 4B via Ollama (2026-11-18)
- `make dev` uses `ollama:nemotron-3-nano:4b` (2.9 GB, local, free; supports tool calling). The 30B variant needs 18–24 GB and does not fit the 16 GB development Mac; the `:cloud` variant was retired and Ollama cloud needs credits.
- Verified with a real call through the AG-UI agent: the stream arrived in 20 deltas and **usage was reported** (`metered`, 29 input / 89 output tokens, thread recorded). Priced at zero in `config/model-prices.yaml`.
- Structured Findings (`json_schema`, not strict): the output matched the schema shape, but failed the contract rule "root_cause must be one of the hypotheses" on the first attempt, in 39 s. The repair loop must handle this, and the rule's design is under review (task filed).
- CI and tests keep the keyless `fake:echo` default.

