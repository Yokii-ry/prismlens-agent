from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.errors import AppError, ErrorCode
from app.api.responses import success_response
from app.core.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.db.models import User
from app.db.session import get_db
from app.schemas.auth import LoginRequest, LoginResponse, RegisterRequest

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login(data: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)):
    # 1.查找用户是否存在
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    # 2.用户不存在或密码错误，统一报同一个错
    if not user or not user.hashed_password or not verify_password(data.password, user.hashed_password):
        raise AppError(
            status_code=401,
            code=ErrorCode.INVALID_CREDENTIALS,
            message="用户名或密码错误",
        )

    # 3.生成token
    access_token = create_access_token({"user_id": str(user.id), "email": user.email})

    # 4.httpOnly设置token到cookie
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        # 防止CSRF攻击:lax模式允许在同源的iframe中访问cookie
        samesite="lax",
        # 开发环境可以设置为False，生产环境需要设置为True
        secure=False,
        # 设置token过期时间 30分钟
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )

    return success_response(message="登录成功", data={"email": user.email})


@router.post("/register", response_model=LoginResponse)
async def register(
    data: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    # 1.检查用户是否已注册过
    result = await db.execute(select(User).where(User.email == data.email))
    existing_user = result.scalar_one_or_none()

    if existing_user is not None:
        raise AppError(
            status_code=400,
            code=ErrorCode.USER_ALREADY_EXISTS,
            message="用户已存在",
        )

    # 2.密码加密后存库，绝不存明文
    new_user = User(
        email=data.email,
        hashed_password=hash_password(data.password),
    )
    db.add(new_user)
    await db.commit()
    # 3.刷新用户对象，获取刚创建的id
    await db.refresh(new_user)
    return success_response(message="注册成功", data={"email": new_user.email})
