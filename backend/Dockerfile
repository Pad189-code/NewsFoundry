# Build Railway : Root Directory = backend/ (contexte = ce dossier).
# Build local monorepo : docker build -f backend/Dockerfile backend
FROM ghcr.io/astral-sh/uv:python3.13-bookworm

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen

COPY src/ ./src/
COPY alembic.ini ./
COPY alembic/ ./alembic/
COPY docker-entrypoint.sh ./docker-entrypoint.sh
RUN chmod +x ./docker-entrypoint.sh

EXPOSE 8000

CMD ["./docker-entrypoint.sh"]
