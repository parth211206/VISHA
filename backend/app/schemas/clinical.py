from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ClinicalEvidenceBase(BaseModel):
    syndrome: Optional[str] = None
    clinical_indicators: Optional[Dict[str, Any]] = None
    implicated_genera: Optional[Dict[str, Any]] = None
    rule_version: Optional[str] = None


class ClinicalEvidenceCreate(ClinicalEvidenceBase):
    pass


class ClinicalEvidenceResponse(ClinicalEvidenceBase):
    id: UUID
    case_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
