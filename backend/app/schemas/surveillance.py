from pydantic import BaseModel, ConfigDict
from datetime import datetime
from uuid import UUID
from typing import Optional

class SurveillanceRecordBase(BaseModel):
    case_id: Optional[UUID] = None
    state: Optional[str] = None
    district: Optional[str] = None
    year: Optional[int] = None
    month: Optional[int] = None
    final_species: Optional[str] = None
    final_genus: Optional[str] = None
    venom_category: Optional[str] = None
    clinical_syndrome: Optional[str] = None
    severity: Optional[str] = None
    outcome: Optional[str] = None
    antivenom_given: Optional[bool] = None

class SurveillanceRecordCreate(SurveillanceRecordBase):
    pass

class SurveillanceRecordResponse(SurveillanceRecordBase):
    id: UUID
    is_verified: bool
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
