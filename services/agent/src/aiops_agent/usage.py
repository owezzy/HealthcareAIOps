"""Captures token usage for every LLM call the agent makes (ADR-0008).

`UsageRecorder` is a LangChain callback attached once to the AG-UI agent's
config, which ag-ui-langgraph merges into every run, so any chat model called
inside the graph is recorded without node code having to remember to do it.

Records go to a `UsageSink`: the API in normal operation (`ApiUsageSink`), or
an in-memory `UsageLedger` for tests and runs without an API.
"""

import logging
import time
from collections.abc import Callable
from datetime import UTC, date, datetime
from threading import Lock
from typing import Any, Protocol
from uuid import UUID

import httpx
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, LLMResult

from aiops_contracts.usage import LlmUsage, PriceTable, UsageSummary, summarize

log = logging.getLogger(__name__)


class UsageSink(Protocol):
    def record(self, usage: LlmUsage) -> None: ...


class UsageLedger:
    """In-memory sink for tests and API-less local runs."""

    def __init__(self) -> None:
        self._records: list[LlmUsage] = []
        self._lock = Lock()

    def record(self, usage: LlmUsage) -> None:
        with self._lock:
            self._records.append(usage)

    def records(self) -> list[LlmUsage]:
        with self._lock:
            return list(self._records)

    def summary(self, day: date) -> UsageSummary:
        return summarize(self.records(), day)


class ApiUsageSink:
    """Posts each record to the API's internal endpoint.

    The endpoint is idempotent on call_id, so retries are safe. If every
    attempt fails the record is logged in full so it can be replayed.
    """

    def __init__(
        self,
        api_url: str,
        token: str,
        attempts: int = 3,
        client: httpx.Client | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._url = f"{api_url.rstrip('/')}/internal/usage"
        self._headers = {"Authorization": f"Bearer {token}"}
        self._attempts = attempts
        self._client = client or httpx.Client(timeout=2.0)
        self._sleep = sleep

    def record(self, usage: LlmUsage) -> None:
        body = usage.model_dump(mode="json")
        for attempt in range(1, self._attempts + 1):
            try:
                response = self._client.post(self._url, json=body, headers=self._headers)
                if response.status_code < 500:
                    response.raise_for_status()  # 4xx: our bug, retrying will not help
                    return
            except httpx.HTTPStatusError:
                break
            except httpx.TransportError:
                pass
            if attempt < self._attempts:
                self._sleep(0.2 * 2 ** (attempt - 1))
        log.error("Could not record LLM usage after %d attempts: %s", self._attempts, body)


class UsageRecorder(BaseCallbackHandler):
    """Records one LlmUsage per chat-model call, metered or not."""

    def __init__(
        self,
        sink: UsageSink,
        prices: PriceTable,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._sink = sink
        self._prices = prices
        self._clock = clock
        self._context: dict[UUID, dict[str, str | None]] = {}
        self._lock = Lock()

    def on_chat_model_start(
        self,
        serialized: dict[str, Any],
        messages: list[list[Any]],
        *,
        run_id: UUID,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        metadata = metadata or {}
        with self._lock:
            self._context[run_id] = {
                "thread_id": _str_or_none(metadata.get("thread_id")),
                "provider": _str_or_none(metadata.get("ls_provider")),
                "model": _str_or_none(metadata.get("ls_model_name")),
            }

    def on_llm_end(self, response: LLMResult, *, run_id: UUID, **kwargs: Any) -> None:
        with self._lock:
            context = self._context.pop(run_id, {})
        message = _first_message(response)
        model = (
            (_str_or_none(message.response_metadata.get("model_name")) if message else None)
            or context.get("model")
            or "unknown"
        )
        common = {
            "call_id": str(run_id),
            "thread_id": context.get("thread_id"),
            "provider": context.get("provider"),
            "model": model,
            "recorded_at": self._clock(),
        }
        if message is None or message.usage_metadata is None:
            # Streaming responses only carry usage if the provider sends it
            # (e.g. ChatOpenAI needs stream_usage=True). Record the call as
            # unmetered so spend shows as unknown instead of under-reported.
            log.warning("LLM call %s (model %s) reported no token usage", run_id, model)
            self._sink.record(LlmUsage(**common, metered=False))
            return
        usage = message.usage_metadata
        input_tokens, output_tokens = usage["input_tokens"], usage["output_tokens"]
        self._sink.record(
            LlmUsage(
                **common,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=usage.get("total_tokens", input_tokens + output_tokens),
                cost_usd=self._prices.cost_usd(model, input_tokens, output_tokens),
            )
        )

    def on_llm_error(self, error: BaseException, *, run_id: UUID, **kwargs: Any) -> None:
        with self._lock:
            self._context.pop(run_id, None)


def _first_message(response: LLMResult) -> AIMessage | None:
    for generations in response.generations:
        for generation in generations:
            if isinstance(generation, ChatGeneration) and isinstance(generation.message, AIMessage):
                return generation.message
    return None


def _str_or_none(value: object) -> str | None:
    return value if isinstance(value, str) and value else None
