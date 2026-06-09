.PHONY: up down logs migrate seed demo-data backend-test backend-lint backend-typecheck frontend-install frontend-build frontend-typecheck evals smoke-test verify

up:
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f

migrate:
	cd backend && python -m app.scripts.migrate

seed:
	cd backend && python -m app.scripts.seed

demo-data: seed

backend-test:
	cd backend && python -m pytest

backend-lint:
	cd backend && python -m ruff check .

backend-typecheck:
	cd backend && python -m mypy app

frontend-install:
	cd frontend && npm install

frontend-build:
	cd frontend && npm run build

frontend-typecheck:
	cd frontend && npm run typecheck

evals:
	cd backend && python -m app.scripts.run_evals

smoke-test:
	cd backend && python -m app.scripts.smoke_test

verify: backend-lint backend-typecheck backend-test frontend-typecheck frontend-build
