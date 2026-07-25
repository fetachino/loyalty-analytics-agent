# Changelog

All notable changes to this project are documented here.

## Unreleased

### Added

- Versioned 36-case agent evaluation dataset covering analytics, safety, and scope
- Deterministic tool-selection, grounding, refusal, and prohibited-output scoring
- Optional Pydantic Structured Output judge for semantic evaluation
- OpenTelemetry spans for agent turns and read-only tool execution
- CI validation and an evaluation and observability runbook

## 1.0.0 - 2026-07-25

### Added

- FastAPI REST resources for customers, transactions, and reward redemptions
- PostgreSQL persistence with SQLAlchemy 2.x and Alembic migrations
- Aggregate loyalty analytics, pagination, validation, and CSV exports
- Constrained OpenAI-powered analyst with read-only tools and per-user history
- Responsive executive dashboard and secure administrator authentication
- Deterministic demo data for 100 customers, 1,000 transactions, and 100 rewards
- Docker and Docker Compose development environments
- Render Blueprint deployment, health probes, and idempotent production bootstrap
- Ruff, strict mypy, pytest coverage enforcement, and GitHub Actions CI

### Security

- Argon2 password hashing and signed HttpOnly session cookies
- AI rate limiting, defensive response headers, and request correlation IDs
- Spreadsheet formula neutralization in CSV exports
- Non-root multi-stage production container
