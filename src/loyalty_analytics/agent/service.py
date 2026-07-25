from dataclasses import dataclass
from typing import Any, Protocol

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from sqlalchemy.orm import Session

from loyalty_analytics.agent.tools import TOOL_DEFINITIONS, execute_tool

AGENT_INSTRUCTIONS = """
You are a loyalty analytics assistant. Answer questions only about the loyalty program data
available through your tools. Always use tools for quantitative claims and never invent values.
The tools are read-only aggregates and contain no individual customer details. If a request asks
for unrelated content, database changes, raw SQL, secrets, or personal customer data, briefly
refuse and explain the supported analytics scope. Keep answers concise, label monetary values,
and state when the available aggregate data cannot answer a question.
""".strip()
tracer = trace.get_tracer(__name__)


class ResponsesAPI(Protocol):
    def create(self, **kwargs: Any) -> Any: ...


class AgentExecutionError(RuntimeError):
    """Raised when the model cannot complete a safe agent turn."""


@dataclass(frozen=True)
class AgentResult:
    answer: str
    response_id: str
    tools_used: list[str]


class LoyaltyAnalyticsAgent:
    def __init__(self, responses_api: ResponsesAPI, model: str, max_turns: int = 5) -> None:
        self._responses_api = responses_api
        self._model = model
        self._max_turns = max_turns

    def answer(self, question: str, db: Session) -> AgentResult:
        with tracer.start_as_current_span("agent.answer") as span:
            span.set_attribute("gen_ai.request.model", self._model)
            span.set_attribute("agent.max_turns", self._max_turns)
            try:
                result = self._answer(question, db)
            except Exception as exc:
                span.record_exception(exc)
                span.set_status(Status(StatusCode.ERROR, type(exc).__name__))
                raise
            span.set_attribute("agent.tools_used", result.tools_used)
            span.set_attribute("agent.tool_count", len(result.tools_used))
            return result

    def _answer(self, question: str, db: Session) -> AgentResult:
        input_items: list[Any] = [{"role": "user", "content": question}]
        tools_used: list[str] = []
        for _ in range(self._max_turns):
            response = self._responses_api.create(
                model=self._model,
                instructions=AGENT_INSTRUCTIONS,
                input=input_items,
                tools=TOOL_DEFINITIONS,
                parallel_tool_calls=False,
                store=False,
            )
            input_items.extend(response.output)
            function_calls = [item for item in response.output if item.type == "function_call"]

            if not function_calls:
                answer = response.output_text.strip()
                if not answer:
                    raise AgentExecutionError("The model returned no answer")
                return AgentResult(
                    answer=answer,
                    response_id=response.id,
                    tools_used=list(dict.fromkeys(tools_used)),
                )

            for call in function_calls:
                with tracer.start_as_current_span(
                    "agent.tool",
                    attributes={"agent.tool.name": call.name},
                ):
                    try:
                        output = execute_tool(call.name, call.arguments, db)
                    except (ValueError, TypeError) as exc:
                        raise AgentExecutionError(
                            "The model requested an invalid tool call"
                        ) from exc
                tools_used.append(call.name)
                input_items.append(
                    {
                        "type": "function_call_output",
                        "call_id": call.call_id,
                        "output": output,
                    }
                )

        raise AgentExecutionError("The agent exceeded its maximum number of tool turns")
