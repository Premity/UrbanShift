# ── UrbanShift Web ── Node 22 + pnpm 9 ────────────────────
FROM node:22-alpine

# Install pnpm 9 (v10 has breaking build-script approval requirements)
RUN corepack enable && corepack prepare pnpm@9.15.4 --activate

WORKDIR /app

# Copy dependency manifest first (cache layer)
COPY package.json pnpm-lock.yaml* ./

# Install dependencies
RUN pnpm install --no-frozen-lockfile

# Copy application source
COPY . .

EXPOSE 5173

CMD ["pnpm", "dev", "--host", "0.0.0.0", "--port", "5173"]
