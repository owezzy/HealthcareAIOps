"""Token usage is captured for every chat-model call made inside the graph."""

from datetime import UTC, date, datetime
from typing import Any

from ag_ui_langgraph import LangGraphAgent, add_langgraph_fastapi_endpoint
from fastapi import FastAPI
from fastapi.testclient import TestClient
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph

from aiops_agent.usage import ApiUsageSink, UsageLedger, UsageRecorder, UsageSink
from aiops_contracts.usage import ModelPrice, PriceTable

FIXED_NOW = datetime(2026, 11, 18, 9, 30, tzinfo=UTC)
PRICES = PriceTable(
    models={"priced-model": ModelPrice(input_per_million_usd=2.0, output_per_million_usd=8.0)}
)


class FakeChatModel(BaseChatModel):
    """Behaves like a provider client: reports usage on invoke and, if metered, when streaming."""

    model_id: str
    input_tokens: int
    output_tokens: int
    reports_usage: bool = True

    @property
    def _llm_type(self) -> str:
        return "fake-metered"

    def _usage(self) -> dict[str, int] | None:
        if not self.reports_usage:
            return None
        total = self.input_tokens + self.output_tokens
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": total,
        }

    def _generate(
        self, messages: Any, stop: Any = None, run_manager: Any = None, **kwargs: Any
    ) -> ChatResult:
        message = AIMessage(
            content="ok",
            response_metadata={"model_name": self.model_id},
            usage_metadata=self._usage(),
        )
        return ChatResult(generations=[ChatGeneration(message=message)])

    def _stream(self, messages: Any, stop: Any = None, run_manager: Any = None, **kwargs: Any):
        yield ChatGenerationChunk(message=AIMessageChunk(content="ok"))
        yield ChatGenerationChunk(
            message=AIMessageChunk(
                content="",
                response_metadata={"model_name": self.model_id},
                usage_metadata=self._usage(),
            )
        )


def _graph_calling(*models: FakeChatModel):
    queue = list(models)

    def call_model(state: MessagesState) -> dict:
        return {"messages": [queue.pop(0).invoke(state["messages"])]}

    graph = StateGraph(MessagesState)
    graph.add_node("call_model", call_model)
    graph.add_edge(START, "call_model")
    graph.add_edge("call_model", END)
    return graph.compile(checkpointer=InMemorySaver())


def _recorder(ledger: UsageSink) -> UsageRecorder:
    return UsageRecorder(ledger, PRICES, clock=lambda: FIXED_NOW)


def _invoke(ledger: UsageSink, *models: FakeChatModel, thread_id: str = "inc-1042") -> None:
    graph = _graph_calling(*models)
    for _ in models:
        graph.invoke(
            {"messages": [("user", "investigate")]},
            config={"callbacks": [_recorder(ledger)], "configurable": {"thread_id": thread_id}},
        )


def _run_over_ag_ui(ledger: UsageLedger, model: FakeChatModel, thread_id: str) -> None:
    app = FastAPI()
    add_langgraph_fastapi_endpoint(
        app=app,
        agent=LangGraphAgent(
            name="default", graph=_graph_calling(model), config={"callbacks": [_recorder(ledger)]}
        ),
        path="/agent",
    )
    payload = {
        "threadId": thread_id,
        "runId": "r-1",
        "state": {},
        "tools": [],
        "context": [],
        "forwardedProps": {},
        "messages": [{"id": "m-1", "role": "user", "content": "go"}],
    }
    with TestClient(app).stream("POST", "/agent", json=payload) as response:
        assert response.status_code == 200
        list(response.iter_lines())


def test_records_tokens_cost_and_thread_for_each_call() -> None:
    ledger = UsageLedger()
    _invoke(ledger, FakeChatModel(model_id="priced-model", input_tokens=1_000, output_tokens=500))

    [usage] = ledger.records()
    assert (usage.model, usage.input_tokens, usage.output_tokens, usage.total_tokens) == (
        "priced-model",
        1_000,
        500,
        1_500,
    )
    assert usage.thread_id == "inc-1042"
    assert usage.cost_usd == 0.006  # 1000 * $2/M + 500 * $8/M
    assert usage.recorded_at == FIXED_NOW


def test_streamed_ag_ui_runs_are_recorded_via_the_agent_config() -> None:
    """app.py relies on ag-ui-langgraph merging agent config callbacks into every streamed run."""
    ledger = UsageLedger()
    _run_over_ag_ui(
        ledger,
        FakeChatModel(model_id="priced-model", input_tokens=200, output_tokens=100),
        thread_id="inc-2001",
    )

    [usage] = ledger.records()
    assert (usage.thread_id, usage.model, usage.total_tokens) == ("inc-2001", "priced-model", 300)


def test_call_without_usage_is_counted_unmetered_and_makes_spend_unknown() -> None:
    ledger = UsageLedger()
    _invoke(ledger, FakeChatModel(model_id="priced-model", input_tokens=1_000, output_tokens=500))
    silent = FakeChatModel(
        model_id="priced-model", input_tokens=5, output_tokens=5, reports_usage=False
    )
    _run_over_ag_ui(ledger, silent, thread_id="inc-2002")

    summary = ledger.summary(date(2026, 11, 18))
    assert (summary.calls, summary.unmetered_calls) == (2, 1)
    assert summary.cost_usd is None  # never under-report spend
    unmetered = next(r for r in ledger.records() if not r.metered)
    assert (unmetered.thread_id, unmetered.total_tokens) == ("inc-2002", None)


def test_unpriced_model_has_unknown_cost_and_makes_the_day_total_unknown() -> None:
    ledger = UsageLedger()
    _invoke(
        ledger,
        FakeChatModel(model_id="priced-model", input_tokens=1_000, output_tokens=500),
        FakeChatModel(model_id="mystery-model", input_tokens=10, output_tokens=10),
    )

    summary = ledger.summary(date(2026, 11, 18))
    assert (summary.calls, summary.total_tokens, summary.cost_usd) == (2, 1_520, None)
    totals = {t.model: t for t in summary.by_model}
    assert totals["priced-model"].cost_usd == 0.006
    assert totals["mystery-model"].cost_usd is None


def test_summary_is_scoped_to_the_requested_day() -> None:
    ledger = UsageLedger()
    _invoke(ledger, FakeChatModel(model_id="priced-model", input_tokens=1, output_tokens=1))
    assert ledger.summary(date(2026, 11, 17)).calls == 0


def test_api_sink_retries_transport_errors_then_posts_idempotent_record() -> None:
    import httpx

    calls: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append({"auth": request.headers["authorization"], "body": request.read()})
        if len(calls) == 1:
            raise httpx.ConnectError("api restarting")
        return httpx.Response(201)

    sink = ApiUsageSink(
        "http://api:8000/",
        "svc-token",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        sleep=lambda _: None,
    )
    _invoke(sink, FakeChatModel(model_id="priced-model", input_tokens=10, output_tokens=5))

    assert len(calls) == 2
    assert calls[1]["auth"] == "Bearer svc-token"
    assert b'"total_tokens":15' in calls[1]["body"]


def test_api_sink_does_not_retry_a_rejected_record() -> None:
    import httpx

    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(401)

    sink = ApiUsageSink(
        "http://api:8000",
        "wrong",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        sleep=lambda _: None,
    )
    _invoke(sink, FakeChatModel(model_id="priced-model", input_tokens=1, output_tokens=1))
    assert attempts == 1
