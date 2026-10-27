from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class VerificationStatus(str, Enum):
    UNVERIFIED = "UNVERIFIED"
    PLACEHOLDER = "PLACEHOLDER"
    SOURCE_REQUIRED = "SOURCE_REQUIRED"
    SOURCE_VERIFIED = "SOURCE_VERIFIED"
    CLINICIAN_REVIEWED = "CLINICIAN_REVIEWED"


class AntivenomReference(BaseModel):
    product_name: Optional[str] = None
    manufacturer: Optional[str] = None
    target_species: List[str] = []
    geographic_scope: Optional[str] = None
    formulation: Optional[str] = None
    source_citation: Optional[str] = None
    source_version: Optional[str] = None
    source_date: Optional[str] = None
    evidence_status: Optional[str] = None
    notes: Optional[str] = None
    verification_status: VerificationStatus

    model_config = ConfigDict(from_attributes=True)