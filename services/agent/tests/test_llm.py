"""LLM client: one OpenAI-compatible client per provider, streamed usage, structured output."""

import json
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from ag_ui_langgraph import LangGraphAgent, add_langgraph_fastapi_endpoint
from fastapi import FastAPI
from fastapi.testclient import TestClient

from aiops_agent.llm import (
    FakeEchoChatModel,
    ModelConfigError,
    make_chat_model,
    model_from_env,
    structured_findings,
)
from aiops_agent.spike_graph import build_spike_graph
from aiops_agent.usage import UsageLedger, UsageRecorder
from aiops_contracts.catalogue import load_catalogue
from aiops_contracts.findings import parse_findings
from aiops_contracts.usage import ModelPrice, PriceTable

SIM = Path(__file__).resolve().parents[3] / "sim"
NOW = datetime(2026, 11, 18, 12, 0, tzinfo=UTC)
KEYS = {
    "OPENAI_API_KEY": "sk-openai",
    "DEEPSEEK_API_KEY": "sk-deepseek",
    "DASHSCOPE_API_KEY": "sk-qwen",
}
PROVIDER_HOSTS = {
    "openai": ("api.openai.com", "sk-openai"),
    "deepseek": ("api.deepseek.com", "sk-deepseek"),
    "qwen": ("dashscope-intl.aliyuncs.com", "sk-qwen"),
    "ollama": ("localhost:11434", "not-needed"),
}


