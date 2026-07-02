# uuid：生成全局唯一标识符（比如每个用户、每条任务的主键ID）
import uuid

# datetime：用于声明"创建时间"、"更新时间"这类时间字段的Python类型
from datetime import datetime

# Enum：Python 自带的枚举类型，用来限定一个字段只能是几个固定值之一
from enum import Enum

# 从 SQLAlchemy 核心模块导入几种字段类型和工具：
# DateTime：日期时间类型
# Enum as SAEnum：SQLAlchemy 自己的枚举字段类型（重命名避免跟上面 Python 的 Enum 撞名）
# ForeignKey：外键，用于声明"这个字段引用了另一张表的某个字段"
# String：字符串类型，需要指定长度
# Text：不限长度的长文本类型
# func：SQL 内置函数的封装，下面会用 func.now() 表示"取当前时间"
from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, String, Text, func

# PostgreSQL 专用的字段类型：
# JSONB：以二进制JSON格式存储结构化数据，支持查询、索引，比普通文本字段更适合存报告这类结构化结果
# UUID：PostgreSQL原生的UUID类型，比用字符串存UUID更高效
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID

# Mapped：类型注解工具，配合下面的mapped_column一起声明字段
# mapped_column：声明一个具体的数据库列，可以指定主键、是否唯一、默认值等
# relationship：声明表与表之间的关联关系（比如一个User对应多个ResearchTask）
from sqlalchemy.orm import Mapped, mapped_column, relationship

# 从刚才写的 session.py 里导入 Base 基类，所有表模型都要继承它
from app.db.session import Base


# 定义任务状态的枚举，限定 ResearchTask.status 字段只能是这四个值之一
class TaskStatus(str, Enum):
    PENDING = "pending"      # 已创建，等待Worker处理
    RUNNING = "running"      # Worker正在执行
    COMPLETED = "completed"  # 执行完成
    FAILED = "failed"        # 执行失败


# 用户表模型，继承 Base 后会被 SQLAlchemy 识别为对应数据库里的一张表
class User(Base):
    # 指定这张表在数据库里的实际名字
    __tablename__ = "users"

    # 主键字段，类型是UUID，默认值用 uuid.uuid4 自动生成一个新的唯一ID
    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # 邮箱字段，最长255字符，unique=True表示不能有两个用户用同一个邮箱
    # index=True表示给这个字段建索引，加快按邮箱查找用户的速度
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)

    # 创建时间，server_default=func.now()表示由数据库自动填入"当前时间"，不用应用代码手动赋值
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # 声明关联关系：一个用户可以有多条任务记录
    # back_populates="user" 表示这是双向关系，对应ResearchTask里的 user 字段
    tasks: Mapped[list["ResearchTask"]] = relationship(back_populates="user")


# 研究任务表模型，每一次"多棱镜"查询对应一条记录
class ResearchTask(Base):
    __tablename__ = "research_tasks"

    # 主键，同样用UUID自动生成
    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # 外键字段，指向users表的id字段，表示"这条任务属于哪个用户"
    # index=True：经常会按user_id查询某用户的所有任务，建索引加快查询
    user_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), index=True)

    # 用户输入的查询内容（比如"某地推行的新政策"），用Text因为长度不固定
    event_query: Mapped[str] = mapped_column(Text)

    # 当前任务状态，限定为TaskStatus枚举里的值，默认是PENDING（刚创建还没开始跑）
    status: Mapped[TaskStatus] = mapped_column(SAEnum(TaskStatus), default=TaskStatus.PENDING, index=True)

    # 如果任务执行失败，记录错误信息；正常情况下是None，所以类型标注里加了 | None
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # LangGraph跑图时用来标识这次任务的唯一线程ID，后续接Checkpointer时会用到
    # unique=True保证每条任务对应独一无二的thread_id
    thread_id: Mapped[str] = mapped_column(String(64), unique=True)

    # 最终生成的报告，用JSONB存储结构化结果（共识/分歧等）；任务还没跑完时是None
    final_report: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # 创建时间，数据库自动填当前时间
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # 更新时间：第一次创建时填当前时间(server_default)，
    # 以后每次这条记录被更新时自动刷新成最新时间(onupdate)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # 声明反向关联：通过这个字段可以直接拿到这条任务所属的User对象
    user: Mapped["User"] = relationship(back_populates="tasks")