"""A fake OpenAI-compatible chat endpoint, plugged into ChatOpenAI's HTTP clients.

It speaks the real wire format, so tests exercise the actual client code:
request building (stream_options, response_format, tools) and response
parsing (SSE chunks, the trailing usage chunk, tool calls).
"""

import json
from dataclasses import dataclass, field
from typing import Any, ClassVar

import httpx
import pytest


@dataclass
class FakeOpenAI:
    reply: str = "Hello from the fake provider"
    model_name: str = "fake-provider-model"
    #: Send the usage chunk when the client asks for it (stream_options.include_usage).
    honour_include_usage: bool = True
    #: Non-streamed replies: JSON content (json_schema) or a tool call (function_calling).
    structured: dict[str, Any] | None = None
    requests: list[dict[str, Any]] = field(default_factory=list)

    usage: ClassVar[dict[str, int]] = {
        "prompt_tokens": 42,
        "completion_tokens": 7,
        "total_tokens": 49,
    }

    def handler(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        self.requests.append(
            {"url": str(request.url), "auth": request.headers.get("authorization"), "body": body}
        )
        if body.get("stream"):
            return self._stream(body)
        return httpx.Response(200, json=self._completion(body))

    def _chunk(self, delta: dict, finish: str | None = None) -> dict:
        return {
            "id": "c1",
            "object": "chat.completion.chunk",
            "created": 0,
            "model": self.model_name,
            "choices": [{"index": 0, "delta": delta, "finish_reason": finish}],
        }

    def _stream(self, body: dict) -> httpx.Response:
        words = self.reply.split(" ")
        events = [self._chunk({"role": "assistant", "content": ""})]
        events += [
            self._chunk({"content": w if i == len(words) - 1 else f"{w} "})
            for i, w in enumerate(words)
        ]
        events.append(self._chunk({}, finish="stop"))
        wants_usage = (body.get("stream_options") or {}).get("include_usage")
        if wants_usage and self.honour_include_usage:
            events.append(
                {
                    "id": "c1",
                    "object": "chat.completion.chunk",
                    "created": 0,
                    "model": self.model_name,
                    "choices": [],
                    "usage": self.usage,
                }
            )
        text = "".join(f"data: {json.dumps(e)}\n\n" for e in events) + "data: [DONE]\n\n"
        return httpx.Response(
            200, content=text.encode(), headers={"content-type": "text/event-stream"}
        )

    def _completion(self, body: dict) -> dict:
        message: dict[str, Any] = {"role": "assistant", "content": self.reply}
        if self.structured is not None:
            if body.get("tools"):
                name = body["tools"][0]["function"]["name"]
                message = {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "type": "function",
                            "function": {"name": name, "arguments": json.dumps(self.structured)},
                        }
                    ],
                }
            else:
                message = {"role": "assistant", "content": json.dumps(self.structured)}
        return {
            "id": "c1",
            "object": "chat.completion",
            "created": 0,
            "model": self.model_name,
            "choices": [{"index": 0, "message": message, "finish_reason": "stop"}],
            "usage": self.usage,
        }

    def clients(self) -> dict[str, Any]:
        transport = httpx.MockTransport(self.handler)
        return {
            "http_client": httpx.Client(transport=transport),
            "http_async_client": httpx.AsyncClient(transport=transport),
        }


@pytest.fixture
def fake_openai() -> FakeOpenAI:
    return FakeOpenAI()
