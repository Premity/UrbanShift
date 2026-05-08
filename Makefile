.PHONY: dev stop migrate seed

# ── Development ──────────────────────────────────

dev:
	docker compose up --build

stop:
	docker compose down

# ── Database ─────────────────────────────────────

migrate:
	docker compose exec api alembic upgrade head

seed:
	docker compose exec -e PYTHONPATH=/:/app api python -m scripts.seed_db

refresh-jobs:
	docker compose exec -e PYTHONPATH=/:/app api python -m scripts.refresh_jobs

