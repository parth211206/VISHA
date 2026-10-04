from datetime import datetime
from typing import Dict, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PredictionBase(BaseModel):
    source: str
    binary_label: Optional[str] = None
    binary_confidence: Optional[float] = None
    venomous_probability: Optional[float] = None
    species_available: bool = False
    species_label: Optional[str] = None
    genus_label: Optional[str] = None
    species_probabilities: Optional[Dict[str, float]] = None
    genus_probabilities: Optional[Dict[str, float]] = None
    is_ood: Optional[bool] = None
    ood_score: Optional[float] = None
    geo_prior_state: Optional[str] = None
    geo_prior_species_probabilities: Optional[Dict[str, float]] = None
    is_calibrated: bool = False
    model_version: Optional[str] = None
    model_architecture: Optional[str] = None


class PredictionCreate(PredictionBase):
    pass


class PredictionResponse(PredictionBase):
    id: UUID
    case_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
