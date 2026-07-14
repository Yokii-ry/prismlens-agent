# langGraph postgresSql checkpoint
# 负责把每个节点跑完之后的State 持久化到数据库，支持断点恢复
from contextlib import asynccontextmanager
# 导入异步的postgres saver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
# 导入配置
from app.core.config import settings

# 
def _get_checkpoint_dsn() -> str:
    # AsyncPostgresSaver 用的是 psycopg3 风格的 DSN，
    # 跟业务用的 asyncpg DSN 格式略有不同，需要转换一下
    # postgresql+asyncpg://... → postgresql://...
    return settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")

@asynccontextmanager
async def get_checkpointer():
    """
    获取一个 checkpointer 实例，用完自动关闭连接
    用法： 
       async with get_checkpointer() as checkpointer
           graph = build_graph().compile(checkpointer=checkpointer)
           await graph.ainvoke(...)
    """
    # 获取数据库连接字符串
    dsn = _get_checkpoint_dsn()
    # 创建一个 AsyncPostgresSaver 实例
    async with AsyncPostgresSaver.from_conn_string(dsn) as checkpointer:
        # 返回 checkpointer 实例
        yield checkpointer
        # 自动关闭连接

async def setup_checkpoint_tables() -> None:
    """
    首次部署调用一次，创建checkpointer所需的内部表。
    langGraph 自己管理这些表，跟业务表的Alembic迁移是两套独立机制
    调用一次之后不需要再调用，除非数据库被清空重置
    """
    async with get_checkpointer() as checkpointer:
        await checkpointer.setup()
