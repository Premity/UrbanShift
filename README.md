# UrbanShift

AI-powered, mobile-first platform for urban migrant assistance in Indian cities.

Intelligent orchestration across **Government Schemes**, **Jobs**, and **Housing** — powered by a multi-agent LangGraph pipeline.

## Tech Stack

| Layer | Choice |
|---|---|
| Frontend | React 18 + TypeScript + Vite + Tailwind + shadcn/ui |
| Backend | Python 3.11 + FastAPI + Pydantic v2 |
| Database | Postgres 16 + pgvector |
| Agents | LangGraph + LiteLLM |
| Dev Environment | Docker Compose |

## Quick Start

```bash
# Copy env template
cp .env.development .env

# Start full stack (postgres + adminer + api + web)
make dev

# Run database migrations
make migrate

# Seed database with schemes + housing data
make seed

# Stop all services
make stop
```

## Services

| Service | URL | Description |
|---|---|---|
| API | http://localhost:8000 | FastAPI backend |
| Web | http://localhost:5173 | Vite React frontend |
| Adminer | http://localhost:8080 | Database admin UI |
| Postgres | localhost:5432 | Database (internal) |

## Project Structure

```
UrbanShift/
├── apps/
│   ├── api/          # FastAPI service
│   └── web/          # Vite React TS frontend
├── packages/
│   ├── agents/       # LangGraph nodes, prompts, tools
│   ├── scrapers/     # Playwright + Adzuna scrapers
│   └── shared/       # Cross-cutting Pydantic types
├── data/seed/        # Seed data (schemes, housing)
├── scripts/          # Utility scripts
├── docker-compose.yml
├── Makefile
└── .env.development  # Dev environment template
```

## License

GNU General Public License v3.0
