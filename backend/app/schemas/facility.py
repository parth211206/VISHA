from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


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

    # Coordinates are optional. Facilities without real coordinates
    # remain in the registry but are not plotted on the map.
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)

    @model_validator(mode="after")
    def validate_coordinate_pair(self):
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError(
                "Latitude and longitude must either both be provided or both be omitted."
            )
        return self


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

    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)

    @model_validator(mode="after")
    def validate_coordinate_pair(self):
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError(
                "Latitude and longitude must both be supplied when setting coordinates."
            )
        return self


class AntivenomFacilityResponse(AntivenomFacilityBase):
    id: UUID
    last_verified: Optional[datetime]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
