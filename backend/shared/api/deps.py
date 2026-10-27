import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.core.security import decode_access_token
from shared.db.session import get_db
from shared.models.entities import User
from shared.services.sessions import ACCESS_COOKIE, session_is_active

security = HTTPBearer(auto_error=False)

__all__ = ["get_db", "get_current_user", "require_user"]


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db, scope="function"),
) -> User | None:
    # API clients send a bearer token; browsers send the httpOnly access cookie.
    token = credentials.credentials if credentials else request.cookies.get(ACCESS_COOKIE)
    if not token:
        return None
    try:
        payload = decode_access_token(token)
        user_id = int(payload["sub"])
        session_id = int(payload["sid"]) if "sid" in payload else None
    except (jwt.PyJWTError, KeyError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token") from None
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active or not user.organization.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account disabled or not found")
    if session_id is not None and not await session_is_active(db, session_id, user.id):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session ended. Sign in again.")
    request.state.user = user
    request.state.session_id = session_id
    return user


async def require_user(user: User | None = Depends(get_current_user)) -> User:
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return user
