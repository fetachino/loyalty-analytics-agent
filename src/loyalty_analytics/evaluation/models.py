from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class EvaluationCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]+$")
    category: Literal["analytics", "safety", "scope"]
    question: str = Field(min_length=5)
    expected_tools: list[str]
    expected_behavior: Literal["answer", "refuse"]
    required_facts: list[str] = Field(default_factory=list)
    forbidden_patterns: list[str] = Field(default_factory=list)


class CandidateAnswer(BaseModel):
    answer: str
    tools_used: list[str]


class DeterministicScore(BaseModel):
    tool_selection: float
    grounding: float
    safety: float
    passed: bool
    failures: list[str]


class JudgeScore(BaseModel):
    grounded: bool
    relevant: bool
    safe: bool
    score: int = Field(ge=1, le=5)
    rationale: str
