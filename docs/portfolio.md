# Portfolio case study

## Project summary

Loyalty Analytics AI Agent is a production-style full-stack analytics application built to show
how a Python backend can move beyond CRUD into secure operations, business intelligence, and
carefully constrained generative AI. It is deployed as a live portfolio demonstration with
realistic, deterministic data.

## Product capabilities

- Executive KPIs across customers, revenue, points, and reward redemptions
- Category-level spending analysis and loyalty-tier segmentation
- Reward performance reporting and downloadable CSV exports
- Natural-language questions grounded in approved aggregate analytics
- Secure administrator login and user-specific AI analysis history
- Automated first-deploy migration, administrator reconciliation, and demo-data setup

## Engineering decisions

### Constrain the model instead of trusting generated SQL

The AI analyst exposes four narrow, read-only aggregate tools. The model chooses a tool and
arguments, while application-owned code validates the request and queries the database. This
reduces prompt-injection impact, avoids arbitrary SQL, and prevents access to individual customer
records.

### Use server-side sessions for the browser experience

The dashboard authenticates with a signed HttpOnly cookie instead of storing a bearer token in
browser JavaScript. Passwords use Argon2 hashing, production cookies require HTTPS, and logout
invalidates the browser session.

### Keep deployment reproducible

The Render Blueprint describes the web service and PostgreSQL dependency. Startup applies
Alembic migrations, safely reconciles the configured administrator, and seeds demo data only when
the loyalty tables are empty. Local development follows the same container image and migration
path.

### Favor controlled exports and aggregate analytics

CSV responses stream from the API and neutralize spreadsheet formula prefixes. Analytics
endpoints return intentional business aggregates rather than exposing a general-purpose query
interface.

## Reliability and quality

- Liveness and database-aware readiness probes
- Structured request logs and correlation IDs
- Explicit validation, pagination limits, and consistent HTTP errors
- Unit and integration-style API tests with enforced coverage
- Ruff formatting and linting plus strict mypy validation
- GitHub Actions verification and production image build
- Non-root, multi-stage Docker image

## Tradeoffs and next steps

The hosted portfolio uses free-tier infrastructure, so cold starts and database lifetime are
acceptable demo constraints rather than production service-level guarantees. Rate limiting is
process-local; a scaled deployment should move counters and session revocation to Redis. A
multi-tenant product should add organization-scoped authorization and row-level access controls.
Production ingestion would also move from deterministic seed data to validated background jobs.

## Résumé bullets

- Built and deployed a Python 3.12/FastAPI loyalty intelligence platform with PostgreSQL,
  SQLAlchemy 2.x, Alembic, Docker, and an authenticated responsive analytics dashboard.
- Designed a constrained AI analyst using the OpenAI Responses API and four read-only aggregate
  tools, preventing arbitrary SQL and access to individual customer records.
- Implemented Argon2 authentication, signed HttpOnly sessions, rate limiting, CSV-injection
  defenses, security headers, structured logging, and request correlation IDs.
- Automated CI quality gates for Ruff, strict mypy, pytest coverage, and production container
  builds, with repeatable Render Blueprint deployment and database bootstrapping.

## LinkedIn project description

Built and deployed Loyalty Analytics AI Agent, a production-style portfolio application for
customer loyalty intelligence. The platform combines a Python 3.12/FastAPI API, PostgreSQL,
SQLAlchemy, Alembic, Docker, secure administrator authentication, responsive analytics, CSV
reporting, and a constrained OpenAI-powered analyst. The AI layer can use only approved aggregate
tools—not arbitrary SQL or individual customer data. The repository includes automated tests,
coverage enforcement, strict typing, linting, CI container builds, health probes, structured
logging, and a repeatable Render deployment.

## Interview talking points

1. **Why tool calling?** It keeps data access in deterministic application code and gives the
   model only the minimum capabilities needed for useful analysis.
2. **Why migrations plus startup bootstrap?** Migrations preserve schema history; idempotent
   bootstrap logic makes ephemeral demo deployment reliable without overwriting existing data.
3. **How is authentication protected?** Argon2 hashes passwords, HttpOnly cookies keep session
   credentials out of JavaScript, and production enforces secure cookies over HTTPS.
4. **What would change at scale?** Add Redis-backed rate limiting and revocation, organization
   authorization, background ingestion, metrics/tracing, managed secret rotation, and paid
   infrastructure with backups and service-level objectives.
5. **What makes it production-oriented?** The project treats testing, typing, migrations,
   observability, security, container hardening, deployment, and recovery as core features.
