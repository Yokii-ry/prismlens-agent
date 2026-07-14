# 从 SQLAlchemy 的异步扩展里，导入三个东西：
# AsyncSession：异步数据库会话类型（一次"对话"，用来发查询、提交事务）
# async_sessionmaker：创建"会话工厂"的工具，调用它能生产出一个个 AsyncSession
# create_async_engine：创建数据库连接引擎，真正负责建立和管理网络连接
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# DeclarativeBase：所有 ORM 模型类的基类，继承它之后，
# 一个普通 Python 类才会被 SQLAlchemy 识别成"对应一张数据库表"
from sqlalchemy.orm import DeclarativeBase

# 从config.py中导入settings
from app.core.config import settings

# 数据库连接字符串，格式是：数据库类型+驱动名://用户名:密码@主机:端口/数据库名
# 这里用 asyncpg 驱动（异步），对应你之前 docker run 时设置的用户名密码
DATABASE_URL = settings.DATABASE_URL

# 创建数据库引擎，整个应用生命周期内只需要一个引擎实例（这里创建一次，全局复用）
# echo=True 表示把每一条实际执行的 SQL 打印到终端，方便开发时观察，上线后改成 False
engine = create_async_engine(DATABASE_URL, echo=True)

# 创建一个"会话工厂"，以后每次要操作数据库，就调用 AsyncSessionLocal() 生成一个新会话
# bind=engine：告诉这个工厂用哪个引擎去连接数据库
# expire_on_commit=False：提交事务后，之前查出来的对象数据不会被清空失效，
#   方便事务提交完之后还能继续读取对象的字段值
# class_=AsyncSession：指定生成的会话是异步类型
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


# 定义所有 ORM 模型的公共基类
# 之后写的 User、ResearchTask 等表模型类，都要继承这个 Base
class Base(DeclarativeBase):
    pass
