from collections.abc import Iterable

from fastapi import Depends, HTTPException, status

from shared.api.deps import require_user
from shared.models.entities import User, UserRole


def require_roles(*roles: UserRole | str):
    allowed = {_role_value(role) for role in roles}

    async def dependency(user: User = Depends(require_user)) -> User:
        if _role_value(user.role) not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return user

    return dependency


def _role_value(role: UserRole | str) -> str:
    return role.value if isinstance(role, UserRole) else role


def has_role(user: User, roles: Iterable[UserRole | str]) -> bool:
    return _role_value(user.role) in {_role_value(role) for role in roles}
