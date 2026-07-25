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
```

The API is available at <http://localhost:8000>. Interactive OpenAPI documentation is at
<http://localhost:8000/docs>, with the raw schema at <http://localhost:8000/openapi.json>.

Stop the services with:

```bash
docker compose down
```

Use `docker compose down -v` only when you also want to delete the local database volume.

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
| `GET` | `/api/v1/customers` | Paginated customers |
| `GET` | `/api/v1/customers/{id}` | Customer by UUID |
| `GET` | `/api/v1/transactions` | Paginated transactions |
| `GET` | `/api/v1/rewards` | Paginated reward redemptions |
| `GET` | `/api/v1/analytics/overview` | Program-wide KPIs |
| `GET` | `/api/v1/analytics/loyalty-tiers` | Customer and point totals by tier |
| `GET` | `/api/v1/analytics/spending-by-category` | Purchase metrics by category |
| `GET` | `/api/v1/analytics/reward-redemptions` | Redemption metrics by reward |
| `POST` | `/api/v1/agent/query` | Ask a read-only loyalty analytics question |

Collection endpoints accept `page` (default `1`) and `page_size` (default `20`, maximum `100`).
Responses include `items`, `total`, `page`, `page_size`, and `pages`. Invalid parameters return
FastAPI's structured `422` response; an unknown customer returns `404`.

The AI endpoint uses the OpenAI Responses API and only exposes four read-only aggregate analytics
tools. It cannot execute arbitrary SQL, modify data, or retrieve individual customer records. Set
`OPENAI_API_KEY` in your local `.env` to enable it; never commit the key. The model defaults to
`gpt-5.6-sol` and can be overridden with `OPENAI_MODEL`.

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

## Project layout

```text
src/loyalty_analytics/  application, configuration, ORM models, schemas, and routes
migrations/             Alembic environment and versioned migrations
scripts/seed.py         deterministic development seed data
tests/                  API and configuration tests
Dockerfile              non-root, multi-stage API image
compose.yaml            API and PostgreSQL services
```
