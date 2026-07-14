import unittest
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.api.errors import AppError, ErrorCode
from app.api import routes
from app.db.models import TaskStatus
from app.db.session import get_db
from main import app


async def override_get_db():
    yield object()


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
            response = self.client.get("/api/v1/tasks/12")

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
            response = self.client.get(f"/api/v1/tasks/{task_id}")

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
            response = self.client.get(f"/api/v1/tasks/{task_id}")

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
            response = self.client.post("/api/v1/tasks", params={"event_query": "政策影响分析"})

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

    def test_create_task_is_available_on_unversioned_api_prefix(self) -> None:
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

    def test_get_task_status_is_available_on_unversioned_api_prefix(self) -> None:
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
            response = self.client.get(f"/api/v1/tasks/{task_id}/stream")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.text,
            'data: {"event": "complete", "report": {"raw_results": ["done"]}}\n\n',
        )


if __name__ == "__main__":
    unittest.main()
