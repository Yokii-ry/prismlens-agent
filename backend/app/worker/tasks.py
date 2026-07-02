# ARQ Worker Task
# 非手动调用
import uuid

from arq.connections import RedisSettings
from app.db.crud import update_task_status,create_task
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
    print(f"ARQ Worker收到任务: {event_query},开始跑图,任务id: {ctx['task_id']}")

    #task_id从字符串转回UUID类型，数据库操作需要UUID类型
    task_uuid = uuid.UUID(ctx['task_id'])
    #步骤一：work任务状态从PENDING更新为RUNNING
    async with AsyncSessionLocal() as db:
        await update_task_status(db,task_uuid,TaskStatus.RUNNING)
   
  # 步骤二：构建图，配置checkpoint
    try:
        from langgraph.checkpoint.memory import MemorySaver
        checkpointSaver = MemorySaver()
        graph = build_graph().compile(checkpointer=checkpointSaver)
        #用task_id作为checkpoint的thread_id
        config ={"configurable":{"thread_id":task_uuid}}
        #步骤三：运行图，传入初始状态
        #ainvoke是invoke的异步版本，返回一个协程对象，需要await执行
        result = await graph.ainvoke(
            PrismState(
              event_query=event_query,
              search_queries=[],
              raw_results=[],
              retry_count=0
            ),
            config=config
        )
        print(f"图运行完成,结果: {result}")
        #步骤四：把结果写进数据库，更新任务状态为COMPLETED
        async with AsyncSessionLocal() as db:
            await update_task_status(
                db,
                task_uuid,
                TaskStatus.COMPLETED,
                # 把raw_results作为最终报告存进去
                # !!TODO synthesize节点做好以后，换成真正完整的报告
                final_report={
                    "raw_results":result.get("raw_results",[]),
                }
            )
    except Exception as exc:
        # 捕获异常，更新任务状态为FAILED，记录异常信息
        print(f"图运行失败,任务id: {task_uuid},异常: {exc}")
        async with AsyncSessionLocal() as db:
            await update_task_status(
                db,
                task_uuid,
                TaskStatus.FAILED,
                error_message=str(exc)
            )

# ARQ worker的配置类，告诉ARQ这个worker可以运行哪些函数
class workerSettings:
    # 注册任务函数，worker启动后只会处理这里列举的函数
    functions = [run_research_graph]
    # redis连接配置，worker靠这个连上队列
    redis_settings = RedisSettings.from_dsn('redis://localhost:6379/0')

    # 同时处理的最大任务数，避免同时处理太多任务，导致内存不足
    max_jobs = 2

