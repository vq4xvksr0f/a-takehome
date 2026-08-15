#!/bin/sh
# Container entrypoint: apply migrations, seed admin, start the API.
# (main.py's lifespan also runs migrations+seed, making them idempotent and
# safe to run here as a belt-and-suspenders for `docker compose up`.)
set -e

cd /app
echo "[entrypoint] running alembic migrations..."
alembic upgrade head
echo "[entrypoint] starting uvicorn (lifespan will seed admin)..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
