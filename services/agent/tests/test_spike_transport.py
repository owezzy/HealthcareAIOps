"""The agent speaks AG-UI: a run streams lifecycle and text-message events."""

import json

from fastapi.testclient import TestClient

from aiops_agent.app import create_app


def _run_payload(text: str) -> dict:
    return {
        "threadId": "t-spike",
        "runId": "r-1",
        "state": {},
        "messages": [{"id": "m-1", "role": "user", "content": text}],
        "tools": [],
        "context": [],
        "forwardedProps": {},
    }


def test_run_streams_ag_ui_events_with_the_echo() -> None:
    client = TestClient(create_app())
    with client.stream(
        "POST",
        "/agent",
        json=_run_payload("hello from angular"),
        headers={"accept": "text/event-stream"},
    ) as response:
        assert response.status_code == 200
        events = [
            json.loads(line.removeprefix("data: "))
            for line in response.iter_lines()
            if line.startswith("data: ")
        ]

    types = [e["type"] for e in events]
    assert types[0] == "RUN_STARTED"
    assert types[-1] == "RUN_FINISHED"
    assert "RUN_ERROR" not in types
    text = "".join(e.get("delta", "") for e in events if e["type"] == "TEXT_MESSAGE_CONTENT")
    snapshot = json.dumps([e for e in events if e["type"] == "MESSAGES_SNAPSHOT"])
    assert "Agent received: hello from angular" in text + snapshot
