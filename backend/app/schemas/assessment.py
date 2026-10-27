
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TaxonomyReviewInput(BaseModel):
    family: str | None = None
    genus: str | None = None
    species: str | None = None
    source: str | None = None
    notes: str | None = None
    verified: bool = False

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ClinicalAssessmentRequest(BaseModel):
    case_reference: str | None = None
    facility_name: str | None = None

    patient_age_group: str | None = None
    patient_sex: str | None = None
    bite_site: str | None = None
    symptom_onset: str | None = None
    symptom_progression: str | None = None

    symptoms: list[str] = Field(default_factory=list)
    clinical_notes: str | None = None

    state: str | None = None
    district: str | None = None
    locality: str | None = None
    location_type: str | None = None
    habitat: str | None = None
    encounter_time: str | None = None
    snake_description: str | None = None

    twenty_wbct: str = "Not recorded"
    pt_inr: str = "Not recorded"
    aptt: str = "Not recorded"
    platelets: str = "Not recorded"
    fibrinogen: str = "Not recorded"
    other_labs: str | None = None

    clinician_recorded_status: str | None = None
    reference_review_status: str | None = None

    image_prediction: dict[str, Any] | None = None
    taxonomy: TaxonomyReviewInput = Field(
        default_factory=TaxonomyReviewInput
    )

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
