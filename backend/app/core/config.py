# 应用全局配置，所有环境变量从 backend/.env 读取
# 用pydantic-settings管理配置:
# 1.自动从.env文件读取，不用手动os.environ.get(...)
# 2.有类型校验
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]

class Settings(BaseSettings):
    # env_file 使用绝对路径，确保从项目根目录或 backend/ 目录启动时都读取同一个文件。
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 数据库连接字符串
    # 应用本身用asyncpg驱动（异步），所以是postgresql+asyncpg
    DATABASE_URL: str = "postgresql+asyncpg://multiprism:multiprism@localhost:5432/multiprism"
    # Redis连接字符串
    REDIS_URL: str = "redis://localhost:6379/0"

    # LLM相关：DeepSeek 提供 OpenAI-compatible API，所以继续使用 OPENAI_* 命名
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.deepseek.com"
    OPENAI_MODEL: str = "deepseek-chat"
    OPENAI_TEMPERATURE: float = 0
    
    # !!TODO搜索引擎相关,先预留
    TAVILY_API_KEY: str = ""
    TAVILY_MAX_RESULTS: int = 3

    # worker并发限制，最多跑几个实例
    MAX_CONCURRENT_JOBS: int = 2

    # pipeline运行策略
    PIPELINE_MAX_RETRIES: int = 2
    REFLECT_RESULT_CONTENT_CHARS: int = 200
    REPORT_RESULT_CONTENT_CHARS: int = 300
    REDIS_PROGRESS_CHANNEL_PREFIX: str = "multiprism:progress:"

    # 临时用户配置。接入真实认证后可以删除。
    PLACEHOLDER_USER_ID: str = "00000000-0000-0000-0000-000000000001"
    PLACEHOLDER_USER_EMAIL: str = "placeholder@prismlens.local"

    # JWT相关
    JWT_SECRET_KEY: str = "3a6ae5d6f371b330203f3a75cb6e8267bf89d7fc36caaae584df0fa8d97591c5"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # front web url,cors跨域请求需要
    FRONTEND_URL: str = "http://localhost:7777"
    # 逗号分隔的前端来源。保留 FRONTEND_URL 是为了兼容旧配置。
    CORS_ALLOWED_ORIGINS: str = "http://localhost:7777,http://127.0.0.1:7777"
    # 开发时常用局域网 IP 访问 Next.js，例如 http://192.168.0.6:7777
    CORS_ALLOWED_ORIGIN_REGEX: str = r"^http://192\.168\.\d{1,3}\.\d{1,3}:7777$"

    @property
    def cors_allowed_origins(self) -> list[str]:
        origins = [
            origin.strip()
            for origin in self.CORS_ALLOWED_ORIGINS.split(",")
            if origin.strip()
        ]
        if self.FRONTEND_URL and self.FRONTEND_URL not in origins:
            origins.append(self.FRONTEND_URL)
        return origins

    @property
    def alembic_database_url(self) -> str:
        return self.DATABASE_URL.replace(
            "postgresql+asyncpg://",
            "postgresql+psycopg2://",
        )

    def progress_channel(self, task_id: object) -> str:
        return f"{self.REDIS_PROGRESS_CHANNEL_PREFIX}{task_id}"

#创建一个单例实例，方便在其他地方统一导入
settings = Settings()
