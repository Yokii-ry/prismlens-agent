# API路由层
# 职责：接收请求、写入数据库、入队、返回响应
# 不负责跑图，那是worker的工作
import json
import uuid

from fastapi import APIRouter,Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

# ARQ的连接池，用来把任务塞进redis队列
from arq import create_pool
from arq.connections import RedisSettings

# 读取配置
from app.core.config import settings
from app.core.debug_log import debug_panel

# 导入API响应工具
from app.api.errors import ErrorCode
from app.api.responses import error_json_response, success_response

# 导入db模块
from app.db.curd import create_research_task,ensure_user_exists,get_task,list_tasks_for_user
from app.db.models import TaskStatus
from app.db.session import get_db

# APIRouter：路由定义和fastApi分开，方便模块化开发
router = APIRouter(tags=["tasks"])

# !!TODO 占位用户ID，等认证模块写好之后再替换
PLACEHOLDER_USER_ID = "00000000-0000-0000-0000-000000000001"
PLACEHOLDER_USER_EMAIL = "placeholder@prismlens.local"

@router.post("/tasks")
async def create_task(event_query:str,db:AsyncSession=Depends(get_db))->dict:
    """
    提交一个新的研究任务
    街道请求后立即返回，不等图跑完-真正跑图是worker的工作
    """
    debug_panel("api", "create_task request received", {"event_query": event_query})
    # 用任务id作为thread_id，方便后续查询,保证唯一性
    thread_id = str(uuid.uuid4())
    # 步骤一：在数据库里写入一条PENDING状态的记录
    user_id = uuid.UUID(PLACEHOLDER_USER_ID)
    await ensure_user_exists(db=db,user_id=user_id,email=PLACEHOLDER_USER_EMAIL)
    task = await create_research_task(db=db,user_id=user_id,thread_id=thread_id,event_query=event_query)
    # 步骤二： 把任务塞进redis队列，worker会监听这个队列，拿到任务后开始跑图
    redis = await create_pool(RedisSettings.from_dsn(settings.REDIS_URL))
    await redis.enqueue_job("run_research_graph",task_id=task.id,event_query=event_query)
    await redis.close()
    debug_panel(
        "api",
        "task queued",
        {
            "task_id": str(task.id),
            "thread_id": thread_id,
            "status": TaskStatus.PENDING.value,
        },
        status="success",
    )
    # 立刻返回任务id，前端拿着这个id来轮询状态或者订阅sse
    return success_response(
        message="Task created",
        data={
            "task_id":str(task.id),
            "task_status":TaskStatus.PENDING.value,
        },
    )

@router.get("/tasks/{task_id}")
async def get_task_status(task_id:uuid.UUID,db:AsyncSession=Depends(get_db))->dict:
    """
    查询一个任务的当前状态和结果
    前端可以轮询这个接口，也可以配合sse实时更新
    """
    task=await get_task(db=db,task_id=task_id)
    if not task:
        debug_panel(
            "api",
            "task status lookup failed",
            {"task_id": str(task_id), "reason": "not found"},
            status="error",
        )
        return error_json_response(
            status_code=404,
            code=ErrorCode.TASK_NOT_FOUND,
            message="Task not found",
        )
    return success_response(
        message="Task fetched",
        data={
            "task_id":str(task.id),
            "task_status":task.status.value,
            "event_query":task.event_query,
            "final_report":task.final_report,
            "error_message":task.error_message,
            "created_at":task.created_at.isoformat(),
        },
    )

def sse_data(payload: dict) -> str:
    return f"data: {json.dumps(payload,ensure_ascii=False)}\n\n"


def terminal_progress_payload(task) -> dict | None:
    if task is None:
        return {"event":"error","message":"Task not found"}
    if task.status == TaskStatus.COMPLETED:
        return {"event":"complete","report":task.final_report}
    if task.status == TaskStatus.FAILED:
        return {"event":"error","message":task.error_message or "Task failed"}
    return None


@router.get("/tasks/{task_id}/stream")
async def stream_task_results(task_id:uuid.UUID,db:AsyncSession=Depends(get_db)):
    """
    SSE接口：实时推送任务执行进度给前端
    前端用 EventSource 连上这个接口，每当worker跑完一个节点，就推送一次进度
    """
    import redis.asyncio as aioredis

    debug_panel("api", "sse stream opened", {"task_id": str(task_id)})
    terminal_payload = terminal_progress_payload(await get_task(db=db,task_id=task_id))
    if terminal_payload is not None:
        debug_panel(
            "api",
            "sse returned terminal state",
            {"task_id": str(task_id), "payload": terminal_payload},
        )
        async def completed_event_generator():
            yield sse_data(terminal_payload)

        return StreamingResponse(
            completed_event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control":"no-cache",
                "X-Accel-Buffering":"no",
            },
        )

    async def event_generator():
        # 建立redis连接，订阅这个任务专属的publish channel & subscribe channel
        # decode_responses=True: 将redis返回的二进制数据转换为字符串
        r = aioredis.from_url(settings.REDIS_URL,decode_responses=True)
        # 订阅任务专属的publish channel & subscribe channel
        pubsub = r.pubsub()
        # 每个任务有自己的subscribe channel，只订阅自己的进度
        # 格式是： f"multiprism:progress:{task_id}"
        channel = f"multiprism:progress:{task_id}"
        await pubsub.subscribe(channel)

        try:
            terminal_payload = terminal_progress_payload(await get_task(db=db,task_id=task_id))
            if terminal_payload is not None:
                yield sse_data(terminal_payload)
                return

            async for message in pubsub.listen():
                # pubsub.listen() 会收到各自类型的消息，只用处理真正的数据消息
                if message['type'] == 'message':
                    data=message['data']
                    try:
                        log_payload = json.loads(data)
                    except json.JSONDecodeError:
                        log_payload = data
                    debug_panel(
                        "api",
                        "sse event forwarded",
                        {"task_id": str(task_id), "payload": log_payload},
                    )
                    # sse数据格式：data: {data}\n\n 里面data是json字符串 必须用两个\n\n来结束
                    yield f"data: {data}\n\n"

                    # 如果收到的是complete或error事件，说明任务结束了，关闭连接
                    try:
                        parsed = json.loads(data)
                        if parsed.get('event') in ('complete','error'):
                            break
                    except json.JSONDecodeError:
                        pass
        finally:
            # 无论正常结束还是前端断开连接，都要清理redis订阅
            await pubsub.unsubscribe(channel)
            await r.aclose()

    # streamingResponse：fastapi的流式响应，支持sse
    # media_type="text/event-stream" 是sse协议规定的content-type
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            # 禁用浏览器缓存，确保前端能实时收到最新数据
            "Cache-Control":"no-cache",
            # 禁用nginx缓冲，确保数据立即发送到前端
            "X-Accel-Buffering":"no",
        },
    )
