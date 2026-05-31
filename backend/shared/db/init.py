from shared.db.seed import seed_database


async def init_database() -> None:
    await seed_database()
