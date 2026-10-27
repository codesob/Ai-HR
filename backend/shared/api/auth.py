import re
from datetime import timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.api.deps import require_user
from shared.api.rbac import require_roles
from shared.core.config import get_settings
from shared.core.security import generate_invite_token, hash_password, hash_token, verify_password
from shared.db.session import get_db
from shared.models.entities import AuditLog, AuthSession, Invitation, Organization, User, UserRole
from shared.schemas.common import (
    AcceptInviteRequest,
    CandidateRegister,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    InvitationOut,
    InviteCreate,
    LoginRequest,
    OrganizationOut,
    OrgSignup,
    ProfileUpdate,
    ResetPasswordRequest,
    SessionOut,
    Token,
    TokenRequest,
    UserOut,
    UserUpdate,
)
from shared.services.email import send_account_email
from shared.services.events import publish_notification
from shared.services.sessions import (
    PURPOSE_RESET,
    PURPOSE_VERIFY,
    REFRESH_COOKIE,
    aware,
    clear_auth_cookies,
    consume_user_token,
    issue_user_token,
    refresh,
    revoke_sessions,
    sign_in,
    utcnow,
)

router = APIRouter(prefix="/auth", tags=["auth"])
users_router = APIRouter(prefix="/users", tags=["users"])
account_router = APIRouter(prefix="/account", tags=["account"])

# Dummy hash so failed logins for unknown emails take as long as wrong passwords.
_TIMING_HASH = hash_password("timing-equaliser")


# Seeded demo accounts are shared by every visitor, so nobody may lock the others out of them.
DEMO_EMAIL_SUFFIX = "@aihr.demo"


def _forbid_on_demo(user: User) -> None:
    if user.email.endswith(DEMO_EMAIL_SUFFIX):
        raise HTTPException(status_code=403, detail="This is a shared demo account, so it can't be changed.")


async def _send_verification(db: AsyncSession, user: User, background: BackgroundTasks) -> None:
    settings = get_settings()
    raw = await issue_user_token(db, user.id, PURPOSE_VERIFY, timedelta(hours=settings.email_verify_expire_hours))
    link = f"{settings.frontend_url.rstrip('/')}/verify-email?token={raw}"
    background.add_task(
        send_account_email, user.email, "Confirm your email for AI-HR",
        f"Hi {user.full_name},\n\nConfirm this is your email address by opening the link below.", link,
    )


