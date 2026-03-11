# Enterprise Knowledge Copilot & Automation Platform

AI-powered knowledge search and automation for enterprises.
Stack: Next.js · FastAPI · Azure · Qdrant · Entra ID

## Quick Start (Local Dev)

```bash
# 1. Copy env file and fill in values
cp .env.example .env

# 2. Start all services
make dev

# 3. Open
# Frontend: http://localhost:3000
# Backend:  http://localhost:8000/docs
# Qdrant:   http://localhost:6333/dashboard
```

## Project Structure

```
knowledge-copilot/
├── apps/
│   ├── api/          # FastAPI Backend (Python)
│   └── web/          # Next.js Frontend (TypeScript)
├── infra/
│   ├── docker/       # Dockerfiles
│   └── scripts/      # Setup & deploy scripts
├── .github/workflows/  # CI/CD
├── docker-compose.yml  # Local dev
├── Makefile            # Dev commands
└── .env.example
```

## Make Commands

| Command | Description |
|---------|-------------|
| `make dev` | Start all services (docker-compose) |
| `make stop` | Stop all services |
| `make logs` | Tail all logs |
| `make migrate` | Run DB migrations |
| `make seed` | Seed initial data |
| `make test-api` | Run backend tests |
| `make test-web` | Run frontend tests |
| `make lint` | Lint all code |
| `make build` | Build production images |

## Environment Variables

See [.env.example](.env.example) for all required variables.
