import unittest
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from fastapi.testclient import TestClient

from app.api.errors import AppError, ErrorCode
from app.api import routes
from app.core.security import hash_password
from app.db.models import TaskStatus
from app.db.session import get_db
from main import app


async def override_get_db():
    yield object()


def override_db_with(db):
    async def _override_get_db():
        yield db

    return _override_get_db


@app.get("/__tests__/rate-limited")
async def raise_rate_limited():
    raise AppError(
        status_code=429,
        code=ErrorCode.RATE_LIMITED,
        message="Rate limit exceeded",
    )


@app.get("/__tests__/service-unavailable")
async def raise_service_unavailable():
    raise AppError(
        status_code=503,
        code=ErrorCode.SERVICE_UNAVAILABLE,
        message="Service unavailable",
    )


@app.get("/__tests__/agent-timeout")
async def raise_agent_timeout():
    raise AppError(
        status_code=504,
        code=ErrorCode.AGENT_TIMEOUT,
        message="Agent execution timed out",
    )


@app.get("/__tests__/internal-error")
async def raise_internal_error():
    raise RuntimeError("boom")


class TaskRoutesTest(unittest.TestCase):
    def setUp(self) -> None:
        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)
        self.no_raise_client = TestClient(app, raise_server_exceptions=False)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()

    def test_get_task_status_rejects_malformed_task_id_before_database_lookup(self) -> None:
        with patch.object(routes, "get_task", new_callable=AsyncMock, return_value=None) as get_task:
            response = self.client.get("/api/tasks/12")

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["code"], "VALIDATION_ERROR")
        self.assertEqual(response.json()["status"], "error")
        self.assertEqual(response.json()["message"], "Validation error")
        get_task.assert_not_called()

    def test_cors_allows_lan_frontend_origin(self) -> None:
        response = self.client.options(
            "/api/tasks",
            headers={
                "Origin": "http://192.168.0.6:7777",
                "Access-Control-Request-Method": "POST",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers["access-control-allow-origin"],
            "http://192.168.0.6:7777",
        )

    def test_rate_limited_error_returns_standard_response(self) -> None:
        response = self.client.get("/__tests__/rate-limited")

        self.assertEqual(response.status_code, 429)
        self.assertEqual(
            response.json(),
            {
                "code": "RATE_LIMITED",
                "status": "error",
                "message": "Rate limit exceeded",
                "data": None,
            },
        )

    def test_service_unavailable_error_returns_standard_response(self) -> None:
        response = self.client.get("/__tests__/service-unavailable")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.json(),
            {
                "code": "SERVICE_UNAVAILABLE",
                "status": "error",
                "message": "Service unavailable",
                "data": None,
            },
        )

    def test_agent_timeout_error_returns_standard_response(self) -> None:
        response = self.client.get("/__tests__/agent-timeout")

        self.assertEqual(response.status_code, 504)
        self.assertEqual(
            response.json(),
            {
                "code": "AGENT_TIMEOUT",
                "status": "error",
                "message": "Agent execution timed out",
                "data": None,
            },
        )

    def test_unhandled_exception_returns_standard_internal_error_response(self) -> None:
        response = self.no_raise_client.get("/__tests__/internal-error")

        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            response.json(),
            {
                "code": "INTERNAL_ERROR",
                "status": "error",
                "message": "Internal server error",
                "data": None,
            },
        )

    def test_get_task_status_returns_standard_error_when_task_not_found(self) -> None:
        task_id = uuid.uuid4()

        with patch.object(routes, "get_task", new_callable=AsyncMock, return_value=None):
            response = self.client.get(f"/api/tasks/{task_id}")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.json(),
            {
                "code": "TASK_NOT_FOUND",
                "status": "error",
                "message": "Task not found",
                "data": None,
            },
        )

    def test_get_task_status_returns_standard_success_response(self) -> None:
        task_id = uuid.uuid4()
        task = SimpleNamespace(
            id=task_id,
            status=TaskStatus.COMPLETED,
            event_query="政策影响分析",
            final_report={"summary": "done"},
            error_message=None,
            created_at=datetime(2026, 7, 2, 16, 0, tzinfo=timezone.utc),
        )

        with patch.object(routes, "get_task", new_callable=AsyncMock, return_value=task):
            response = self.client.get(f"/api/tasks/{task_id}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["code"], "OK")
        self.assertEqual(response.json()["status"], "success")
        self.assertEqual(response.json()["message"], "Task fetched")
        self.assertEqual(
            response.json()["data"],
            {
                "task_id": str(task_id),
                "task_status": "completed",
                "event_query": "政策影响分析",
                "final_report": {"summary": "done"},
                "error_message": None,
                "created_at": "2026-07-02T16:00:00+00:00",
            },
        )

    def test_create_task_returns_standard_success_response(self) -> None:
        task_id = uuid.uuid4()
        task = SimpleNamespace(id=task_id)
        redis = AsyncMock()

        with (
            patch.object(routes, "ensure_user_exists", new_callable=AsyncMock) as ensure_user_exists,
            patch.object(routes, "create_research_task", new_callable=AsyncMock, return_value=task),
            patch.object(routes, "create_pool", new_callable=AsyncMock, return_value=redis),
        ):
            response = self.client.post("/api/tasks", params={"event_query": "政策影响分析"})

        ensure_user_exists.assert_awaited_once()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "code": "OK",
                "status": "success",
                "message": "Task created",
                "data": {
                    "task_id": str(task_id),
                    "task_status": "pending",
                },
            },
        )

    def test_create_task_uses_single_api_prefix(self) -> None:
        task_id = uuid.uuid4()
        task = SimpleNamespace(id=task_id)
        redis = AsyncMock()

        with (
            patch.object(routes, "ensure_user_exists", new_callable=AsyncMock) as ensure_user_exists,
            patch.object(routes, "create_research_task", new_callable=AsyncMock, return_value=task),
            patch.object(routes, "create_pool", new_callable=AsyncMock, return_value=redis),
        ):
            response = self.client.post("/api/tasks", params={"event_query": "2"})

        ensure_user_exists.assert_awaited_once()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["task_id"], str(task_id))

    def test_register_returns_standard_success_response(self) -> None:
        db = SimpleNamespace(
            execute=AsyncMock(return_value=SimpleNamespace(scalar_one_or_none=lambda: None)),
            add=Mock(),
            commit=AsyncMock(),
            refresh=AsyncMock(),
        )
        app.dependency_overrides[get_db] = override_db_with(db)

        response = self.client.post(
            "/api/auth/register",
            json={"email": "new@example.com", "password": "secret123"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["code"], "OK")
        self.assertEqual(response.json()["status"], "success")
        self.assertEqual(response.json()["message"], "注册成功")
        self.assertEqual(response.json()["data"], {"email": "new@example.com"})
        db.add.assert_called_once()
        self.assertEqual(db.add.call_args.args[0].email, "new@example.com")
        self.assertNotEqual(db.add.call_args.args[0].hashed_password, "secret123")
        db.commit.assert_awaited_once()
        db.refresh.assert_awaited_once()

    def test_register_returns_standard_error_when_user_exists(self) -> None:
        db = SimpleNamespace(
            execute=AsyncMock(
                return_value=SimpleNamespace(
                    scalar_one_or_none=lambda: SimpleNamespace(email="taken@example.com")
                )
            )
        )
        app.dependency_overrides[get_db] = override_db_with(db)

        response = self.client.post(
            "/api/auth/register",
            json={"email": "taken@example.com", "password": "secret123"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json(),
            {
                "code": "USER_ALREADY_EXISTS",
                "status": "error",
                "message": "用户已存在",
                "data": None,
            },
        )

    def test_login_sets_cookie_and_returns_standard_success_response(self) -> None:
        user = SimpleNamespace(
            id=uuid.uuid4(),
            email="user@example.com",
            hashed_password=hash_password("secret123"),
        )
        db = SimpleNamespace(
            execute=AsyncMock(return_value=SimpleNamespace(scalar_one_or_none=lambda: user))
        )
        app.dependency_overrides[get_db] = override_db_with(db)

        response = self.client.post(
            "/api/auth/login",
            json={"email": "user@example.com", "password": "secret123"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["code"], "OK")
        self.assertEqual(response.json()["status"], "success")
        self.assertEqual(response.json()["message"], "登录成功")
        self.assertEqual(response.json()["data"], {"email": "user@example.com"})
        self.assertIn("access_token=", response.headers["set-cookie"])
        self.assertIn("HttpOnly", response.headers["set-cookie"])

    def test_login_returns_standard_error_for_bad_credentials(self) -> None:
        user = SimpleNamespace(
            id=uuid.uuid4(),
            email="user@example.com",
            hashed_password=hash_password("secret123"),
        )
        db = SimpleNamespace(
            execute=AsyncMock(return_value=SimpleNamespace(scalar_one_or_none=lambda: user))
        )
        app.dependency_overrides[get_db] = override_db_with(db)

        response = self.client.post(
            "/api/auth/login",
            json={"email": "user@example.com", "password": "wrong-password"},
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            response.json(),
            {
                "code": "INVALID_CREDENTIALS",
                "status": "error",
                "message": "用户名或密码错误",
                "data": None,
            },
        )

    def test_get_task_status_uses_single_api_prefix(self) -> None:
        task_id = uuid.uuid4()
        task = SimpleNamespace(
            id=task_id,
            status=TaskStatus.COMPLETED,
            event_query="2",
            final_report={"summary": "done"},
            error_message=None,
            created_at=datetime(2026, 7, 2, 16, 0, tzinfo=timezone.utc),
        )

        with patch.object(routes, "get_task", new_callable=AsyncMock, return_value=task):
            response = self.client.get(f"/api/tasks/{task_id}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["task_id"], str(task_id))

    def test_stream_returns_complete_event_when_task_already_completed(self) -> None:
        task_id = uuid.uuid4()
        task = SimpleNamespace(
            id=task_id,
            status=TaskStatus.COMPLETED,
            final_report={"raw_results": ["done"]},
            error_message=None,
        )

        with patch.object(routes, "get_task", new_callable=AsyncMock, return_value=task):
            response = self.client.get(f"/api/tasks/{task_id}/stream")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.text,
            'data: {"event": "complete", "report": {"raw_results": ["done"]}}\n\n',
        )

    def test_versioned_api_prefix_is_not_registered(self) -> None:
        response = self.client.get(f"/api/v1/tasks/{uuid.uuid4()}")

        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
