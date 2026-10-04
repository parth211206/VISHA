from typing import Any, Dict
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.audit import AuditLog


class AuditService:
    async def log_action(
        self,
        user_id: UUID | None,
        action: str,
        payload: Dict[str, Any],
        db: AsyncSession,
        case_id: UUID | None = None,
        target_resource: str | None = None,
        target_id: str | None = None,
    ) -> None:
        """Persist an audit entry in a single transaction.
        The caller must ensure that any related DB changes are part of the same transaction
        (e.g., by using the same AsyncSession)."""
        entry = AuditLog(
            user_id=user_id,
            case_id=case_id,
            action=action,
            target_resource=target_resource,
            target_id=target_id,
            details=payload,
        )
        db.add(entry)
        await db.flush()
