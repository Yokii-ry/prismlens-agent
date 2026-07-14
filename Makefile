.PHONY: help api worker frontend test migrate redis-start redis-stop redis-status docker-redis docker-postgres

# Default target: show available commands.
help:
	@echo "PrismLens development commands:"
	@echo ""
	@echo "  make redis-start      Start Redis via Homebrew (default)"
	@echo "  make redis-stop       Stop Redis via Homebrew"
	@echo "  make redis-status     Check if Redis is running"
	@echo ""
	@echo "  make api              Start FastAPI dev server (auto-reload)"
	@echo "  make worker           Start ARQ background worker"
	@echo "  make frontend         Start Next.js dev server on :7777"
	@echo "  make test             Run backend unit tests"
	@echo "  make migrate          Run database migrations"
	@echo ""
	@echo "  make docker-redis     Start Redis in Docker (requires Colima/Docker)"
	@echo "  make docker-postgres  Start PostgreSQL in Docker (requires Colima/Docker)"

# --- Infrastructure (Homebrew) ---

redis-start:
	brew services start redis

redis-stop:
	brew services stop redis

redis-status:
	@redis-cli ping 2>/dev/null && echo "Redis is running" || echo "Redis is not running (try: make redis-start)"

# --- Infrastructure (Docker, optional) ---

docker-redis:
	colima start
	docker start redis 2>/dev/null || docker run -d --name redis -p 6379:6379 redis:7-alpine
	docker ps

docker-postgres:
	colima start
	docker start postgres 2>/dev/null || docker run -d --name postgres \
		-p 5432:5432 \
		-e POSTGRES_USER=multiprism \
		-e POSTGRES_PASSWORD=multiprism \
		-e POSTGRES_DB=multiprism \
		postgres:16
	docker ps

# --- Application ---

api:
	cd backend && uv run uvicorn main:app --reload

worker:
	cd backend && uv run arq app.worker.tasks.WorkerSettings

frontend:
	cd frontend && npm run dev

migrate:
	cd backend && uv run alembic upgrade head

test:
	cd backend && env PYTHONDONTWRITEBYTECODE=1 uv run python -m unittest discover -s tests
