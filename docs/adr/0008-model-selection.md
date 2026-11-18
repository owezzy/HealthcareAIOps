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
- Not yet enforced: the agent does not refuse runs when the budget is exhausted. That is a separate task.

