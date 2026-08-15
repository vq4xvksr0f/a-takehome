.PHONY: up down logs test lint format typecheck build

# ── Stack ─────────────────────────────────────────────────
up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f

# ── Checks ────────────────────────────────────────────────
test:
	cd backend && .venv/bin/python -m pytest tests/ -q

lint: lint-backend lint-frontend

lint-backend:
	cd backend && .venv/bin/ruff check . && .venv/bin/ruff format --check .

lint-frontend:
	cd frontend && npm run lint && npm run typecheck

format:
	cd backend && .venv/bin/ruff format .

# ── Frontend build sanity check (standalone) ──────────────
build:
	cd frontend && npm run build
