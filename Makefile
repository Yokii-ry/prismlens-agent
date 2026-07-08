.PHONY: api worker test

# Start the FastAPI development server with auto-reload.
api:
	cd backend && uv run uvicorn main:app --reload

# Start the ARQ worker that runs background research tasks.
worker:
	cd backend && uv run arq app.worker.tasks.WorkerSettings

# Run backend unit tests without writing __pycache__ files.
test:
	cd backend && env PYTHONDONTWRITEBYTECODE=1 uv run python -m unittest discover -s tests
