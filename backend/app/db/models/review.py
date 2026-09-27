from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Boolean, ForeignKey, Text
from sqlalchemy.dialects.postgresql import TIMESTAMP
from app.db.base import Base, UUIDMixin
import uuid
from datetime import datetime
from sqlalchemy.sql import func

class ClinicianReview(Base, UUIDMixin):
    __tablename__ = "clinician_reviews"

    case_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), nullable=False)
    reviewed_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    
    accepted_ai_prediction: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    clinician_diagnosis: Mapped[str | None] = mapped_column(String(500), nullable=True)
    final_species: Mapped[str | None] = mapped_column(String(200), nullable=True)
    final_genus: Mapped[str | None] = mapped_column(String(200), nullable=True)
    confidence_level: Mapped[str | None] = mapped_column(String(50), nullable=True)
    
    clinical_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    antivenom_reference_used: Mapped[str | None] = mapped_column(String(200), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    
    case = relationship("Case", back_populates="clinician_reviews")
    reviewer = relationship("User", foreign_keys=[reviewed_by])
