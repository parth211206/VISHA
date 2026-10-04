from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.schemas.antivenom import VerificationStatus


class ClinicalGuideline(BaseModel):
    title: Optional[str] = None
    organization: Optional[str] = None
    version: Optional[str] = None
    date: Optional[str] = None
    topic: Optional[str] = None
    citation: Optional[str] = None
    geographic_scope: Optional[str] = None
    evidence_status: Optional[str] = None
    notes: Optional[str] = None
    verification_status: VerificationStatus

    model_config = ConfigDict(from_attributes=True)
