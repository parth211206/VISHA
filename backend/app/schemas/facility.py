from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AntivenomFacilityBase(BaseModel):
    name: str
    facility_type: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None
    address: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    has_polyvalent_asv: Optional[bool] = None
    has_icu: Optional[bool] = None
    notes: Optional[str] = None


class AntivenomFacilityCreate(AntivenomFacilityBase):
    pass


class AntivenomFacilityUpdate(BaseModel):
    name: Optional[str] = None
    facility_type: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None
    address: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    has_polyvalent_asv: Optional[bool] = None
    has_icu: Optional[bool] = None
    notes: Optional[str] = None
    last_verified: Optional[datetime] = None


class AntivenomFacilityResponse(AntivenomFacilityBase):
    id: UUID
    last_verified: Optional[datetime]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
