# 数据库CURD操作，例如创建、更新、删除、查询等
# 只跟数据库打交道，不包含任何业务逻辑
# 业务模块（什么时候入队，什么时候生成报告）放在其他文件里面
import uuid
# 导入数据库模型
from sqlalchemy import select
# 导入异步会话
from sqlalchemy.ext.asyncio import AsyncSession
# 导入数据库模型
from app.db.models import ResearchTask,TaskStatus


async def create_research_task(db: AsyncSession, user_id:uid.UUID, event_query:str,thread_id:str) -> ResearchTask:
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

async def get_task(
    db: AsyncSession,
    task_id: uuid.UUID,
)-> ResearchTask | None:
    # 根据任务id查一条任务记录
    # scalar_one_or_none：返回单个结果或None，如果没有找到则返回None,不抛异常
    result = await db.execute(
        
    )
