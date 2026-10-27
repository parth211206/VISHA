from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, HttpUrl


class ClinicalReference(BaseModel):
    reference_id: str = Field(min_length=1, description="Unique reference identifier")
    title: str = Field(min_length=1, description="Title of the guideline or source")
    issuing_organization: str = Field(
        min_length=1, description="Organization that issued the guideline"
    )
    document_date_or_version: Optional[str] = Field(
        None,
        description="Published date or version string (may be null if not provided)",
    )
    official_url: HttpUrl = Field(
        ..., description="Official URL for the source (must be HTTPS with hostname)"
    )
    source_status: str = Field(min_length=1, description="Status of the source")
    clinical_review_status: str = Field(
        min_length=1, description="Review status of the clinical content"
    )
    last_reviewed: Optional[str] = Field(
        None,
        description="Date when the content was last reviewed (may be null until reviewed)",
    )
    notes: str = Field(min_length=1, description="Free-text notes about the reference")

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    @field_validator("official_url")
    def url_must_be_https(cls, v: HttpUrl) -> HttpUrl:
        """Reject any URL whose scheme is not HTTPS."""
        # HttpUrl already validates structure; ensure scheme is https
        if v.scheme is not None and v.scheme.lower() != "https":
            raise ValueError("official_url must be an HTTPS URL")
        return v


class ClinicalReferenceList(BaseModel):
    entries: List[ClinicalReference]
    total: int = Field(..., ge=0, description="Total number of catalogue entries")

    model_config = ConfigDict(from_attributes=True)