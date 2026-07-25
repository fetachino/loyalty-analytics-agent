.PHONY: install run migrate migration seed eval-validate format lint typecheck test check up down

install:
	python -m pip install -e ".[dev]"

run:
	uvicorn loyalty_analytics.main:app --reload

migrate:
	alembic upgrade head

migration:
	alembic revision --autogenerate -m "$(name)"

seed:
	python scripts/seed.py

eval-validate:
	python scripts/run_evals.py --validate

format:
	ruff format .
	ruff check --fix .

lint:
	ruff format --check .
	ruff check .

typecheck:
	mypy

test:
	pytest

check: lint typecheck test

up:
	docker compose up --build -d

down:
	docker compose down
