# FINN: one container running the API (FastAPI, internal :8000) and the web app (Next.js, public $PORT).
# Data lives on a mounted volume at /data; on first boot it is seeded from api/seed/finn.db.gz so the demo works
# immediately, even if the host's IP is blocked by NSE. See DEPLOY.md.

# ── web build ────────────────────────────────────────────────────────────────
FROM node:20-bookworm-slim AS web
WORKDIR /web
RUN corepack enable
COPY web/package.json web/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY web/ ./
ENV NEXT_TELEMETRY_DISABLED=1
RUN pnpm build

# ── runtime: Python + the Node binary for the standalone Next server ─────────
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim
COPY --from=web /usr/local/bin/node /usr/local/bin/node

WORKDIR /app/api
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONUNBUFFERED=1
COPY api/pyproject.toml api/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY api/ ./

WORKDIR /app/web
COPY --from=web /web/.next/standalone ./
COPY --from=web /web/.next/static ./.next/static
COPY --from=web /web/public ./public

COPY deploy/start.sh /app/start.sh
RUN chmod +x /app/start.sh

ENV FINN_CACHE_DIR=/data API_URL=http://127.0.0.1:8000 NEXT_TELEMETRY_DISABLED=1 PORT=3000
EXPOSE 3000
CMD ["/app/start.sh"]
