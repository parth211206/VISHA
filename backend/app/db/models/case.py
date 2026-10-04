import uuid
from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import Boolean, ForeignKey, Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin


class Case(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "cases"

    case_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="open", nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    patient_age_years: Mapped[int | None] = mapped_column(Integer, nullable=True)
    patient_sex: Mapped[str | None] = mapped_column(String(20), nullable=True)

    bite_date: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    bite_time_approx: Mapped[bool] = mapped_column(Boolean, default=False)
    bite_site: Mapped[str | None] = mapped_column(String(100), nullable=True)

    incident_state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    incident_district: Mapped[str | None] = mapped_column(String(100), nullable=True)
    incident_location_description: Mapped[str | None] = mapped_column(String, nullable=True)
    incident_coordinates = mapped_column(Geometry("POINT", srid=4326), nullable=True)

    snake_observed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    snake_description: Mapped[str | None] = mapped_column(String, nullable=True)
    snake_image_path: Mapped[str | None] = mapped_column(String(500), nullable=True)

    symptoms: Mapped[dict] = mapped_column(
        JSONB, default=dict, nullable=False, server_default=text("'{}'::jsonb")
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)

    creator = relationship("User", foreign_keys=[created_by])
    assignee = relationship("User", foreign_keys=[assigned_to])

    predictions = relationship(
        "CasePrediction", back_populates="case", cascade="all, delete-orphan"
    )
    clinical_evidence = relationship(
        "ClinicalEvidence", back_populates="case", cascade="all, delete-orphan"
    )
    clinician_reviews = relationship(
        "ClinicianReview", back_populates="case", cascade="all, delete-orphan"
    )
