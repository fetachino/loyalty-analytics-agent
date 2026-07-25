import uuid
from typing import Any, Literal, Protocol, TypedDict, cast

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, Interrupt, RetryPolicy, interrupt
from openai import APIConnectionError, APITimeoutError, RateLimitError
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from loyalty_analytics.agent.service import AgentResult

Classification = Literal["analytics", "sensitive", "out_of_scope"]
SENSITIVE_TERMS = (
    "delete",
    "drop table",
    "update ",
    "change ",
    "add points",
    "password",
    "api key",
    "secret",
    "email address",
    "customer name",
    "personal data",
    "raw sql",
    "export database",
)
OUT_OF_SCOPE_TERMS = (
    "weather",
    "stock",
    "medical",
    "diagnose",
    "lawsuit",
    "poem",
    "political news",
    "web scraper",
)
REFUSAL = (
    "I can only analyze aggregate loyalty-program data. I cannot perform database writes, "
    "run arbitrary SQL, disclose secrets, or reveal individual customer information."
)


class WorkflowState(TypedDict, total=False):
    question: str
    owner_id: str
    classification: Classification
    approved: bool
    answer: str
    response_id: str
    tools_used: list[str]


class WorkflowResult(BaseModel):
    status: Literal["completed", "approval_required"]
    workflow_id: str
    classification: Classification
    answer: str | None = None
    response_id: str | None = None
    tools_used: list[str] = Field(default_factory=list)
    approval_request: str | None = None


CHECKPOINTER = InMemorySaver()


class AnalyticsAgent(Protocol):
    def answer(self, question: str, db: Session) -> AgentResult: ...


def classify_question(question: str) -> Classification:
    normalized = question.casefold()
    if any(term in normalized for term in SENSITIVE_TERMS):
        return "sensitive"
    if any(term in normalized for term in OUT_OF_SCOPE_TERMS):
        return "out_of_scope"
    return "analytics"


def _route(state: WorkflowState) -> Classification:
    return state["classification"]


def build_workflow(agent: AnalyticsAgent, db: Session) -> Any:
    def classify_node(state: WorkflowState) -> WorkflowState:
        return {"classification": classify_question(state["question"])}

    def analyze_node(state: WorkflowState) -> WorkflowState:
        result = agent.answer(state["question"], db)
        return {
            "answer": result.answer,
            "response_id": result.response_id,
            "tools_used": result.tools_used,
        }

    def approval_node(state: WorkflowState) -> WorkflowState:
        approved = cast(
            bool,
            interrupt(
                {
                    "type": "sensitive_request",
                    "message": (
                        "This request may involve data modification, secrets, or personal data. "
                        "Approve only to record a reviewed refusal; approval grants no access."
                    ),
                }
            ),
        )
        prefix = (
            "The request was reviewed, but approval cannot override the read-only boundary."
            if approved
            else "The sensitive request was rejected."
        )
        return {
            "approved": approved,
            "answer": f"{prefix} {REFUSAL}",
            "response_id": f"workflow-{uuid.uuid4()}",
            "tools_used": [],
        }

    def refuse_node(state: WorkflowState) -> WorkflowState:
        del state
        return {
            "answer": REFUSAL,
            "response_id": f"workflow-{uuid.uuid4()}",
            "tools_used": [],
        }

    builder = StateGraph(WorkflowState)
    builder.add_node("classify", classify_node)
    builder.add_node(
        "analyze",
        analyze_node,
        retry_policy=RetryPolicy(
            max_attempts=3,
            retry_on=(APIConnectionError, APITimeoutError, RateLimitError),
        ),
    )
    builder.add_node("approval", approval_node)
    builder.add_node("refuse", refuse_node)
    builder.add_edge(START, "classify")
    builder.add_conditional_edges(
        "classify",
        _route,
        {
            "analytics": "analyze",
            "sensitive": "approval",
            "out_of_scope": "refuse",
        },
    )
    builder.add_edge("analyze", END)
    builder.add_edge("approval", END)
    builder.add_edge("refuse", END)
    return builder.compile(checkpointer=CHECKPOINTER)


def start_workflow(
    agent: AnalyticsAgent,
    db: Session,
    question: str,
    owner_id: str,
) -> WorkflowResult:
    thread_id = str(uuid.uuid4())
    graph = build_workflow(agent, db)
    state = cast(
        dict[str, object],
        graph.invoke(
            {"question": question, "owner_id": owner_id},
            config={"configurable": {"thread_id": thread_id}},
        ),
    )
    return _result(thread_id, state)


def resume_workflow(
    agent: AnalyticsAgent,
    db: Session,
    workflow_id: str,
    approved: bool,
    owner_id: str,
) -> WorkflowResult:
    graph = build_workflow(agent, db)
    config = {"configurable": {"thread_id": workflow_id}}
    snapshot = graph.get_state(config)
    if not snapshot.values:
        raise KeyError(workflow_id)
    if snapshot.values.get("owner_id") != owner_id:
        raise PermissionError(workflow_id)
    state = cast(
        dict[str, object],
        graph.invoke(
            Command(resume=approved),
            config=config,
        ),
    )
    return _result(workflow_id, state)


def _result(workflow_id: str, state: dict[str, object]) -> WorkflowResult:
    interrupts = cast(tuple[Interrupt, ...], state.get("__interrupt__", ()))
    classification = cast(Classification, state["classification"])
    if interrupts:
        value = cast(dict[str, str], interrupts[0].value)
        return WorkflowResult(
            status="approval_required",
            workflow_id=workflow_id,
            classification=classification,
            approval_request=value["message"],
        )
    return WorkflowResult(
        status="completed",
        workflow_id=workflow_id,
        classification=classification,
        answer=cast(str, state["answer"]),
        response_id=cast(str, state["response_id"]),
        tools_used=cast(list[str], state.get("tools_used", [])),
    )