def _run_over_ag_ui(model, ledger: UsageLedger, thread_id: str) -> list[str]:
    app = FastAPI()
    prices = PriceTable(
        models={
            "fake-provider-model": ModelPrice(input_per_million_usd=1.0, output_per_million_usd=2.0)
        }
    )
    add_langgraph_fastapi_endpoint(
        app=app,
        agent=LangGraphAgent(
            name="default",
            graph=build_spike_graph(model),
            config={"callbacks": [UsageRecorder(ledger, prices, clock=lambda: NOW)]},
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
        "messages": [{"id": "m-1", "role": "user", "content": "hi"}],
    }
    with TestClient(app).stream("POST", "/agent", json=payload) as response:
        assert response.status_code == 200
        return [line for line in response.iter_lines() if line.startswith("data: ")]


# --- configuration --------------------------------------------------------------


@pytest.mark.parametrize(
    ("spec", "message"),
    [
        ("gpt-without-provider", "must look like '<provider>:<model id>'"),
        ("anthropic:some-model", "unknown provider 'anthropic'"),
        ("openai:", "must look like"),
        ("deepseek:some-model", "DEEPSEEK_API_KEY is not set"),
    ],
)
def test_bad_model_configuration_fails_loudly(spec, message) -> None:
    with pytest.raises(ModelConfigError, match=message):
        make_chat_model(spec, env={})


def test_default_model_is_the_keyless_fake() -> None:
    assert isinstance(model_from_env(env={}), FakeEchoChatModel)


def test_base_url_override_wins(fake_openai) -> None:
    env = {**KEYS, "AIOPS_LLM_BASE_URL": "https://dashscope-us.example/compatible-mode/v1"}
    model = make_chat_model("qwen:some-model", env, **fake_openai.clients())
    model.invoke("hi")
    assert fake_openai.requests[0]["url"].startswith("https://dashscope-us.example/")


# --- streamed usage through the AG-UI agent (task acceptance) -------------------


@pytest.mark.parametrize("provider", ["openai", "deepseek", "qwen", "ollama"])
def test_streamed_run_records_metered_usage_for_each_provider(provider, fake_openai) -> None:
    ledger = UsageLedger()
    model = make_chat_model(f"{provider}:some-model", KEYS, **fake_openai.clients())

    events = _run_over_ag_ui(model, ledger, thread_id=f"inc-{provider}")

    [request] = fake_openai.requests
    host, key = PROVIDER_HOSTS[provider]
    assert host in request["url"] and request["auth"] == f"Bearer {key}"
    assert request["body"]["stream"] is True
    assert request["body"]["stream_options"] == {"include_usage": True}
    assert any('"TEXT_MESSAGE_CONTENT"' in e for e in events)

    [usage] = ledger.records()
    assert usage.metered and usage.thread_id == f"inc-{provider}"
    assert (usage.model, usage.input_tokens, usage.output_tokens) == ("fake-provider-model", 42, 7)
    assert usage.cost_usd == 0.000056  # 42 * $1/M + 7 * $2/M
    assert ledger.summary(date(2026, 11, 18)).unmetered_calls == 0


def test_provider_that_ignores_include_usage_is_recorded_unmetered(fake_openai) -> None:
    fake_openai.honour_include_usage = False
    ledger = UsageLedger()
    model = make_chat_model("qwen:some-model", KEYS, **fake_openai.clients())

    _run_over_ag_ui(model, ledger, thread_id="inc-silent")

    [usage] = ledger.records()
    assert not usage.metered
    assert ledger.summary(date(2026, 11, 18)).cost_usd is None


def test_fake_echo_model_streams_metered_usage_without_keys() -> None:
    ledger = UsageLedger()
    events = _run_over_ag_ui(FakeEchoChatModel(), ledger, thread_id="inc-local")

    deltas = [json.loads(e.removeprefix("data: ")) for e in events]
    streamed = "".join(d["delta"] for d in deltas if d["type"] == "TEXT_MESSAGE_CONTENT")
    assert streamed == "Spike OK. Agent received: hi"
    assert sum(d["type"] == "TEXT_MESSAGE_CONTENT" for d in deltas) > 1  # word by word
    [usage] = ledger.records()
    assert usage.metered and usage.model == "fake-echo"


# --- structured output -------------------------------------------------------------


def _valid_findings() -> dict:
    return {
        "incident_id": "INC-1042",
        "summary": "lis is crash-looping on memory.",
        "evidence": [
            {
                "id": "ev_19c2",
                "source": "k8s_event",
                "ref": "events lis",
                "observed_at": "2026-11-17T09:12:00Z",
                "summary": "6 OOMKilled restarts",
            }
        ],
        "confirmed_facts": [{"statement": "LIS restarted 6 times.", "evidence_ids": ["ev_19c2"]}],
        "hypotheses": [],
        "root_cause_rank": None,
        "clinical_impact": "Tier 1: lab results delayed.",
        "missing_information": [],
        "suspected_injection": [],
        "proposals": [
            {
                "action": "restart_deployment",
                "target": "lis",
                "replicas": None,
                "rationale": "Clear crashed pods.",
                "risk": "medium",
                "expected_outcome": "Queue drains.",
                "rollback": None,
                "follow_up": None,
                "evidence_ids": ["ev_19c2"],
            }
        ],
        "escalation": None,
    }


def _assert_strict(schema: dict) -> None:
    """OpenAI strict mode: every object closed with all properties required, no length keywords."""
    if isinstance(schema, dict):
        if schema.get("type") == "object" and "properties" in schema:
            assert schema["additionalProperties"] is False
            assert set(schema["required"]) == set(schema["properties"])
        assert "minLength" not in schema and "default" not in schema
        for key, value in schema.items():
            if key in ("properties", "$defs"):
                for sub in value.values():
                    _assert_strict(sub)
            else:
                _assert_strict(value)
    elif isinstance(schema, list):
        for item in schema:
            _assert_strict(item)


def test_openai_uses_strict_json_schema_and_output_validates(fake_openai) -> None:
    fake_openai.structured = _valid_findings()
    spec = "openai:some-model"
    model = make_chat_model(spec, KEYS, **fake_openai.clients())

    output = structured_findings(model, spec).invoke("Investigate INC-1042")

    response_format = fake_openai.requests[0]["body"]["response_format"]
    assert response_format["type"] == "json_schema"
    assert response_format["json_schema"]["strict"] is True
    _assert_strict(response_format["json_schema"]["schema"])
    findings, errors = parse_findings(output, load_catalogue(SIM / "services.yaml"))
    assert errors == [] and findings.incident_id == "INC-1042"


@pytest.mark.parametrize("provider", ["deepseek", "qwen"])
def test_other_providers_use_tool_calling_and_output_validates(provider, fake_openai) -> None:
    fake_openai.structured = _valid_findings()
    spec = f"{provider}:some-model"
    model = make_chat_model(spec, KEYS, **fake_openai.clients())

    output = structured_findings(model, spec).invoke("Investigate INC-1042")

    body = fake_openai.requests[0]["body"]
    assert body["tools"][0]["function"]["name"] == "Findings"
    assert "response_format" not in body
    findings, errors = parse_findings(output, load_catalogue(SIM / "services.yaml"))
    assert errors == [] and findings.proposals[0].target == "lis"


def test_invalid_structured_output_yields_repair_messages(fake_openai) -> None:
    bad = _valid_findings()
    bad["proposals"][0]["target"] = "ehr-db"
    fake_openai.structured = bad
    spec = "openai:some-model"
    model = make_chat_model(spec, KEYS, **fake_openai.clients())

    output = structured_findings(model, spec).invoke("Investigate INC-1042")

    findings, errors = parse_findings(output, load_catalogue(SIM / "services.yaml"))
    assert findings is None
    assert errors == [
        "proposal 1: restart_deployment cannot target 'ehr-db': it is a database, "
        "not an application"
    ]


def test_ollama_model_ids_keep_their_own_colons(fake_openai) -> None:
    model = make_chat_model("ollama:nemotron-3-nano:30b-cloud", {}, **fake_openai.clients())
    model.invoke("hi")
    assert fake_openai.requests[0]["body"]["model"] == "nemotron-3-nano:30b-cloud"


def test_ollama_uses_non_strict_json_schema(fake_openai) -> None:
    fake_openai.structured = _valid_findings()
    spec = "ollama:some-model:cloud"
    model = make_chat_model(spec, {}, **fake_openai.clients())

    output = structured_findings(model, spec).invoke("Investigate INC-1042")

    response_format = fake_openai.requests[0]["body"]["response_format"]
    assert response_format["type"] == "json_schema"
    assert response_format["json_schema"].get("strict") in (None, False)
    _findings, errors = parse_findings(output, load_catalogue(SIM / "services.yaml"))
    assert errors == []


def test_timeouts_default_per_provider_and_can_be_overridden() -> None:
    assert make_chat_model("openai:m", KEYS).request_timeout == 60.0
    assert make_chat_model("ollama:m", {}).request_timeout == 300.0
    env = {"AIOPS_LLM_TIMEOUT_SECONDS": "15"}
    assert make_chat_model("ollama:m", env).request_timeout == 15.0


def test_ollama_uses_model_sampling_and_no_retries(fake_openai) -> None:
    """Reasoning models loop at temperature 0 (verified with nemotron-3-nano:4b)."""
    ollama = make_chat_model("ollama:m", {}, **fake_openai.clients())
    ollama.invoke("hi")
    assert "temperature" not in fake_openai.requests[0]["body"]
    assert ollama.max_retries == 0

    hosted = make_chat_model("openai:m", KEYS, **fake_openai.clients())
    hosted.invoke("hi")
    assert fake_openai.requests[1]["body"]["temperature"] == 0
