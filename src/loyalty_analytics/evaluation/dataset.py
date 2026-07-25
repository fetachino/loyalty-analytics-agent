import json
from collections.abc import Iterator
from pathlib import Path

from pydantic import ValidationError

from loyalty_analytics.evaluation.models import EvaluationCase


def load_cases(path: Path) -> list[EvaluationCase]:
    cases: list[EvaluationCase] = []
    seen: set[str] = set()
    with path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            if not line.strip():
                continue
            try:
                case = EvaluationCase.model_validate_json(line)
            except (ValidationError, json.JSONDecodeError) as exc:
                raise ValueError(f"Invalid evaluation case on line {line_number}") from exc
            if case.id in seen:
                raise ValueError(f"Duplicate evaluation case id: {case.id}")
            seen.add(case.id)
            cases.append(case)
    if not cases:
        raise ValueError("Evaluation dataset is empty")
    return cases


def iter_cases(path: Path) -> Iterator[EvaluationCase]:
    yield from load_cases(path)
