from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
# 跨域请求中间件
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.errors import AppError
from app.api.exception_handlers import app_error_handler, internal_error_handler, validation_error_handler
from app.api.routes import router

app = FastAPI(title='PrismLen agent')

app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)
app.add_exception_handler(Exception, internal_error_handler)

# 配置跨域请求
app.add_middleware(
    CORSMiddleware,
    # 只允许列表中的前端域名访问
    allow_origins=[settings.FRONTEND_URL],
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
