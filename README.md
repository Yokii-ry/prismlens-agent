# PrismLens

PrismLens has a FastAPI backend, an ARQ worker, Redis, PostgreSQL, and a Next.js frontend.

## Project Structure

```text
prismlens/
├── backend/          # FastAPI 后端、数据库模型、API 路由、任务队列 worker、迁移和测试
├── frontend/         # Next.js 前端页面、组件、样式和前端工具函数
├── demo归档/         # 早期调试/实验脚本，偏演示和归档用途
├── docker-compose.yml# 本地容器编排配置
├── Makefile          # 常用启动、测试、迁移命令入口
├── VERSIONING.md     # 版本管理说明
└── README.md         # 项目总说明与启动指南
```

### Backend Overview

`backend/` 主要负责业务 API、数据库访问和后台任务执行：

- `backend/main.py`：FastAPI 入口，注册路由、CORS、异常处理和健康检查
- `backend/app/api/`：HTTP 接口层，包含任务提交、查询、SSE 推送和认证相关路由
- `backend/app/db/`：数据库会话、模型和 CRUD 方法
- `backend/app/pipeline/`：研究流程的状态、节点、图编排和 checkpoint 逻辑
- `backend/app/worker/`：ARQ worker 与后台任务入口
- `backend/migrations/`：Alembic 数据库迁移文件
- `backend/tests/`：后端单元测试与接口测试

### Frontend Overview

`frontend/` 主要负责展示层和交互：

- `frontend/app/`：Next.js App Router 页面、布局和全局样式
- `frontend/components/`：页面级组件和通用 UI 组件
- `frontend/lib/`：前端工具函数、API 封装和辅助逻辑
- `frontend/public/`：静态资源

### Docs

- `backend/README.md`：后端相关说明
- `frontend/README.md`：前端默认项目说明
- `VERSIONING.md`：版本号与发布规则

## Authentication

PrismLens 现在支持基于邮箱和密码的登录注册：

- `POST /api/auth/register`：创建新用户
- `POST /api/auth/login`：校验密码并签发 JWT
- 登录成功后，服务端会把 `access_token` 写入 `HttpOnly` Cookie
- 前端请求需要携带 cookie，受保护接口可以通过 `get_current_user` 读取当前用户

为了让认证正常工作，后端需要配置这些环境变量：

```env
JWT_SECRET_KEY=your-own-secret
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
FRONTEND_URL=http://localhost:7777
```

如果你要从别的设备访问本地前端，可以把 `CORS_ALLOWED_ORIGINS` 按需补上对应来源。

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

如果你刚拉了包含认证改动的新版本，请务必先跑迁移。用户表现在会保存密码哈希，不再依赖明文密码。

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
