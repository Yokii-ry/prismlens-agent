# PrismLens

PrismLens has a FastAPI backend, an ARQ worker, Redis, PostgreSQL, and a Next.js frontend.

## Start After Restart

After shutting down or restarting your computer, start the project in this order.

### 1. Go to the project directory

```bash
cd /Users/yokili/fy/game/ag/prismlens
```

### 2. Start infrastructure

Start PostgreSQL:

```bash
make docker-postgres
```

Start Redis:

```bash
make docker-redis
```

These commands use Colima/Docker. The default PostgreSQL settings are:

```text
host: localhost
port: 5432
database: multiprism
user: multiprism
password: multiprism
```

The backend reads the database URL from `backend/.env`:

```env
DATABASE_URL=postgresql+asyncpg://multiprism:multiprism@localhost:5432/multiprism
```

### 3. Run database migrations

Run this after PostgreSQL is up:

```bash
make migrate
```

### 4. Start the API server

Open a new terminal tab:

```bash
cd /Users/yokili/fy/game/ag/prismlens
make api
```

The API runs at:

```text
http://localhost:8000
```

Health check:

```text
http://localhost:8000/health
```

### 5. Start the worker

Open another terminal tab:

```bash
cd /Users/yokili/fy/game/ag/prismlens
make worker
```

The worker processes background research tasks from Redis.

### 6. Start the frontend

Open another terminal tab:

```bash
cd /Users/yokili/fy/game/ag/prismlens
make frontend
```

The frontend runs at:

```text
http://localhost:7777
```

## Common Problems

### `password authentication failed for user "multiprism"`

The password in `backend/.env` does not match the PostgreSQL container password.

For the Docker setup in this repo, use:

```env
DATABASE_URL=postgresql+asyncpg://multiprism:multiprism@localhost:5432/multiprism
```

### `Connection refused` on port `5432`

PostgreSQL is not running or is not listening on `localhost:5432`.

Run:

```bash
make docker-postgres
```

### Redis connection errors

Redis is not running.

Run:

```bash
make docker-redis
```

### Check running containers

```bash
docker ps
```

### Check PostgreSQL container config

```bash
docker inspect postgres --format '{{range .Config.Env}}{{println .}}{{end}}'
```

## Useful Commands

```bash
make help
make test
make migrate
make api
make worker
make frontend
```
