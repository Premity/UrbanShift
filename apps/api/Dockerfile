# ── UrbanShift API ── Python 3.11 + uv ──────────────────
FROM python:3.11-slim

# System deps for asyncpg and pgvector
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv package manager
RUN pip install --no-cache-dir uv

WORKDIR /app

# Copy dependency manifest first (cache layer)
COPY pyproject.toml .

# Install dependencies into system Python (no venv needed in Docker)
RUN uv pip install --system -r pyproject.toml

# Copy application source
COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
