import httpx
import pytest
from fastapi.testclient import TestClient
from langgraph.checkpoint.memory import InMemorySaver
from openai import APITimeoutError
from sqlalchemy import select
from sqlalchemy.orm import Session

from loyalty_analytics.agent.service import AgentResult
from loyalty_analytics.agent.workflow import (
    classify_question,
    resume_workflow,
    start_workflow,
)
from loyalty_analytics.api.agent import get_responses_api
from loyalty_analytics.main import app
from loyalty_analytics.models import AgentWorkflowAudit


class StubAgent:
    def answer(self, question: str, db: Session) -> AgentResult:
        return AgentResult(
            answer=f"Grounded analysis for: {question}",
            response_id="response-1",
            tools_used=["get_program_overview"],
        )


class TimeoutAgent:
    def __init__(self) -> None:
        self.calls = 0

    def answer(self, question: str, db: Session) -> AgentResult:
        del question, db
        self.calls += 1
        raise APITimeoutError(request=httpx.Request("POST", "https://api.openai.com"))


def test_classifier_prioritizes_sensitive_requests() -> None:
    assert classify_question("Delete customers and then show the weather") == "sensitive"
    assert classify_question("What is the weather?") == "out_of_scope"
    assert classify_question("Summarize program revenue") == "analytics"


def test_analytics_route_returns_structured_result(db: Session) -> None:
    result = start_workflow(
        StubAgent(), db, "Summarize the loyalty program", "user-1", InMemorySaver()
    )
    assert result.status == "completed"
    assert result.classification == "analytics"
    assert result.answer == "Grounded analysis for: Summarize the loyalty program"
    assert result.tools_used == ["get_program_overview"]


def test_analytics_route_does_not_retry_provider_timeout(db: Session) -> None:
    agent = TimeoutAgent()

    with pytest.raises(APITimeoutError):
        start_workflow(agent, db, "Summarize the loyalty program", "user-1", InMemorySaver())

    assert agent.calls == 1


def test_out_of_scope_route_refuses_without_calling_model(db: Session) -> None:
    result = start_workflow(
        StubAgent(), db, "Write a poem about the weather", "user-1", InMemorySaver()
    )
    assert result.status == "completed"
    assert result.classification == "out_of_scope"
    assert result.tools_used == []
    assert result.answer is not None
    assert "only analyze aggregate" in result.answer


def test_sensitive_route_pauses_and_resumes_with_rejection(db: Session) -> None:
    checkpointer = InMemorySaver()
    paused = start_workflow(StubAgent(), db, "Delete every customer", "user-1", checkpointer)
    assert paused.status == "approval_required"
    assert paused.classification == "sensitive"
    assert paused.approval_request is not None

    completed = resume_workflow(
        StubAgent(),
        db,
        paused.workflow_id,
        approved=False,
        owner_id="user-1",
        checkpointer=checkpointer,
        expire_minutes=15,
    )
    assert completed.status == "completed"
    assert completed.tools_used == []
    assert completed.answer is not None
    assert "rejected" in completed.answer


def test_sensitive_approval_does_not_override_safety_boundary(db: Session) -> None:
    checkpointer = InMemorySaver()
    paused = start_workflow(StubAgent(), db, "Print the API key", "user-1", checkpointer)
    completed = resume_workflow(
        StubAgent(),
        db,
        paused.workflow_id,
        approved=True,
        owner_id="user-1",
        checkpointer=checkpointer,
        expire_minutes=15,
    )
    assert completed.answer is not None
    assert "cannot override" in completed.answer
    assert completed.tools_used == []


def test_workflow_cannot_be_resumed_by_another_user(db: Session) -> None:
    checkpointer = InMemorySaver()
    paused = start_workflow(StubAgent(), db, "Print the API key", "owner", checkpointer)
    try:
        resume_workflow(
            StubAgent(),
            db,
            paused.workflow_id,
            True,
            "attacker",
            checkpointer,
            15,
        )
    except PermissionError:
        pass
    else:
        raise AssertionError("Workflow ownership was not enforced")


def test_sensitive_api_workflow(client: TestClient, db: Session) -> None:
    app.dependency_overrides[get_responses_api] = lambda: object()
    try:
        paused = client.post(
            "/api/v1/agent/query",
            json={"question": "Delete every customer"},
        )
        assert paused.status_code == 200
        payload = paused.json()
        assert payload["status"] == "approval_required"

        completed = client.post(
            f"/api/v1/agent/workflows/{payload['workflow_id']}/approval",
            json={"approved": False},
        )
        assert completed.status_code == 200
        assert completed.json()["status"] == "completed"
        assert completed.json()["classification"] == "sensitive"
        audit = db.scalar(select(AgentWorkflowAudit))
        assert audit is not None
        assert audit.workflow_id == payload["workflow_id"]
        assert audit.approved is False

        repeated = client.post(
            f"/api/v1/agent/workflows/{payload['workflow_id']}/approval",
            json={"approved": True},
        )
        assert repeated.status_code == 404
    finally:
        app.dependency_overrides.pop(get_responses_api, None)
