FROM ghcr.io/astral-sh/uv:python3.13-bookworm

WORKDIR /app

COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen

COPY backend/src/ ./src/
COPY backend/alembic.ini ./
COPY backend/alembic/ ./alembic/

# Port indicatif en local ; en prod Railway définit PORT et main.py l’utilise.
EXPOSE 8000

# Écoute sur os.environ["PORT"] (injecté par Railway) et host 0.0.0.0 dans src/main.py.
CMD ["uv", "run", "python", "src/main.py"]