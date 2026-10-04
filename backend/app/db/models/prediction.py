import uuid
from datetime import datetime

from sqlalchemy import Boolean, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base, UUIDMixin


class CasePrediction(Base, UUIDMixin):
    __tablename__ = "case_predictions"

    case_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cases.id", ondelete="CASCADE"), nullable=False
    )
    source: Mapped[str] = mapped_column(String(50), nullable=False)

    binary_label: Mapped[str | None] = mapped_column(String(50), nullable=True)
    binary_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    venomous_probability: Mapped[float | None] = mapped_column(Float, nullable=True)

    species_available: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    species_label: Mapped[str | None] = mapped_column(String(200), nullable=True)
    genus_label: Mapped[str | None] = mapped_column(String(200), nullable=True)
    species_probabilities: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    genus_probabilities: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    is_ood: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    ood_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    geo_prior_state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    geo_prior_species_probabilities: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    is_calibrated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    model_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    model_architecture: Mapped[str | None] = mapped_column(String(100), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    case = relationship("Case", back_populates="predictions")