async def _ensure_email_free(db: AsyncSession, email: str) -> None:
    existing = await db.execute(select(User.id).where(User.email == email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")


async def _unique_slug(db: AsyncSession, name: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:48] or "org"
    slug, n = base, 1
    while (await db.execute(select(Organization.id).where(Organization.slug == slug))).scalar_one_or_none():
        n += 1
        slug = f"{base}-{n}"
    return slug


@router.post("/signup", response_model=Token, status_code=status.HTTP_201_CREATED)
async def signup_organization(
    payload: OrgSignup,
    request: Request,
    response: Response,
    background: BackgroundTasks,
    db: AsyncSession = Depends(get_db, scope="function"),
):
    """Create a new company workspace; the signing-up user becomes its admin."""
    email = payload.email.lower()
    await _ensure_email_free(db, email)
    org = Organization(name=payload.company_name.strip(), slug=await _unique_slug(db, payload.company_name))
    db.add(org)
    await db.flush()
    user = User(
        organization_id=org.id,
        email=email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name.strip(),
        role=UserRole.ADMIN,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    await _send_verification(db, user, background)
    return await sign_in(db, user, request, response)


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register_candidate(
    payload: CandidateRegister,
    request: Request,
    response: Response,
    background: BackgroundTasks,
    db: AsyncSession = Depends(get_db, scope="function"),
):
    """Public candidate sign-up from an organization's careers page. Always creates a candidate."""
    org = (
        await db.execute(select(Organization).where(Organization.slug == payload.org_slug, Organization.is_active))
    ).scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    email = payload.email.lower()
    await _ensure_email_free(db, email)
    user = User(
        organization_id=org.id,
        email=email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name.strip(),
        role=UserRole.CANDIDATE,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    await _send_verification(db, user, background)
    return await sign_in(db, user, request, response)


@router.post("/login", response_model=Token)
async def login(
    payload: LoginRequest, request: Request, response: Response, db: AsyncSession = Depends(get_db, scope="function")
):
    result = await db.execute(select(User).where(User.email == payload.email.lower()))
    user = result.scalar_one_or_none()
    password_ok = verify_password(payload.password, user.hashed_password if user else _TIMING_HASH)
    if not user or not password_ok:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    if not user.is_active or not user.organization.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")
    return await sign_in(db, user, request, response)


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(require_user)):
    return user


@router.get("/organization", response_model=OrganizationOut)
async def my_organization(user: User = Depends(require_user)):
    return user.organization


@router.post("/accept-invite", response_model=Token)
async def accept_invite(
    payload: AcceptInviteRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db, scope="function"),
):
    invite = (
        await db.execute(select(Invitation).where(Invitation.token_hash == hash_token(payload.token)))
    ).scalar_one_or_none()
    now = utcnow()
    if not invite or invite.accepted_at or aware(invite.expires_at) < now:
        raise HTTPException(status_code=400, detail="Invitation is invalid or has expired")
    await _ensure_email_free(db, invite.email)
    user = User(
        organization_id=invite.organization_id,
        email=invite.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name.strip(),
        role=invite.role,
        # The invite link was emailed to this address, which proves it.
        email_verified_at=now,
    )
    db.add(user)
    invite.accepted_at = now
    await db.flush()
    await db.refresh(user)
    return await sign_in(db, user, request, response)


@router.post("/refresh", response_model=Token)
async def refresh_session(request: Request, response: Response, db: AsyncSession = Depends(get_db, scope="function")):
    """Swap the refresh cookie for a new access cookie (and a new refresh cookie)."""
    raw = request.cookies.get(REFRESH_COOKIE)
    token = await refresh(db, raw, response) if raw else None
    if not token:
        clear_auth_cookies(response)
        # Raising would drop the cookie-clearing headers set on `response`.
        return Response(
            content='{"detail":"Session expired. Sign in again."}', status_code=401, media_type="application/json",
            headers={k: v for k, v in response.headers.items() if k.lower() == "set-cookie"},
        )
    return token


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(request: Request, db: AsyncSession = Depends(get_db, scope="function")):
    raw = request.cookies.get(REFRESH_COOKIE)
    if raw:
        session = (
            await db.execute(select(AuthSession).where(AuthSession.refresh_token_hash == hash_token(raw)))
        ).scalar_one_or_none()
        if session:
            await revoke_sessions(db, session.user_id, only=session.id)
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    clear_auth_cookies(response)
    return response


@router.post("/password/forgot", status_code=status.HTTP_202_ACCEPTED)
async def forgot_password(
    payload: ForgotPasswordRequest, background: BackgroundTasks, db: AsyncSession = Depends(get_db, scope="function")
):
    """Always answers the same way, so it can't be used to find out which emails have accounts."""
    settings = get_settings()
    user = (await db.execute(select(User).where(User.email == payload.email.lower()))).scalar_one_or_none()
    if user and user.is_active and not user.email.endswith(DEMO_EMAIL_SUFFIX):
        raw = await issue_user_token(
            db, user.id, PURPOSE_RESET, timedelta(minutes=settings.password_reset_expire_minutes)
        )
        link = f"{settings.frontend_url.rstrip('/')}/reset-password?token={raw}"
        background.add_task(
            send_account_email, user.email, "Reset your AI-HR password",
            f"Hi {user.full_name},\n\nSomeone asked to reset your password. If it was you, open the link below "
            f"within {settings.password_reset_expire_minutes} minutes. If not, you can ignore this email.", link,
        )
    return {"detail": "If that email has an account, a reset link is on its way."}


@router.post("/password/reset", response_model=Token)
async def reset_password(
    payload: ResetPasswordRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db, scope="function"),
):
    user = await consume_user_token(db, payload.token, PURPOSE_RESET)
    if not user:
        raise HTTPException(status_code=400, detail="This reset link is invalid or has expired. Ask for a new one.")
    user.hashed_password = hash_password(payload.password)
    # Opening the emailed link proves the address.
    user.email_verified_at = user.email_verified_at or utcnow()
    await revoke_sessions(db, user.id)
    return await sign_in(db, user, request, response)


@router.post("/email/verify", response_model=UserOut)
async def verify_email(payload: TokenRequest, db: AsyncSession = Depends(get_db, scope="function")):
    user = await consume_user_token(db, payload.token, PURPOSE_VERIFY)
    if not user:
        raise HTTPException(status_code=400, detail="This confirmation link is invalid or has expired.")
    user.email_verified_at = user.email_verified_at or utcnow()
    await db.flush()
    return user


@router.post("/email/resend", status_code=status.HTTP_202_ACCEPTED)
async def resend_verification(
    background: BackgroundTasks,
    db: AsyncSession = Depends(get_db, scope="function"),
    user: User = Depends(require_user),
):
    if not user.email_verified_at:
        await _send_verification(db, user, background)
    return {"detail": "Confirmation email sent."}


@account_router.patch("/profile", response_model=UserOut)
async def update_profile(
    payload: ProfileUpdate, db: AsyncSession = Depends(get_db, scope="function"), user: User = Depends(require_user)
):
    _forbid_on_demo(user)
    user.full_name = payload.full_name.strip()
    await db.flush()
    return user


@account_router.post("/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    db: AsyncSession = Depends(get_db, scope="function"),
    user: User = Depends(require_user),
):
    _forbid_on_demo(user)
    if not verify_password(payload.current_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Your current password is wrong.")
    user.hashed_password = hash_password(payload.new_password)
    # Everyone else holding the old password is signed out; this device stays in.
    await revoke_sessions(db, user.id, keep=getattr(request.state, "session_id", None))


@account_router.get("/sessions", response_model=list[SessionOut])
async def list_sessions(
    request: Request, db: AsyncSession = Depends(get_db, scope="function"), user: User = Depends(require_user)
):
    now = utcnow()
    rows = (
        await db.execute(
            select(AuthSession)
            .where(AuthSession.user_id == user.id, AuthSession.revoked_at.is_(None))
            .order_by(AuthSession.last_used_at.desc())
        )
    ).scalars()
    current = getattr(request.state, "session_id", None)
    return [
        SessionOut.model_validate(s).model_copy(update={"current": s.id == current})
        for s in rows
        if aware(s.expires_at) > now
    ]


@account_router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def end_session(
    session_id: int, db: AsyncSession = Depends(get_db, scope="function"), user: User = Depends(require_user)
):
    _forbid_on_demo(user)
    await revoke_sessions(db, user.id, only=session_id)


@account_router.post("/sessions/revoke-others", status_code=status.HTTP_204_NO_CONTENT)
async def end_other_sessions(
    request: Request, db: AsyncSession = Depends(get_db, scope="function"), user: User = Depends(require_user)
):
    _forbid_on_demo(user)
    await revoke_sessions(db, user.id, keep=getattr(request.state, "session_id", None))


@users_router.get("", response_model=list[UserOut])
async def list_users(
    role: UserRole | None = None,
    db: AsyncSession = Depends(get_db, scope="function"),
    admin: User = Depends(require_roles(UserRole.ADMIN, UserRole.RECRUITER)),
):
    query = select(User).where(User.organization_id == admin.organization_id).order_by(User.created_at)
    if role:
        query = query.where(User.role == role)
    return (await db.execute(query)).scalars().all()


@users_router.get("/audit")
async def audit_log(
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db, scope="function"),
    admin: User = Depends(require_roles(UserRole.ADMIN)),
):
    rows = (await db.execute(
        select(AuditLog)
        .where(AuditLog.organization_id == admin.organization_id)
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .limit(limit)
    )).scalars()
    return [
        {
            "id": r.id, "actor": r.actor, "action": r.action, "resource": r.resource,
            "status_code": (r.metadata_json or {}).get("status_code"), "created_at": r.created_at,
        }
        for r in rows
    ]


@users_router.patch("/{user_id}", response_model=UserOut)
async def update_user(
    user_id: int,
    payload: UserUpdate,
    db: AsyncSession = Depends(get_db, scope="function"),
    admin: User = Depends(require_roles(UserRole.ADMIN)),
):
    target = (
        await db.execute(select(User).where(User.id == user_id, User.organization_id == admin.organization_id))
    ).scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target.id == admin.id and (payload.role not in (None, UserRole.ADMIN) or payload.is_active is False):
        raise HTTPException(status_code=400, detail="You cannot demote or deactivate yourself")
    if payload.role is not None:
        target.role = payload.role
    if payload.is_active is not None:
        target.is_active = payload.is_active
    if payload.full_name is not None:
        target.full_name = payload.full_name
    await db.flush()
    return target


@users_router.post("/invite", response_model=InvitationOut, status_code=status.HTTP_201_CREATED)
async def invite_user(
    payload: InviteCreate,
    db: AsyncSession = Depends(get_db, scope="function"),
    admin: User = Depends(require_roles(UserRole.ADMIN)),
):
    settings = get_settings()
    email = payload.email.lower()
    await _ensure_email_free(db, email)
    raw, token_hash = generate_invite_token()
    invite = Invitation(
        organization_id=admin.organization_id,
        email=email,
        role=payload.role,
        token_hash=token_hash,
        invited_by_id=admin.id,
        expires_at=utcnow() + timedelta(hours=settings.invite_expire_hours),
    )
    db.add(invite)
    await db.flush()
    invite_url = f"{settings.frontend_url.rstrip('/')}/accept-invite?token={raw}"
    await publish_notification(
        db,
        organization_id=admin.organization_id,
        recipient=email,
        channel="email",
        subject=f"You're invited to join {admin.organization.name} on AI-HR",
        body=f"{admin.full_name} invited you to join as {payload.role.value}. Accept: {invite_url}",
        event_type="user.invited",
        payload={"invite_id": invite.id},
        send_now=True,
    )
    out = InvitationOut.model_validate(invite)
    # The raw link is returned once so admins can share it if email delivery isn't configured.
    out.invite_url = invite_url
    return out
