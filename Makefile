.PHONY: dev stop logs migrate seed test-api test-web lint build

dev:
	docker compose up -d
	@echo "✅ Services running"
	@echo "   Frontend: http://localhost:3000"
	@echo "   Backend:  http://localhost:8000/docs"
	@echo "   Qdrant:   http://localhost:6333/dashboard"

stop:
	docker compose down

logs:
	docker compose logs -f

logs-api:
	docker compose logs -f api

logs-web:
	docker compose logs -f web

logs-worker:
	docker compose logs -f worker

migrate:
	docker compose exec api alembic upgrade head

migrate-create:
	@read -p "Migration name: " name; \
	docker compose exec api alembic revision --autogenerate -m "$$name"

seed:
	docker compose exec api python -m src.core.seed

test-api:
	docker compose exec api pytest tests/ -v

test-web:
	docker compose exec web npm test

lint:
	docker compose exec api ruff check src/
	docker compose exec web npx eslint src/

format:
	docker compose exec api ruff format src/
	docker compose exec web npx prettier --write src/

build:
	docker build -f infra/docker/Dockerfile.api -t kc-api .
	docker build -f infra/docker/Dockerfile.web -t kc-web .
	docker build -f infra/docker/Dockerfile.worker -t kc-worker .

shell-api:
	docker compose exec api bash

shell-db:
	docker compose exec postgres psql -U copilot -d copilot

qdrant-ui:
	@echo "Open http://localhost:6333/dashboard"
