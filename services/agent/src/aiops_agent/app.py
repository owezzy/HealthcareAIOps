"""Composition root: serves the agent graph over AG-UI.

Run locally:  make agent   (uvicorn aiops_agent.app:create_app --factory --port 8123)
The Copilot runtime (services/copilot-runtime) proxies browser traffic here;
browsers never call this service directly (ADR-0004).

Env:
  AIOPS_API_URL         API base URL; LLM usage is posted there (ADR-0008).
                        Unset: usage is kept in memory only, with a warning.
  AIOPS_INTERNAL_TOKEN  service token for the API's /internal endpoints.
  AIOPS_MODEL_PRICES    price table path (default config/model-prices.yaml).
  AIOPS_LLM_MODEL       <provider>:<model id>; default fake:echo (see aiops_agent.llm).
"""

import logging
import os
from pathlib import Path

from ag_ui_langgraph import LangGraphAgent, add_langgraph_fastapi_endpoint
from fastapi import FastAPI
from langchain_core.language_models import BaseChatModel

from aiops_agent.llm import model_from_env
from aiops_agent.spike_graph import build_spike_graph
from aiops_agent.usage import ApiUsageSink, UsageLedger, UsageRecorder, UsageSink
from aiops_contracts.usage import PriceTable, load_price_table

AGENT_NAME = "default"
DEFAULT_PRICES_PATH = "config/model-prices.yaml"

log = logging.getLogger(__name__)


def create_app(
    sink: UsageSink | None = None,
    prices: PriceTable | None = None,
    model: BaseChatModel | None = None,
) -> FastAPI:
    sink = sink or _usage_sink()
    prices = prices or _load_prices()
    model = model or model_from_env()
    app = FastAPI(title="Healthcare AIOps Agent", version="0.1.0")

    @app.get("/health", tags=["platform"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    add_langgraph_fastapi_endpoint(
        app=app,
        agent=LangGraphAgent(
            name=AGENT_NAME,
            description="ADR-0004 spike agent: one streamed model call.",
            graph=build_spike_graph(model),
            # Merged into every run by ag-ui-langgraph, so every LLM call is recorded.
            config={"callbacks": [UsageRecorder(sink, prices)]},
        ),
        path="/agent",
    )
    return app


def _usage_sink() -> UsageSink:
    api_url = os.environ.get("AIOPS_API_URL")
    token = os.environ.get("AIOPS_INTERNAL_TOKEN")
    if api_url and token:
        return ApiUsageSink(api_url, token)
    log.warning("AIOPS_API_URL/AIOPS_INTERNAL_TOKEN not set: LLM usage is kept in memory only")
    return UsageLedger()


def _load_prices() -> PriceTable:
    path = Path(os.environ.get("AIOPS_MODEL_PRICES", DEFAULT_PRICES_PATH))
    if not path.exists():
        log.warning("No model price table at %s: costs will be recorded as unknown", path)
        return PriceTable()
    return load_price_table(path)
