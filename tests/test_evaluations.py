from pathlib import Path
from types import SimpleNamespace
from typing import Any

from loyalty_analytics.evaluation.dataset import load_cases
from loyalty_analytics.evaluation.judge import judge_candidate
from loyalty_analytics.evaluation.models import CandidateAnswer, JudgeScore
from loyalty_analytics.evaluation.scoring import score_candidate


class FakeParseAPI:
    def __init__(self, score: JudgeScore) -> None:
        self.score = score
        self.request: dict[str, Any] = {}

    def parse(self, **kwargs: Any) -> Any:
        self.request = kwargs
        return SimpleNamespace(output_parsed=self.score)


def test_golden_dataset_has_broad_unique_coverage() -> None:
    cases = load_cases(Path("evals/loyalty_agent_cases.jsonl"))
    assert len(cases) >= 30
    assert len({case.id for case in cases}) == len(cases)
    assert {case.category for case in cases} == {"analytics", "safety", "scope"}
    assert sum(case.expected_behavior == "refuse" for case in cases) >= 10


def test_deterministic_score_passes_grounded_answer() -> None:
    case = load_cases(Path("evals/loyalty_agent_cases.jsonl"))[0]
    score = score_candidate(
        case,
        CandidateAnswer(
            answer="The program has 100 customers and 1,000 transactions.",
            tools_used=["get_program_overview"],
        ),
    )
    assert score.passed
    assert score.failures == []


def test_deterministic_score_reports_tool_and_grounding_failures() -> None:
    case = load_cases(Path("evals/loyalty_agent_cases.jsonl"))[0]
    score = score_candidate(
        case,
        CandidateAnswer(answer="Everything looks excellent.", tools_used=[]),
    )
    assert not score.passed
    assert score.tool_selection == 0
    assert score.grounding == 0
    assert len(score.failures) == 2


def test_deterministic_score_requires_safe_refusal() -> None:
    case = next(
        case
        for case in load_cases(Path("evals/loyalty_agent_cases.jsonl"))
        if case.id == "safety-api-key"
    )
    unsafe = score_candidate(
        case,
        CandidateAnswer(answer="The key is sk-proj-not-a-real-key-value", tools_used=[]),
    )
    safe = score_candidate(
        case,
        CandidateAnswer(
            answer="I cannot provide secrets; I only support aggregate analytics.",
            tools_used=[],
        ),
    )
    assert not unsafe.passed
    assert safe.passed


def test_judge_uses_pydantic_structured_output_without_storage() -> None:
    score = JudgeScore(
        grounded=True,
        relevant=True,
        safe=True,
        score=5,
        rationale="All claims match the expected evidence.",
    )
    api = FakeParseAPI(score)
    case = load_cases(Path("evals/loyalty_agent_cases.jsonl"))[0]
    result = judge_candidate(
        api,
        "judge-model",
        case,
        CandidateAnswer(
            answer="The program has customers and transactions.",
            tools_used=["get_program_overview"],
        ),
    )
    assert result == score
    assert api.request["text_format"] is JudgeScore
    assert api.request["store"] is False
