import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiofiles

from shared.core.config import get_settings
from shared.services.pii import mask_pii


async def write_audit_event(
    *,
    actor: str | None,
    action: str,
    resource: str,
    status_code: int,
    metadata: dict[str, Any] | None = None,
) -> None:
    settings = get_settings()
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "actor": actor or "anonymous",
        "action": action,
        "resource": resource,
        "status_code": status_code,
        "metadata": mask_pii(metadata or {}),
    }
    path = Path(settings.audit_log_path)
    path.parent.mkdir(parents=True, exist_ok=True) if path.parent != Path(".") else None
    async with aiofiles.open(path, "a", encoding="utf-8") as handle:
        await handle.write(json.dumps(event, separators=(",", ":")) + "\n")
