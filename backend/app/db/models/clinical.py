from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from app.db.base import Base, UUIDMixin
import uuid
from datetime import datetime
from sqlalchemy.sql import func

class ClinicalEvidence(Base, UUIDMixin):
    __tablename__ = "clinical_evidence"

    case_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), nullable=False)
    
    syndrome: Mapped[str | None] = mapped_column(String(200), nullable=True)
    clinical_indicators: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    implicated_genera: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    rule_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    
    case = relationship("Case", back_populates="clinical_evidence")
