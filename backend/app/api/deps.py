from fastapi import Depends,Cookie,HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.db.session import get_db
from app.db.models import User

async def get_current_user(
    # 从Cookie中获取access_token
    access_token:str | None = Cookie(default=None),
    db:AsyncSession = Depends(get_db),
)-> User:
    