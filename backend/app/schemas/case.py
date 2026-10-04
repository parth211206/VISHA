from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CaseBase(BaseModel):
    patient_age_years: Optional[int] = None
    patient_sex: Optional[str] = None
    bite_date: Optional[datetime] = None
    bite_time_approx: bool = False
    bite_site: Optional[str] = None
    incident_state: Optional[str] = None
    incident_district: Optional[str] = None
    incident_location_description: Optional[str] = None
    snake_observed: Optional[bool] = None
    snake_description: Optional[str] = None
    symptoms: Dict[str, Any] = Field(default_factory=dict)


class CaseCreate(CaseBase):
    pass


class CaseUpdate(CaseBase):
    status: Optional[str] = None
    assigned_to: Optional[UUID] = None


class CaseResponse(CaseBase):
    id: UUID
    case_number: str
    status: str
    created_by: UUID
    assigned_to: Optional[UUID]
    snake_image_path: Optional[str]
    confirmed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
