from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
# 跨域请求中间件
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.errors import AppError
from app.api.exception_handlers import app_error_handler, internal_error_handler, validation_error_handler
from app.api.routes import router
# 生命周期钩子
from contextlib import asynccontextmanager
# 初始化checkpoint表
from app.pipeline.checkpoint import setup_checkpoint_tables

# lifespan: fast api 的生命周期钩子
# yield 之前的代码在应用启动时执行，yield之后的代码在应用关闭时执行
# 类比js里的process.on('beforeExit', () => {})
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 应用启动时：初始化checkpoint表
    await setup_checkpoint_tables()
    yield
    # 应用关闭时：当前没有要清空的资源，暂时留空

app = FastAPI(title='PrismLen agent',lifespan=lifespan)

app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)
app.add_exception_handler(Exception, internal_error_handler)

# 配置跨域请求
app.add_middleware(
    CORSMiddleware,
    # 只允许列表中的前端域名访问
    allow_origins=settings.cors_allowed_origins,
    allow_origin_regex=settings.CORS_ALLOWED_ORIGIN_REGEX,
    # 允许携带cookie
    allow_credentials=True,
    # 允许所有方法
    allow_methods=["*"],
    # 允许所有头
    allow_headers=["*"],
)

# 把路由模块注册进来
app.include_router(router, prefix="/api/v1")
app.include_router(router, prefix="/api")

# 健康检查接口
@app.get("/health")
def read_root():
    return {"message": "OK", "code": 0}
