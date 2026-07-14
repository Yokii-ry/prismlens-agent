# ARQ Worker Task
# 非手动调用
import json
import uuid

from arq.connections import RedisSettings
import redis.asyncio as aioredis
from app.core.config import settings
from app.core.debug_log import debug_panel
from app.db.curd import update_task_status
from app.db.models import TaskStatus
from app.db.session import AsyncSessionLocal
from app.pipeline.graph import build_graph
from app.pipeline.state import PrismState

async def run_research_graph(ctx:dict,task_id:str,event_query:str) -> dict:
    """
    ARQ 任务入口函数

    参数: 
       ctx: 上下文信息
       task_id: 任务ID
       event_query: 用户输入的事件查询

    返回:
        dict: 任务结果
    """
    debug_panel(
        "worker",
        "收到研究任务",
        {"task_id": task_id, "event_query": event_query},
    )

    #task_id从字符串转回UUID类型，数据库操作需要UUID类型
    task_uuid = uuid.UUID(str(task_id))
    channel = settings.progress_channel(task_uuid)
    redis = aioredis.from_url(settings.REDIS_URL,decode_responses=True)

    async def publish_progress(payload: dict) -> None:
        await redis.publish(channel,json.dumps(payload,ensure_ascii=False))

    #步骤一：work任务状态从PENDING更新为RUNNING
    async with AsyncSessionLocal() as db:
        await update_task_status(db,task_uuid,TaskStatus.RUNNING)
   
  # 步骤二：构建图，配置checkpoint
    try:
        await publish_progress({"event":"started"})

        from app.pipeline.checkpoint import get_checkpointer
        async with get_checkpointer() as checkpointer:
            graph = build_graph(checkpointer=checkpointer)
            #用task_id作为checkpoint的thread_id
            config ={"configurable":{"thread_id":task_uuid}}
            #步骤三：运行图，传入初始状态
            #astream会在每个节点完成后产出增量，方便同步推送SSE进度
            result: dict = {}
            async for chunk in graph.astream(
                PrismState(
                  event_query=event_query,
                  search_queries=[],
                  raw_results=[],
                  retry_count=0
                ),
                config=config,
                # 增量更新模式，只更新变化的部分，避免重复计算
                stream_mode="updates"
            ):
                for node_name,node_result in chunk.items():
                    await publish_progress({"event":"step","node":node_name})
                    debug_panel(
                        "worker",
                        "研究图节点完成",
                        {"task_id": str(task_uuid), "node": node_name, "updates": node_result},
                        status="success",
                    )
                    if isinstance(node_result,dict):
                        result.update(node_result)

        debug_panel(
            "worker",
            "研究图完成",
            {
                "task_id": str(task_uuid),
                "raw_result_count": len(result.get("raw_results", [])),
                "result": result,
            },
            status="success",
        )
        final_report = result.get("final_report")
        if final_report is None:
            final_report = {
                "raw_results": result.get("raw_results", []),
            }
        #步骤四：把结果写进数据库，更新任务状态为COMPLETED
        async with AsyncSessionLocal() as db:
            await update_task_status(
                db,
                task_uuid,
                TaskStatus.COMPLETED,
                # 把final_report作为最终报告存进去
                final_report=final_report
            )
        await publish_progress({"event":"complete","report":final_report})
        debug_panel(
            "worker",
            "研究图跑完了，更新任务状态为COMPLETED",
            {"task_id": str(task_uuid), "report": final_report},
            status="success",
        )
    except Exception as exc:
        # 捕获异常，更新任务状态为FAILED，记录异常信息
        debug_panel(
            "worker",
            "研究图跑失败，更新任务状态为FAILED",
            {"task_id": str(task_uuid), "error": str(exc)},
            status="error",
        )
        async with AsyncSessionLocal() as db:
            await update_task_status(
                db,
                task_uuid,
                TaskStatus.FAILED,
                error_message=str(exc)
            )
        await publish_progress({"event":"error","message":str(exc)})
    finally:
        await redis.aclose()

# ARQ worker的配置类，告诉ARQ这个worker可以运行哪些函数
class WorkerSettings:
    # 注册任务函数，worker启动后只会处理这里列举的函数
    functions = [run_research_graph]
    # redis连接配置，worker靠这个连上队列
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)

    # 同时处理的最大任务数，避免同时处理太多任务，导致内存不足
    max_jobs = settings.MAX_CONCURRENT_JOBS
