from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AuditLogBase(BaseModel):
    action: str
    target_resource: Optional[str] = None
    target_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    user_agent: Optional[str] = None


class AuditLogCreate(AuditLogBase):
    pass


class AuditLogResponse(AuditLogBase):
    id: UUID
    user_id: Optional[UUID]
    case_id: Optional[UUID]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
