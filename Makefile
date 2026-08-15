.PHONY: up down logs seed setup test lint format typecheck build

# ── Stack ─────────────────────────────────────────────────
up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f

# One-command reviewer setup: bring the stack up, wait for the backend to be
# healthy, then populate demo data.
setup: up
	@echo "Waiting for backend to be healthy..."
	@until docker compose exec -T backend \
		python -c "import urllib.request,sys;sys.exit(0 if urllib.request.urlopen('http://localhost:8000/api/health').status==200 else 1)" \
		>/dev/null 2>&1; do sleep 1; done
	@$(MAKE) seed

# Populate the running stack with fake demo leads (+ resumes + activity).
# Idempotent — skips if leads already exist. Run after `make up`.
seed:
	docker compose exec backend python -m app.core.demo_seed

# ── Checks ────────────────────────────────────────────────
test:
	cd backend && .venv/bin/python -m pytest tests/ -q
	cd frontend && npm test

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
