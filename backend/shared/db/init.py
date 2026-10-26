import logging

from sqlalchemy import text

from shared.core.config import get_settings
from shared.db.seed import seed_demo_data
from shared.db.session import Base, engine

logger = logging.getLogger(__name__)


async def init_database() -> None:
    """Dev/test bootstrap. In production the schema is owned by `alembic upgrade head`."""
    settings = get_settings()
    if settings.auto_create_schema:
        import shared.models.entities  # noqa: F401  (register all tables on Base.metadata)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    if settings.seed_demo_data:
        await seed_demo_data()


async def check_database() -> bool:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        logger.exception("Database readiness check failed")
        return False
