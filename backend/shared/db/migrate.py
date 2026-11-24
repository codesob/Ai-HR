"""One-shot job: `python -m shared.db.migrate`. Applies migrations, then seeds demo data if enabled."""

import asyncio
from pathlib import Path

from alembic import command
from alembic.config import Config

from shared.core.config import get_settings
from shared.db.seed import seed_demo_data


def main() -> None:
    command.upgrade(Config(str(Path(__file__).resolve().parents[2] / "alembic.ini")), "head")
    if get_settings().seed_demo_data:
        asyncio.run(seed_demo_data())


if __name__ == "__main__":
    main()
