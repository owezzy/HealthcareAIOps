"""Chat model configuration for OpenAI, DeepSeek and Qwen (ADR-0008).

All three are reached through one OpenAI-compatible client (LangChain
`ChatOpenAI`), so a model is configuration, not code:

    AIOPS_LLM_MODEL=<provider>:<model id>      e.g. openai:<model>, qwen:<model>, ollama:<model>
                                               (Ollama: local daemon; cloud models need credits)
    AIOPS_LLM_MODEL=fake:echo                  local development and tests (default)

Every client streams with `stream_usage=True`: runs stream over AG-UI, and a
streamed response only reports token usage when the client asks for it. A
provider that still sends none is recorded as unmetered (aiops_agent.usage).

Exact model versions are pinned in ADR-0008 when the first eval runs; this
module deliberately ships no default real model.
"""

import os
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from typing import Any, Literal

import httpx
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage, HumanMessage
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult
from langchain_core.runnables import Runnable
from langchain_openai import ChatOpenAI

from aiops_contracts.findings import Findings
from aiops_contracts.schema import strict_json_schema

DEFAULT_MODEL = "fake:echo"
StructuredMethod = Literal["json_schema", "function_calling"]


@dataclass(frozen=True)
class Provider:
    name: str
    base_url: str | None  # None: the client library's default (OpenAI)
    #: None: the provider needs no key (a local Ollama daemon).
    api_key_env: str | None
    #: json_schema where the provider supports it; tool calling otherwise.
    structured_method: StructuredMethod
    #: Ask the provider to enforce the schema exactly (only where it is documented to).
    strict: bool = False
    #: Per-request timeout. Local models on a laptop need far longer than hosted APIs.
    timeout_seconds: float = 60.0
    #: None: the model's own recommended sampling. Reasoning models loop at 0.
    temperature: float | None = 0.0
    #: Client retries. A local server handles one request at a time and keeps
    #: generating for an abandoned one, so retries only queue behind it.
    max_retries: int = 2


PROVIDERS: dict[str, Provider] = {
    "openai": Provider("openai", None, "OPENAI_API_KEY", "json_schema", strict=True),
    "deepseek": Provider(
        "deepseek", "https://api.deepseek.com", "DEEPSEEK_API_KEY", "function_calling"
    ),
    "qwen": Provider(
        "qwen",
        "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
        "DASHSCOPE_API_KEY",
        "function_calling",
    ),
    # Ollama's OpenAI-compatible API on the local daemon. Cloud models
    # (`*:cloud`) are proxied by the daemon and billed as Ollama credits.
    "ollama": Provider(
        "ollama",
        "http://localhost:11434/v1",
        None,
        "json_schema",
        timeout_seconds=300.0,
        temperature=None,
        max_retries=0,
    ),
}


class ModelConfigError(ValueError):
    """The configured model cannot be built (bad spec or missing key)."""


@dataclass(frozen=True)
class ModelSpec:
    provider: str
    model: str

    @classmethod
    def parse(cls, spec: str) -> ModelSpec:
        provider, sep, model = spec.partition(":")
        if not sep or not model:
            raise ModelConfigError(f"model must look like '<provider>:<model id>', got {spec!r}")
        if provider != "fake" and provider not in PROVIDERS:
            known = ", ".join(["fake", *PROVIDERS])
            raise ModelConfigError(f"unknown provider {provider!r}; known: {known}")
        return cls(provider, model)


def make_chat_model(
    spec: str,
    env: Mapping[str, str] = os.environ,
    http_client: httpx.Client | None = None,
    http_async_client: httpx.AsyncClient | None = None,
) -> BaseChatModel:
    """Build the chat model for `<provider>:<model id>`.

    `AIOPS_LLM_BASE_URL` overrides the provider's endpoint (other regions, proxies).
    """
    parsed = ModelSpec.parse(spec)
    if parsed.provider == "fake":
        return FakeEchoChatModel()
    provider = PROVIDERS[parsed.provider]
    if provider.api_key_env is None:
        api_key = "not-needed"  # the client library insists on a value
    else:
        api_key = env.get(provider.api_key_env, "")
        if not api_key:
            raise ModelConfigError(f"{provider.api_key_env} is not set for {spec!r}")
    return ChatOpenAI(
        model=parsed.model,
        api_key=api_key,
        base_url=env.get("AIOPS_LLM_BASE_URL") or provider.base_url,
        stream_usage=True,
        temperature=provider.temperature,
        timeout=float(env.get("AIOPS_LLM_TIMEOUT_SECONDS") or provider.timeout_seconds),
        max_retries=provider.max_retries,
        http_client=http_client,
        http_async_client=http_async_client,
    )


def model_from_env(env: Mapping[str, str] = os.environ) -> BaseChatModel:
    return make_chat_model(env.get("AIOPS_LLM_MODEL", DEFAULT_MODEL), env)


def structured_findings(model: BaseChatModel, spec: str) -> Runnable:
    """A runnable that returns raw Findings JSON (as a dict) from the model.

    Validate the result with `aiops_contracts.findings.parse_findings`:
    provider-side enforcement is a convenience, the contract is the authority.
    """
    provider = PROVIDERS.get(ModelSpec.parse(spec).provider)
    method = provider.structured_method if provider else "json_schema"
    strict = provider.strict if provider else False
    schema = {
        "title": "Findings",
        "description": "Typed findings for one incident investigation.",
        **strict_json_schema(Findings),
    }
    return model.with_structured_output(schema, method=method, strict=strict)


class FakeEchoChatModel(BaseChatModel):
    """Deterministic local model: echoes the last user message, streaming word by word.

    Reports usage like a correctly configured provider, so the usage and
    budget path is exercised without API keys. Priced at zero in
    config/model-prices.yaml.
    """

    model_name: str = "fake-echo"

    @property
    def _llm_type(self) -> str:
        return "fake-echo"

    def _reply(self, messages: list[BaseMessage]) -> str:
        last = next((m for m in reversed(messages) if isinstance(m, HumanMessage)), None)
        return f"Spike OK. Agent received: {last.text if last else '(no message)'}"

    def _usage(self, messages: list[BaseMessage], reply: str) -> dict[str, int]:
        input_tokens = sum(len(m.text.split()) for m in messages)
        output_tokens = len(reply.split())
        return {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
        }

    def _generate(
        self, messages: list[BaseMessage], stop: Any = None, run_manager: Any = None, **kwargs: Any
    ) -> ChatResult:
        reply = self._reply(messages)
        message = AIMessage(
            content=reply,
            response_metadata={"model_name": self.model_name},
            usage_metadata=self._usage(messages, reply),
        )
        return ChatResult(generations=[ChatGeneration(message=message)])

    def _stream(
        self, messages: list[BaseMessage], stop: Any = None, run_manager: Any = None, **kwargs: Any
    ) -> Iterator[ChatGenerationChunk]:
        reply = self._reply(messages)
        words = reply.split(" ")
        for index, word in enumerate(words):
            text = word if index == len(words) - 1 else f"{word} "
            chunk = ChatGenerationChunk(message=AIMessageChunk(content=text))
            if run_manager:
                run_manager.on_llm_new_token(text, chunk=chunk)
            yield chunk
        yield ChatGenerationChunk(
            message=AIMessageChunk(
                content="",
                response_metadata={"model_name": self.model_name},
                usage_metadata=self._usage(messages, reply),
            )
        )
