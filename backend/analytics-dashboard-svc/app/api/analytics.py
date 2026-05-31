from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from shared.api.rbac import require_roles
from shared.db.session import get_db
from shared.models.entities import User, UserRole
from shared.schemas.common import AnalyticsSummary
from shared.services.analytics import get_hiring_analytics

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/hiring", response_model=AnalyticsSummary)
async def hiring_analytics(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.RECRUITER)),
):
    return await get_hiring_analytics(db)
