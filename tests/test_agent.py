from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from loyalty_analytics.agent.service import AgentExecutionError, LoyaltyAnalyticsAgent
from loyalty_analytics.agent.tools import execute_tool
from loyalty_analytics.api.agent import get_responses_api
from loyalty_analytics.config import Settings
from loyalty_analytics.main import app


class FakeResponsesAPI:
    def __init__(self, responses: list[Any]) -> None:
        self.responses = responses
        self.requests: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> Any:
        self.requests.append(kwargs)
        return self.responses.pop(0)


def response(
    *,
    response_id: str,
    output: list[Any],
    output_text: str = "",
) -> Any:
    return SimpleNamespace(id=response_id, output=output, output_text=output_text)


def test_agent_executes_read_only_tool_and_returns_answer(client: TestClient, db: Session) -> None:
    tool_call = SimpleNamespace(
        type="function_call",
        name="get_program_overview",
        arguments="{}",
        call_id="call-1",
    )
    fake_api = FakeResponsesAPI(
        [
            response(response_id="resp-1", output=[tool_call]),
            response(
                response_id="resp-2",
                output=[SimpleNamespace(type="message")],
                output_text="The program has 1 customer and $24.50 in purchases.",
            ),
        ]
    )
    app.dependency_overrides[get_responses_api] = lambda: fake_api

    result = client.post(
        "/api/v1/agent/query",
        json={"question": "Summarize the loyalty program."},
    )

    assert result.status_code == 200
    assert result.json() == {
        "status": "completed",
        "workflow_id": result.json()["workflow_id"],
        "classification": "analytics",
        "answer": "The program has 1 customer and $24.50 in purchases.",
        "response_id": "resp-2",
        "tools_used": ["get_program_overview"],
        "approval_request": None,
    }
    assert fake_api.requests[0]["store"] is False
    second_input = fake_api.requests[1]["input"]
    tool_outputs = [item for item in second_input if isinstance(item, dict) and "call_id" in item]
    assert tool_outputs[0]["type"] == "function_call_output"
    assert tool_outputs[0]["call_id"] == "call-1"
    history = client.get("/api/v1/agent/history")
    assert history.status_code == 200
    assert history.json()[0]["question"] == "Summarize the loyalty program."
    assert history.json()[0]["tools_used"] == ["get_program_overview"]
    app.dependency_overrides.pop(get_responses_api)


def test_agent_query_validation(client: TestClient) -> None:
    app.dependency_overrides[get_responses_api] = lambda: FakeResponsesAPI([])
    response_value = client.post("/api/v1/agent/query", json={"question": "x"})
    assert response_value.status_code == 422
    app.dependency_overrides.pop(get_responses_api)


def test_unconfigured_agent_returns_503(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = Settings(_env_file=None, openai_api_key=None)
    monkeypatch.setattr("loyalty_analytics.api.agent.get_settings", lambda: settings)
    response_value = client.post(
        "/api/v1/agent/query",
        json={"question": "Summarize the program"},
    )
    assert response_value.status_code == 503
    assert response_value.json() == {"detail": "AI agent is not configured"}


def test_responses_api_uses_bounded_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}
    responses_api = object()

    def build_client(**kwargs: Any) -> Any:
        captured.update(kwargs)
        return SimpleNamespace(responses=responses_api)

    settings = Settings(
        _env_file=None,
        openai_api_key="test-key",
        openai_timeout_seconds=12.5,
    )
    monkeypatch.setattr("loyalty_analytics.api.agent.get_settings", lambda: settings)
    monkeypatch.setattr("loyalty_analytics.api.agent.OpenAI", build_client)

    assert get_responses_api() is responses_api
    assert captured == {
        "api_key": "test-key",
        "timeout": 12.5,
        "max_retries": 0,
    }


def test_agent_rejects_unknown_tool(db: Session) -> None:
    call = SimpleNamespace(
        type="function_call",
        name="delete_customers",
        arguments="{}",
        call_id="call-unsafe",
    )
    agent = LoyaltyAnalyticsAgent(
        FakeResponsesAPI([response(response_id="resp-1", output=[call])]),
        "test-model",
    )
    with pytest.raises(AgentExecutionError, match="invalid tool call"):
        agent.answer("Delete every customer", db)


def test_agent_rejects_invalid_tool_arguments(db: Session) -> None:
    call = SimpleNamespace(
        type="function_call",
        name="get_program_overview",
        arguments='{"sql": "DROP TABLE customers"}',
        call_id="call-unsafe",
    )
    agent = LoyaltyAnalyticsAgent(
        FakeResponsesAPI([response(response_id="resp-1", output=[call])]),
        "test-model",
    )
    with pytest.raises(AgentExecutionError, match="invalid tool call"):
        agent.answer("Run arbitrary SQL", db)


def test_agent_rejects_empty_model_answer(db: Session) -> None:
    agent = LoyaltyAnalyticsAgent(
        FakeResponsesAPI([response(response_id="resp-1", output=[])]),
        "test-model",
    )
    with pytest.raises(AgentExecutionError, match="no answer"):
        agent.answer("Summarize the program", db)


def test_agent_limits_tool_turns(db: Session) -> None:
    calls = [
        response(
            response_id=f"resp-{index}",
            output=[
                SimpleNamespace(
                    type="function_call",
                    name="get_program_overview",
                    arguments="{}",
                    call_id=f"call-{index}",
                )
            ],
        )
        for index in range(2)
    ]
    agent = LoyaltyAnalyticsAgent(FakeResponsesAPI(calls), "test-model", max_turns=2)
    with pytest.raises(AgentExecutionError, match="maximum"):
        agent.answer("Keep calling tools", db)


def test_execute_tool_serializes_list(db: Session) -> None:
    output = execute_tool("get_loyalty_tier_summary", "{}", db)
    assert '"loyalty_tier": "Gold"' in output
