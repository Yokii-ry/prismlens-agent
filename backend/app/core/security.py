# 加密和解密token

# 导入time模块
from datetime import datetime, timedelta, timezone
# 导入typing模块
from typing import Any

import jwt
from passlib.context import CryptContext
from app.core.config import settings

# ====配置项====
# secret_key: 用来给 JWT 签名的密钥，绝对不能泄露或提交到git仓库
SECRET_KEY = settings.JWT_SECRET_KEY
# 签名算法，HS256是最常用的对称加密算法
ALGORITHM = settings.JWT_ALGORITHM
# 过期时间，单位为分钟
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES

# 密码加密上下文，指定用bcrypt算法
pwd_context = CryptContext(schemes=["bcrypt"],deprecated="auto")

# 密码加密函数，返回加密后的密码
def hash_password(password: str) -> str:
    """把明文密码加密成 hash,存数据库时用这个已加密好的hash字符"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """登录时用：比对用户输入的明文密码和数据库里存的hash是否匹配"""
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict[str, Any]) -> str:
    """创建访问令牌 JWT Token"""
    if not SECRET_KEY:
        raise RuntimeError("JWT_SECRET_KEY 未配置，请在 backend/.env 中填写 JWT 签名密钥")
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> dict[str, Any] | None:
    """验证并解析 JWT Token, 失败返回None"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        # 过期
        return None
    except jwt.InvalidTokenError:
        # 无效
        return None
