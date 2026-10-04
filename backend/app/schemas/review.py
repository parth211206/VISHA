from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ClinicianReviewBase(BaseModel):
    accepted_ai_prediction: Optional[bool] = None
    clinician_diagnosis: Optional[str] = None
    final_species: Optional[str] = None
    final_genus: Optional[str] = None
    confidence_level: Optional[str] = None
    clinical_notes: Optional[str] = None
    reasoning: Optional[str] = None
    antivenom_reference_used: Optional[str] = None


class ClinicianReviewCreate(ClinicianReviewBase):
    pass


class ClinicianReviewResponse(ClinicianReviewBase):
    id: UUID
    case_id: UUID
    reviewed_by: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
