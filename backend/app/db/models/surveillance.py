from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Boolean, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import TIMESTAMP
from geoalchemy2 import Geometry
from app.db.base import Base, UUIDMixin
import uuid
from datetime import datetime
from sqlalchemy.sql import func

class SurveillanceRecord(Base, UUIDMixin):
    __tablename__ = "surveillance_records"

    case_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("cases.id"), nullable=True)
    
    state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    district: Mapped[str | None] = mapped_column(String(100), nullable=True)
    approximate_coordinates = mapped_column(Geometry('POINT', srid=4326), nullable=True)
    
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    month: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    final_species: Mapped[str | None] = mapped_column(String(200), nullable=True)
    final_genus: Mapped[str | None] = mapped_column(String(200), nullable=True)
    venom_category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    clinical_syndrome: Mapped[str | None] = mapped_column(String(200), nullable=True)
    severity: Mapped[str | None] = mapped_column(String(50), nullable=True)
    
    outcome: Mapped[str | None] = mapped_column(String(100), nullable=True)
    antivenom_given: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    
    case = relationship("Case")
