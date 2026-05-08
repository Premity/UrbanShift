# UrbanShift — Docker Development Instructions

> **This file is gitignored.** It lives in `/docs/` which is excluded from version control.
> All agents and developers must follow these instructions at all times.

---

## ⚠️ MANDATORY: Docker-First Development

**The running Docker Compose environment is the PRIMARY and ONLY environment for all development, testing, debugging, and command execution.**

No code should be run, tested, or validated on the host machine directly. Every operation happens inside the Docker containers.

---

## Starting the Environment

```bash
# Start all services (postgres + adminer + api + web)
make dev
# or equivalently:
docker compose up --build
```

This brings up 4 services:

| Service | Container | URL | Purpose |
|---------|-----------|-----|---------|
| `db` | `pgvector/pgvector:pg16` | `localhost:5432` | PostgreSQL + pgvector |
| `adminer` | `adminer:latest` | `http://localhost:8080` | Database admin UI |
| `api` | built from `apps/api/` | `http://localhost:8000` | FastAPI backend |
| `web` | built from `apps/web/` | `http://localhost:5173` | Vite React frontend |

## Stopping the Environment

```bash
make stop
# or:
docker compose down
```

---

## Executing Commands Inside Containers

### API (Python/FastAPI)

```bash
# Open a shell inside the API container
docker compose exec api bash

# Run a Python script
docker compose exec api python -m scripts.seed_db

# Run Alembic migrations
docker compose exec api alembic upgrade head
# or simply:
make migrate
```

### Web (Node/React)

```bash
# Open a shell inside the Web container
docker compose exec web sh

# Run any Node/pnpm command
docker compose exec web pnpm <command>
```

### Database (PostgreSQL)

```bash
# Open psql shell
docker compose exec db psql -U urbanshift -d urbanshift

# Run a quick SQL query
docker compose exec db psql -U urbanshift -d urbanshift -c "SELECT count(*) FROM schemes;"
```

Or use **Adminer** at `http://localhost:8080`:
- System: PostgreSQL
- Server: `db`
- Username: `urbanshift`
- Password: `urbanshift_dev`
- Database: `urbanshift`

---

## Installing Dependencies

### Python (API)

```bash
# ALWAYS install inside the container
docker compose exec api uv pip install --system <package>

# To add to pyproject.toml permanently (preferred)
# 1. Edit apps/api/pyproject.toml on host (file is volume-mounted)
# 2. Then sync inside container:
docker compose exec api uv pip install --system -r pyproject.toml
```

### Node (Web)

```bash
# ALWAYS install inside the container
docker compose exec web pnpm add <package>
docker compose exec web pnpm add -D <package>   # dev dependency
```

---

## Database Migrations

```bash
# Run pending migrations
make migrate

# Create a new migration after model changes
docker compose exec api alembic revision --autogenerate -m "description_of_change"

# Rollback last migration
docker compose exec api alembic downgrade -1
```

---

## Seeding Data

```bash
make seed
# Runs: docker compose exec -e PYTHONPATH=/:/app api python -m scripts.seed_db
```

---

## Refreshing Jobs (Scrapers)

```bash
make refresh-jobs
# Runs: docker compose exec -e PYTHONPATH=/:/app api python -m scripts.refresh_jobs
```

---

## Hot Reload / Live Development

Both services are configured for hot reload:

- **API**: `uvicorn` runs with `--reload`. Edit any `.py` file in `apps/api/` or `packages/` and the server restarts automatically.
- **Web**: Vite HMR is enabled. Edit any file in `apps/web/src/` and changes reflect instantly in the browser.

Source code is **volume-mounted** from the host into the containers, so you edit files normally on your host machine using your IDE — changes are reflected inside the containers immediately.

---

## Rebuilding Containers

If you change `Dockerfile`, `pyproject.toml`, or `package.json`:

```bash
# Rebuild and restart
docker compose up --build

# Or rebuild a specific service
docker compose build api
docker compose build web
```

---

## ❌ Anti-Patterns — NEVER Do These

| ❌ Don't | ✅ Do Instead |
|----------|--------------|
| Run `uv sync` on host machine | `docker compose exec api uv pip install --system -r pyproject.toml` |
| Run `pnpm install` on host machine | `docker compose exec web pnpm install` |
| Run `python main.py` on host | `docker compose exec api python main.py` |
| Connect to postgres from host directly | Use Adminer at `:8080` or `docker compose exec db psql` |
| Run `alembic` on host | `make migrate` or `docker compose exec api alembic ...` |
| Install system packages on host for the project | Add to the appropriate `Dockerfile` and rebuild |
| Create a local venv or node_modules on host | Everything lives inside containers |

---

## Why Docker-First?

1. **Parity**: Dev environment is identical to what runs in production — same OS, same versions, same extensions (pgvector).
2. **No "works on my machine"**: Every developer/agent gets the exact same environment.
3. **pgvector availability**: The `vector` extension is only available inside the `pgvector/pgvector:pg16` container. Running migrations or queries from the host will fail.
4. **Isolation**: No risk of polluting the host machine with project-specific dependencies.
5. **Reproducibility**: `docker compose up --build` from a clean state always produces a working environment.

---

## Troubleshooting

### Container won't start
```bash
# Check logs for a specific service
docker compose logs api
docker compose logs db

# Rebuild from scratch
docker compose down -v   # removes volumes too (⚠️ deletes DB data)
docker compose up --build
```

### Database connection issues
```bash
# Verify DB is healthy
docker compose ps
# Look for "healthy" status on the db service

# Check if the DB accepts connections
docker compose exec db pg_isready -U urbanshift
```

### Port conflicts
If ports 5432, 8000, 5173, or 8080 are already in use on your host, either stop the conflicting service or change ports in `docker-compose.yml`.
