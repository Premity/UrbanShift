# UrbanShift

> **AI-powered, mobile-first guidance for India's urban migrant workers.**
> Find work, find a home, and unlock the government schemes you're eligible for — in your language, in minutes.

UrbanShift orchestrates personalised recommendations across three life-critical domains — **Government Schemes**, **Jobs**, and **Housing** — through a multi-agent LangGraph pipeline that reasons over a worker's profile, location, and goals.

---

## Why UrbanShift

India's internal migrants face a fragmented information landscape: hundreds of overlapping welfare schemes, opaque job listings, and informal housing markets. UrbanShift collapses that complexity into a single guided experience that:

- **Speaks your language.** Full UI + content support for English, हिंदी (Hindi), and ಕನ್ನಡ (Kannada).
- **Understands your story.** A short intake — or a one-click resume upload — drives every recommendation.
- **Reasons, not just searches.** A LangGraph agent graph plans, retrieves, validates, and ranks results before they hit your screen.
- **Works on a phone first.** Built for low-bandwidth Android browsers, not desktops.

---

## Architecture at a glance

```
┌─────────────────┐    ┌──────────────────┐    ┌────────────────────┐
│  React + Vite   │ ─► │ FastAPI gateway  │ ─► │  LangGraph agents  │
│  (Tailwind UI)  │    │  (Pydantic v2)   │    │  Scheme · Job ·    │
│  i18n: en/hi/kn │ ◄─ │  Sessions / RAG  │ ◄─ │  Housing · Validate│
└─────────────────┘    └──────────────────┘    └────────────────────┘
                                │                        │
                                ▼                        ▼
                       ┌──────────────────┐     ┌─────────────────┐
                       │  Postgres 16 +   │     │  LiteLLM router │
                       │  pgvector (RAG)  │     │  (multi-model)  │
                       └──────────────────┘     └─────────────────┘
```

### Tech stack

| Layer            | Choice                                              |
| ---------------- | --------------------------------------------------- |
| Frontend         | React 18 · TypeScript · Vite · Tailwind · i18next   |
| Backend          | Python 3.11 · FastAPI · Pydantic v2 · Alembic       |
| Database         | Postgres 16 + pgvector                              |
| Agents           | LangGraph · LiteLLM                                 |
| Ingestion        | Playwright scrapers · resume parser                 |
| Dev environment  | Docker Compose                                      |

---

## Quick start

You need Docker, Docker Compose, and `make`.

```bash
# 1. Set up env (one-time)
cp .env.development.example .env.development

# 2. Start the full stack — postgres, adminer, api, web
make dev

# 3. Apply DB migrations
make migrate

# 4. Seed schemes, jobs and housing data
make seed

# 5. (Optional) seed scheme embeddings for vector retrieval
docker compose exec api python -m scripts.seed_scheme_embeddings

# When you're done
make stop
```

Open http://localhost:5173 and walk through the intake.

> Detailed Docker workflow notes live in [`DOCKER_DEV_INSTRUCTIONS.md`](./DOCKER_DEV_INSTRUCTIONS.md).

### Services

| Service  | URL                       | Purpose                |
| -------- | ------------------------- | ---------------------- |
| Web      | http://localhost:5173     | Vite + React frontend  |
| API      | http://localhost:8000     | FastAPI backend + docs |
| Adminer  | http://localhost:8080     | Postgres UI            |
| Postgres | `localhost:5432`          | Database (internal)    |

The interactive API reference is at http://localhost:8000/docs.

---

## Project structure

```
urban-shift/
├── apps/
│   ├── api/              # FastAPI service
│   │   ├── routes/       # session, intake, profile, resume, run, schemes
│   │   ├── models/       # SQLAlchemy models
│   │   ├── schemas/      # Pydantic v2 schemas
│   │   └── alembic/      # Migrations
│   └── web/              # React + Vite frontend
│       └── src/
│           ├── pages/    # landing, intake, processing, results, confirm
│           ├── components/intake, results, shared
│           └── locales/  # en.json, hi.json, kn.json
├── packages/
│   ├── agents/           # LangGraph graph + scheme/job/housing/validator agents
│   ├── scrapers/         # Playwright job + housing scrapers
│   └── shared/           # Cross-cutting Pydantic types
├── data/seed/            # schemes.json, housing.json, jobs CSVs
├── scripts/              # seed, refresh, link checks, agent test harnesses
├── docker-compose.yml
├── Makefile
└── .env.development      # Dev env template
```

---

## Common tasks

```bash
# Refresh job listings via scrapers
make refresh-jobs

# Re-seed jobs from CSV
make seed-jobs

# Validate links across seed data
docker compose exec api python -m scripts.check_links

# Exercise individual agents
docker compose exec api python -m scripts.test_scheme_agent
docker compose exec api python -m scripts.test_job_agent
docker compose exec api python -m scripts.test_validator_agent
docker compose exec api python -m scripts.test_graph
```

---

## License

[GNU General Public License v3.0](./LICENSE)
