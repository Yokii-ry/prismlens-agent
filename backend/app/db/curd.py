# 数据库CURD操作，例如创建、更新、删除、查询等
# 只跟数据库打交道，不包含任何业务逻辑
# 业务模块（什么时候入队，什么时候生成报告）放在其他文件里面
import uuid
# 导入数据库模型
from sqlalchemy import select
# 导入异步会话
from sqlalchemy.ext.asyncio import AsyncSession
# 导入数据库模型
from app.db.models import ResearchTask,TaskStatus,User


async def ensure_user_exists(db: AsyncSession, user_id: uuid.UUID, email: str) -> User:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is not None:
        return user

    user = User(id=user_id, email=email)
    db.add(user)
    await db.flush()
    return user


async def create_research_task(db: AsyncSession, user_id: uuid.UUID, event_query:str,thread_id:str) -> ResearchTask:
    # 创建一条新的任务记录，状态默认是PENDING（等待worker处理）
    task = ResearchTask(
        user_id=user_id,
        event_query=event_query,
        thread_id=thread_id,
        status=TaskStatus.PENDING,
    )
    # 加入session，准备提交到数据库
    db.add(task) 
    # 提交事务，真正写入数据库
    await db.commit()
    # 从数据库重新读取这条记录（获取到数据库自动生成的字段，如id、created_at等）
    await db.refresh(task)
    return task

# 根据任务id查一条任务记录
async def get_task(
    db: AsyncSession,
    task_id: uuid.UUID,
)-> ResearchTask | None:
    # scalar_one_or_none：返回单个结果或None，如果没有找到则返回None,不抛异常
    result = await db.execute(
        select(ResearchTask).where(ResearchTask.id == task_id)
    )
    return result.scalar_one_or_none()

# 查询某个指定用户的任务列表，根据创建时间倒序排列（最新的在最前面）
async def list_tasks_for_user(db: AsyncSession, user_id: uuid.UUID) -> list[ResearchTask]:
    result = await db.execute(
        select(ResearchTask).where(ResearchTask.user_id == user_id).order_by(ResearchTask.created_at.desc())
    )
    return list(result.scalars().all())

# 更新任务状态，同时可以顺便写入最终报告内容或错误信息
async def update_task_status(db: AsyncSession, task_id: uuid.UUID, status: TaskStatus,final_report:dict | None = None,error_message:str | None = None) -> None:
    # 先查询出任务记录
    task = await get_task(db, task_id)
    if task is None:
        # 如果任务记录不存在，直接返回
        return
    task.status = status
    # 只有传了final_report或error_message时才更新
    if final_report is not None:
        task.final_report = final_report
    if error_message is not None:
        task.error_message = error_message
    # 提交事务，真正写入数据库
    await db.commit()
