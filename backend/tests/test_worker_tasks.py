import uuid
import unittest
from unittest.mock import AsyncMock, patch

from app.db.models import TaskStatus
from app.worker import tasks


class _FakeSessionContext:
    session = object()

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, exc_type, exc, traceback):
        return False


class _FakeCompiledGraph:
    async def astream(self, state, config, stream_mode):
        self.state = state
        self.config = config
        self.stream_mode = stream_mode
        yield {"plan": {"search_queries": ["政策影响分析 支持", "政策影响分析 反对"]}}
        yield {"search": {"raw_results": [{"title": "result"}]}}
        yield {"reflect": {"retry_count": 1}}
        yield {"generate_report": {"final_report": {"summary": "report from graph"}}}


class _FakeCheckpointerContext:
    async def __aenter__(self):
        return object()

    async def __aexit__(self, exc_type, exc, traceback):
        return False


class WorkerTasksTest(unittest.IsolatedAsyncioTestCase):
    async def test_run_research_graph_uses_task_id_argument_from_arq_job(self) -> None:
        task_id = uuid.uuid4()
        redis = AsyncMock()

        with (
            patch.object(tasks, "AsyncSessionLocal", return_value=_FakeSessionContext()),
            patch.object(tasks, "update_task_status", new_callable=AsyncMock) as update_task_status,
            patch.object(tasks, "build_graph", return_value=_FakeCompiledGraph()),
            patch("app.pipeline.checkpoint.get_checkpointer", return_value=_FakeCheckpointerContext()),
            patch("redis.asyncio.from_url", return_value=redis),
        ):
            await tasks.run_research_graph(
                ctx={},
                task_id=str(task_id),
                event_query="政策影响分析",
            )

        self.assertEqual(
            update_task_status.await_args_list[0].args[:3],
            (_FakeSessionContext.session, task_id, TaskStatus.RUNNING),
        )
        self.assertEqual(
            update_task_status.await_args_list[1].args[:3],
            (_FakeSessionContext.session, task_id, TaskStatus.COMPLETED),
        )
        self.assertEqual(
            update_task_status.await_args_list[1].kwargs["final_report"],
            {"summary": "report from graph"},
        )
        redis.publish.assert_any_await(
            tasks.settings.progress_channel(task_id),
            '{"event": "started"}',
        )
        redis.publish.assert_any_await(
            tasks.settings.progress_channel(task_id),
            '{"event": "step", "node": "plan"}',
        )
        redis.publish.assert_any_await(
            tasks.settings.progress_channel(task_id),
            '{"event": "step", "node": "search"}',
        )
        redis.publish.assert_any_await(
            tasks.settings.progress_channel(task_id),
            '{"event": "step", "node": "reflect"}',
        )
        redis.publish.assert_any_await(
            tasks.settings.progress_channel(task_id),
            '{"event": "step", "node": "generate_report"}',
        )
        redis.publish.assert_any_await(
            tasks.settings.progress_channel(task_id),
            '{"event": "complete", "report": {"summary": "report from graph"}}',
        )
        redis.aclose.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
