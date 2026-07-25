import argparse
from pathlib import Path

from loyalty_analytics.evaluation.dataset import load_cases


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate the versioned agent evaluation set.")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("evals/loyalty_agent_cases.jsonl"),
    )
    parser.add_argument("--validate", action="store_true", required=True)
    args = parser.parse_args()
    cases = load_cases(args.dataset)
    categories = sorted({case.category for case in cases})
    print(f"Validated {len(cases)} evaluation cases across: {', '.join(categories)}")


if __name__ == "__main__":
    main()
