# Loyalty Analytics AI Agent

[![CI](https://github.com/fetachino/loyalty-analytics-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/fetachino/loyalty-analytics-agent/actions/workflows/ci.yml)

Production-oriented backend foundation for a customer loyalty analytics platform. This milestone
contains no AI, LangChain, LangGraph, or LLM functionality.

## Stack

Python 3.12, FastAPI, PostgreSQL, SQLAlchemy 2.x, Alembic, Pydantic v2, Docker Compose,
pytest, Ruff, and mypy.

## Quick start with Docker

Requirements: Docker with Compose v2.

```bash
cp .env.example .env
docker compose up --build -d
docker compose exec api alembic upgrade head
docker compose exec api python scripts/seed.py
docker compose exec api python scripts/create_admin.py --email you@example.com
```

The dashboard is available at <http://localhost:8000>. Interactive OpenAPI documentation is at
<http://localhost:8000/docs>, with the raw schema at <http://localhost:8000/openapi.json>.

Before starting the application, generate a strong signing key and set it as `AUTH_SECRET_KEY` in
your local `.env`. For example, `python -c "import secrets; print(secrets.token_urlsafe(48))"`
prints a suitable value. Never commit the generated key. The administrator command prompts for a
password without echoing it and requires at least 12 characters.

Stop the services with:

```bash
docker compose down
```

Use `docker compose down -v` only when you also want to delete the local database volume.

## Deployment

The repository includes a `render.yaml` Blueprint for deploying the existing Docker image with a
managed PostgreSQL database. It generates the session-signing secret, requires sensitive values to
be entered in Render, runs migrations during startup, bootstraps the first administrator, and
enables HTTPS-only authentication cookies.

See [the deployment guide](docs/deployment.md) for the exact workflow, security requirements, and
free-tier limitations. The included Free PostgreSQL instance expires after 30 days and is intended
only for a portfolio demonstration.

## Local development

Create a Python 3.12 virtual environment and run:

```bash
python -m pip install -e ".[dev]"
cp .env.example .env
```

Set `DATABASE_URL` to a reachable PostgreSQL instance, then:

```bash
alembic upgrade head
python scripts/seed.py
uvicorn loyalty_analytics.main:app --reload
```

The seed is deterministic and replaces existing loyalty data with exactly 100 customers,
1,000 transactions, and 100 reward redemptions. It is intended for development environments.

## API

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/health` | Service health |
| `GET` | `/health/live` | Process liveness probe |
| `GET` | `/health/ready` | Database readiness probe |
| `GET` | `/api/v1/customers` | Paginated customers |
| `GET` | `/api/v1/customers/{id}` | Customer by UUID |
| `GET` | `/api/v1/transactions` | Paginated transactions |
| `GET` | `/api/v1/rewards` | Paginated reward redemptions |
| `GET` | `/api/v1/analytics/overview` | Program-wide KPIs |
| `GET` | `/api/v1/analytics/loyalty-tiers` | Customer and point totals by tier |
| `GET` | `/api/v1/analytics/spending-by-category` | Purchase metrics by category |
| `GET` | `/api/v1/analytics/reward-redemptions` | Redemption metrics by reward |
| `POST` | `/api/v1/agent/query` | Ask a read-only loyalty analytics question |
| `GET` | `/api/v1/agent/history` | List the signed-in user's recent AI analyses |
| `GET` | `/api/v1/exports/summary.csv` | Download program KPIs |
| `GET` | `/api/v1/exports/customers.csv` | Download customer data |
| `GET` | `/api/v1/exports/transactions.csv` | Download transaction data |
| `GET` | `/api/v1/exports/rewards.csv` | Download reward data |
| `POST` | `/api/v1/auth/login` | Start a secure dashboard session |
| `POST` | `/api/v1/auth/logout` | End the current session |
| `GET` | `/api/v1/auth/me` | Get the authenticated user |

Collection endpoints accept `page` (default `1`) and `page_size` (default `20`, maximum `100`).
Responses include `items`, `total`, `page`, `page_size`, and `pages`. Invalid parameters return
FastAPI's structured `422` response; an unknown customer returns `404`.

All customer, transaction, reward, analytics, and AI routes require authentication. Successful
login sets a signed, HttpOnly, SameSite session cookie; passwords are hashed with Argon2 and are
never stored in plaintext. Set `AUTH_COOKIE_SECURE=true` whenever the application is served over
HTTPS. AI questions and answers are retained per user so recent analyses can be revisited from the
dashboard. Health probes and static dashboard assets remain public.

Authenticated users can download streamed CSV reports from the dashboard. Text cells that begin
with spreadsheet formula prefixes are escaped before export to reduce CSV injection risk.

The AI endpoint uses the OpenAI Responses API and only exposes four read-only aggregate analytics
tools. It cannot execute arbitrary SQL, modify data, or retrieve individual customer records. Set
`OPENAI_API_KEY` in your local `.env` to enable it; never commit the key. The model defaults to
`gpt-5.6-sol` and can be overridden with `OPENAI_MODEL`. AI requests are limited per client to 10
requests per 60 seconds by default; configure `AGENT_RATE_LIMIT_REQUESTS` and
`AGENT_RATE_LIMIT_WINDOW_SECONDS` as needed.

```bash
curl -X POST "http://localhost:8000/api/v1/agent/query" \
  -H "Content-Type: application/json" \
  -d '{"question":"Which spending categories generate the most revenue?"}'
```

Example:

```bash
curl "http://localhost:8000/api/v1/customers?page=1&page_size=20"
```

## Quality gates

```bash
make format
make lint
make typecheck
make test
# or all read-only checks:
make check
```

The same formatting, linting, type-checking, and test gates run in GitHub Actions for every pull
request targeting `main` and every push to `main`.

Tests use an isolated in-memory SQLite database; the deployed application uses PostgreSQL.
Schema changes must be made through Alembic migrations.

Every HTTP response includes an `X-Request-ID` correlation header and defensive browser security
headers. Application request logs are emitted as structured JSON with method, path, status, and
duration fields. The Docker API health check uses the database-aware readiness endpoint.

## Project layout

```text
src/loyalty_analytics/  application, configuration, ORM models, schemas, and routes
src/loyalty_analytics/static/ responsive dashboard and AI analyst interface
migrations/             Alembic environment and versioned migrations
scripts/seed.py         deterministic development seed data
scripts/create_admin.py secure interactive administrator setup
scripts/bootstrap_admin.py non-interactive first-deploy administrator setup
docs/deployment.md      hosted deployment runbook
render.yaml             managed service and PostgreSQL deployment Blueprint
tests/                  API and configuration tests
Dockerfile              non-root, multi-stage API image
compose.yaml            API and PostgreSQL services
```
