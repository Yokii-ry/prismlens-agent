# 应用全局配置，所有环境变量从这个文件读取
# 用pydantic-settings管理配置:
# 1.自动从.env文件读取，不用手动os.environ.get(...)
# 2.有类型校验
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # settingsConfigDict:设置配置文件的读取方式,默认是dotenv，这里改为env
    # env_file=".env",表示从根目录的.env文件读取
    # env_file_encoding="utf-8",表示文件编码为utf-8,不会出现中文乱码
    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env"),
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
    
    # !!TODO搜索引擎相关,先预留
    TAVILY_API_KEY: str = "tavily-a4220804343a47468f05168365987969"

    # worker并发限制，最多跑几个实例
    MAX_CONCURRENT_JOBS: int = 2

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

#创建一个单例实例，方便在其他地方统一导入
settings = Settings()
