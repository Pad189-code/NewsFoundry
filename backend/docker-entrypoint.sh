#!/bin/sh
set -e
echo "[NewsFoundry] Alembic upgrade head..."
uv run alembic upgrade head
echo "[NewsFoundry] Starting API..."
exec uv run python src/main.py
