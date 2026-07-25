# LangGraph agent workflow

## Flow

```mermaid
flowchart LR
    Start --> Classify
    Classify -->|analytics| Analyze
    Classify -->|out of scope| Refuse
    Classify -->|sensitive| Approval
    Analyze --> End
    Refuse --> End
    Approval -->|approve or reject| SafeRefusal[Reviewed safe refusal]
    SafeRefusal --> End
```

The classifier applies deterministic safety rules before any model request. Sensitive indicators
take precedence over unrelated-topic indicators so mixed prompt-injection requests cannot bypass
the approval boundary.

## Routes

- `analytics` invokes the existing constrained tool-calling agent. Only four read-only aggregate
  tools are available.
- `out_of_scope` returns a refusal without making a paid model request.
- `sensitive` uses a LangGraph interrupt to pause the workflow and return an approval request to
  the authenticated dashboard.

The browser presents the approval request and resumes the same workflow with the administrator's
decision. Workflow ownership is bound to the authenticated user and checked on resume. Approval
records that a human reviewed the request; it deliberately does not unlock
database writes, arbitrary SQL, secrets, or customer-level personal data.

## Reliability

The analytics node retries OpenAI connection errors, timeouts, and rate limits up to three total
attempts using LangGraph's `RetryPolicy`. Validation errors and safety-boundary violations are not
retried.

Every API result follows a structured schema with:

- workflow status and identifier;
- classification;
- answer and provider response identifier when complete;
- tools used;
- approval message when paused.

## Durable persistence

Production uses LangGraph's PostgreSQL checkpointer, so paused approvals survive service restarts
and can resume on another application replica. The saver initializes its own checkpoint schema
idempotently and strict MessagePack deserialization is enabled in deployment configuration.

Each workflow is bound to its authenticated user and expires after 15 minutes by default. Approval
and rejection decisions are written to `agent_workflow_audit`; completed checkpoint state is then
deleted to prevent replay. Tests use an isolated in-memory saver and never depend on PostgreSQL.
