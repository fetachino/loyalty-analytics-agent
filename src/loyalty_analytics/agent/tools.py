import json
from collections.abc import Callable
from typing import Any

from sqlalchemy.orm import Session

from loyalty_analytics.services.analytics import (
    get_loyalty_tiers,
    get_overview,
    get_reward_redemptions,
    get_spending_categories,
)

ToolHandler = Callable[[Session], Any]

TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "name": "get_program_overview",
        "description": (
            "Get program-wide customer, transaction, purchase, points, and redemption KPIs."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "get_loyalty_tier_summary",
        "description": "Get customer counts and point balances grouped by loyalty tier.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "get_spending_by_category",
        "description": "Get transaction counts, spending, and points earned grouped by category.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "get_reward_redemption_summary",
        "description": "Get redemption counts and points used grouped by reward.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        },
        "strict": True,
    },
]

TOOL_HANDLERS: dict[str, ToolHandler] = {
    "get_program_overview": get_overview,
    "get_loyalty_tier_summary": get_loyalty_tiers,
    "get_spending_by_category": get_spending_categories,
    "get_reward_redemption_summary": get_reward_redemptions,
}


def execute_tool(name: str, arguments: str, db: Session) -> str:
    """Validate and execute a registered read-only analytics tool."""
    handler = TOOL_HANDLERS.get(name)
    if handler is None:
        raise ValueError(f"Unknown tool: {name}")

    parsed_arguments = json.loads(arguments)
    if parsed_arguments != {}:
        raise ValueError(f"Tool {name} does not accept arguments")

    result = handler(db)
    if isinstance(result, list):
        payload = [item.model_dump(mode="json") for item in result]
    else:
        payload = result.model_dump(mode="json")
    return json.dumps(payload)
