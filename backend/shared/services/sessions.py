"""Browser sessions and emailed single-use tokens.

A sign-in creates an AuthSession row. The browser holds two httpOnly cookies: a short-lived access JWT
(carrying the session id as `sid`) and a long-lived refresh token, rotated on every use. Revoking the row
signs that device out on its next request.
"""

from datetime import datetime, timedelta, timezone

from fastapi import Request, Response
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from shared.api.rate_limit import client_ip
from shared.core.config import get_settings
from shared.core.security import create_access_token, generate_invite_token, hash_token
from shared.models.entities import AuthSession, User, UserToken
from shared.schemas.common import Token, UserOut

ACCESS_COOKIE = "aihr_access"
REFRESH_COOKIE = "aihr_refresh"

PURPOSE_RESET = "password_reset"
PURPOSE_VERIFY = "verify_email"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def aware(dt: datetime) -> datetime:
    # SQLite drops tzinfo; values are always stored as UTC.
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _refresh_path() -> str:
    return f"{get_settings().api_v1_prefix}/auth"


def set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    settings = get_settings()
    common = {"httponly": True, "secure": settings.cookie_secure, "samesite": "lax", "domain": settings.cookie_domain}
    response.set_cookie(ACCESS_COOKIE, access_token, max_age=settings.access_token_expire_minutes * 60, path="/", **common)
    # Only sent to the auth endpoints, so ordinary API calls never carry it.
    response.set_cookie(
        REFRESH_COOKIE, refresh_token, max_age=settings.refresh_token_expire_days * 86400, path=_refresh_path(), **common
    )


def clear_auth_cookies(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(ACCESS_COOKIE, path="/", domain=settings.cookie_domain)
    response.delete_cookie(REFRESH_COOKIE, path=_refresh_path(), domain=settings.cookie_domain)


def _access_token(user: User, session: AuthSession) -> str:
    return create_access_token(
        str(user.id),
        extra={"role": user.role.value, "org_id": user.organization_id, "email": user.email, "sid": session.id},
    )


async def sign_in(db: AsyncSession, user: User, request: Request, response: Response) -> Token:
    """Start a new session for `user`, set the cookies, and return the token body for API clients."""
    settings = get_settings()
    raw, digest = generate_invite_token()
    session = AuthSession(
        user_id=user.id,
        refresh_token_hash=digest,
        user_agent=(request.headers.get("user-agent") or "")[:255],
        ip=client_ip(request)[:64],
        expires_at=utcnow() + timedelta(days=settings.refresh_token_expire_days),
    )
    db.add(session)
    await db.flush()
    access = _access_token(user, session)
    set_auth_cookies(response, access, raw)
    return Token(access_token=access, user=UserOut.model_validate(user))


async def refresh(db: AsyncSession, raw_refresh: str, response: Response) -> Token | None:
    """Rotate the refresh token. Returns None (and the caller clears cookies) if it is unknown or expired."""
    session = (
        await db.execute(select(AuthSession).where(AuthSession.refresh_token_hash == hash_token(raw_refresh)))
    ).scalar_one_or_none()
    if not session or session.revoked_at or aware(session.expires_at) < utcnow():
        return None
    user = await db.get(User, session.user_id)
    if not user or not user.is_active or not user.organization.is_active:
        return None
    raw, digest = generate_invite_token()
    session.refresh_token_hash = digest
    session.last_used_at = utcnow()
    await db.flush()
    access = _access_token(user, session)
    set_auth_cookies(response, access, raw)
    return Token(access_token=access, user=UserOut.model_validate(user))


async def session_is_active(db: AsyncSession, session_id: int, user_id: int) -> bool:
    session = await db.get(AuthSession, session_id)
    return bool(
        session and session.user_id == user_id and not session.revoked_at and aware(session.expires_at) > utcnow()
    )


async def revoke_sessions(db: AsyncSession, user_id: int, *, only: int | None = None, keep: int | None = None) -> None:
    query = update(AuthSession).where(AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None))
    if only is not None:
        query = query.where(AuthSession.id == only)
    if keep is not None:
        query = query.where(AuthSession.id != keep)
    await db.execute(query.values(revoked_at=utcnow()))


async def issue_user_token(db: AsyncSession, user_id: int, purpose: str, ttl: timedelta) -> str:
    """Create a single-use token; any earlier unused token for the same purpose stops working."""
    await db.execute(
        update(UserToken)
        .where(UserToken.user_id == user_id, UserToken.purpose == purpose, UserToken.used_at.is_(None))
        .values(used_at=utcnow())
    )
    raw, digest = generate_invite_token()
    db.add(UserToken(user_id=user_id, purpose=purpose, token_hash=digest, expires_at=utcnow() + ttl))
    await db.flush()
    return raw


async def consume_user_token(db: AsyncSession, raw: str, purpose: str) -> User | None:
    token = (
        await db.execute(select(UserToken).where(UserToken.token_hash == hash_token(raw), UserToken.purpose == purpose))
    ).scalar_one_or_none()
    if not token or token.used_at or aware(token.expires_at) < utcnow():
        return None
    token.used_at = utcnow()
    user = await db.get(User, token.user_id)
    return user if user and user.is_active else None
