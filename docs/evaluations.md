# Agent evaluation and observability

## Evaluation strategy

The versioned golden set in `evals/loyalty_agent_cases.jsonl` covers normal analytics, destructive
requests, personal-data requests, prompt injection, secret extraction, and unrelated questions.
Each case declares expected tools, answer-versus-refusal behavior, required facts, and forbidden
output patterns.

Deterministic scoring measures:

- exact tool selection, ignoring call order and duplicates;
- presence of required evidence in the final answer;
- refusal of unsafe or out-of-scope requests without tool execution;
- absence of case-specific prohibited output patterns.

These checks are inexpensive, repeatable, and run on every pull request. The scorer is deliberately
strict so regressions are visible instead of averaged away.

## LLM judge

`judge_candidate` provides an optional second opinion for semantic grounding, relevance, and
safety. It uses the OpenAI Responses API with the `JudgeScore` Pydantic schema as a Structured
Output and disables response storage. Candidate questions and answers are explicitly treated as
untrusted data to reduce judge prompt injection.

The judge is not a CI gate because model calls cost money and introduce nondeterminism. A production
evaluation run should record the model snapshot, dataset commit, individual scores, aggregate pass
rates, latency, and token usage. Human review remains necessary for failed cases and a sampled set
of passes.

## Tracing

Agent turns and analytics tool calls emit OpenTelemetry spans. Set:

```text
OTEL_EXPORTER_OTLP_ENDPOINT=https://your-collector.example/v1/traces
OTEL_SERVICE_NAME=loyalty-analytics-agent
```

When the endpoint is absent, the OpenTelemetry API remains a no-op. Traces include model name, tool
names, tool count, errors, and turn limits. Questions, answers, tool payloads, credentials, and
customer records are intentionally excluded from span attributes.

## Running checks

```bash
python scripts/run_evals.py --validate
pytest tests/test_evaluations.py
```

## Current limitations

- The committed CI suite validates contracts and deterministic scoring but does not make paid model
  calls.
- String-based evidence checks are intentionally conservative and should be supplemented by the
  structured judge and human review.
- OTLP exporter authentication and sampling are deployment concerns and must be configured at the
  collector or environment level.
- Evaluation thresholds should be baselined on repeated runs before they block production releases.
