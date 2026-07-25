from typing import Annotated, cast

from fastapi import APIRouter, Depends, HTTPException, Query, status
from openai import OpenAI, OpenAIError
from sqlalchemy import select

from loyalty_analytics.agent.service import (
    AgentExecutionError,
    LoyaltyAnalyticsAgent,
    ResponsesAPI,
)
from loyalty_analytics.agent.workflow import resume_workflow, start_workflow
from loyalty_analytics.api.auth import CurrentUser, get_current_user
from loyalty_analytics.api.dependencies import DatabaseSession
from loyalty_analytics.config import get_settings
from loyalty_analytics.models import AgentQueryHistory
from loyalty_analytics.rate_limit import enforce_agent_rate_limit
from loyalty_analytics.schemas import AgentApproval, AgentHistoryRead, AgentQuery, AgentResponse

router = APIRouter(
    prefix="/api/v1/agent",
    tags=["AI Agent"],
    dependencies=[Depends(get_current_user)],
)


def get_responses_api() -> ResponsesAPI:
    settings = get_settings()
    if settings.openai_api_key is None or not settings.openai_api_key.get_secret_value():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI agent is not configured",
        )
    responses = OpenAI(api_key=settings.openai_api_key.get_secret_value()).responses
    return cast(ResponsesAPI, responses)


ResponsesDependency = Annotated[ResponsesAPI, Depends(get_responses_api)]


@router.post(
    "/query",
    response_model=AgentResponse,
    summary="Ask a read-only question about loyalty analytics",
)
def query_agent(
    query: AgentQuery,
    db: DatabaseSession,
    responses_api: ResponsesDependency,
    user: CurrentUser,
    _: None = Depends(enforce_agent_rate_limit),
) -> AgentResponse:
    settings = get_settings()
    agent = LoyaltyAnalyticsAgent(responses_api, settings.openai_model)
    try:
        result = start_workflow(agent, db, query.question, str(user.id))
    except AgentExecutionError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI agent could not complete the request",
        ) from exc
    except OpenAIError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI provider request failed",
        ) from exc
    response = AgentResponse.model_validate(result, from_attributes=True)
    if response.status == "approval_required":
        return response
    assert response.answer is not None
    assert response.response_id is not None
    db.add(
        AgentQueryHistory(
            user_id=user.id,
            question=query.question,
            answer=response.answer,
            response_id=response.response_id,
            tools_used=response.tools_used,
        )
    )
    db.commit()
    return response


@router.post(
    "/workflows/{workflow_id}/approval",
    response_model=AgentResponse,
    summary="Approve or reject a paused sensitive request",
)
def approve_agent_workflow(
    workflow_id: str,
    approval: AgentApproval,
    db: DatabaseSession,
    responses_api: ResponsesDependency,
    user: CurrentUser,
) -> AgentResponse:
    settings = get_settings()
    agent = LoyaltyAnalyticsAgent(responses_api, settings.openai_model)
    try:
        result = resume_workflow(agent, db, workflow_id, approval.approved, str(user.id))
    except (KeyError, PermissionError) as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent workflow was not found or has expired",
        ) from exc
    response = AgentResponse.model_validate(result, from_attributes=True)
    assert response.answer is not None
    assert response.response_id is not None
    db.add(
        AgentQueryHistory(
            user_id=user.id,
            question="[Sensitive request reviewed]",
            answer=response.answer,
            response_id=response.response_id,
            tools_used=response.tools_used,
        )
    )
    db.commit()
    return response


@router.get("/history", response_model=list[AgentHistoryRead])
def query_history(
    db: DatabaseSession,
    user: CurrentUser,
    limit: int = Query(default=10, ge=1, le=50),
) -> list[AgentQueryHistory]:
    statement = (
        select(AgentQueryHistory)
        .where(AgentQueryHistory.user_id == user.id)
        .order_by(AgentQueryHistory.created_at.desc())
        .limit(limit)
    )
    return list(db.scalars(statement))
