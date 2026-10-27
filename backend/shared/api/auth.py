import re
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.api.deps import require_user
from shared.api.rbac import require_roles
from shared.core.config import get_settings
from shared.core.security import (
    create_access_token,
    generate_invite_token,
    hash_password,
    hash_token,
    verify_password,
)
from shared.db.session import get_db
from shared.models.entities import AuditLog, Invitation, Organization, User, UserRole
from shared.schemas.common import (
    AcceptInviteRequest,
    CandidateRegister,
    InvitationOut,
    InviteCreate,
    LoginRequest,
    OrganizationOut,
    OrgSignup,
    Token,
    UserOut,
    UserUpdate,
)
from shared.services.events import publish_notification

router = APIRouter(prefix="/auth", tags=["auth"])
users_router = APIRouter(prefix="/users", tags=["users"])

# Dummy hash so failed logins for unknown emails take as long as wrong passwords.
_TIMING_HASH = hash_password("timing-equaliser")


def _issue_token(user: User) -> Token:
    token = create_access_token(
        str(user.id),
        extra={"role": user.role.value, "org_id": user.organization_id, "email": user.email},
    )
    return Token(access_token=token, user=UserOut.model_validate(user))


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
async def signup_organization(payload: OrgSignup, db: AsyncSession = Depends(get_db)):
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
    return _issue_token(user)


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register_candidate(payload: CandidateRegister, db: AsyncSession = Depends(get_db)):
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
    return _issue_token(user)


@router.post("/login", response_model=Token)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == payload.email.lower()))
    user = result.scalar_one_or_none()
    password_ok = verify_password(payload.password, user.hashed_password if user else _TIMING_HASH)
    if not user or not password_ok:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    if not user.is_active or not user.organization.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")
    return _issue_token(user)


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(require_user)):
    return user


@router.get("/organization", response_model=OrganizationOut)
async def my_organization(user: User = Depends(require_user)):
    return user.organization


@router.post("/accept-invite", response_model=Token)
async def accept_invite(payload: AcceptInviteRequest, db: AsyncSession = Depends(get_db)):
    invite = (
        await db.execute(select(Invitation).where(Invitation.token_hash == hash_token(payload.token)))
    ).scalar_one_or_none()
    now = datetime.now(timezone.utc)
    if not invite or invite.accepted_at or _aware(invite.expires_at) < now:
        raise HTTPException(status_code=400, detail="Invitation is invalid or has expired")
    await _ensure_email_free(db, invite.email)
    user = User(
        organization_id=invite.organization_id,
        email=invite.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name.strip(),
        role=invite.role,
    )
    db.add(user)
    invite.accepted_at = now
    await db.flush()
    await db.refresh(user)
    return _issue_token(user)


def _aware(dt: datetime) -> datetime:
    # SQLite drops tzinfo; values are always stored as UTC.
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


@users_router.get("", response_model=list[UserOut])
async def list_users(
    role: UserRole | None = None,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_roles(UserRole.ADMIN, UserRole.RECRUITER)),
):
    query = select(User).where(User.organization_id == admin.organization_id).order_by(User.created_at)
    if role:
        query = query.where(User.role == role)
    return (await db.execute(query)).scalars().all()


@users_router.get("/audit")
async def audit_log(
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
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
    db: AsyncSession = Depends(get_db),
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
    db: AsyncSession = Depends(get_db),
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
        expires_at=datetime.now(timezone.utc) + timedelta(hours=settings.invite_expire_hours),
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
