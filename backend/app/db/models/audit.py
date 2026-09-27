from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, INET
from app.db.base import Base, UUIDMixin
import uuid
from datetime import datetime
from sqlalchemy.sql import func

class AuditLog(Base, UUIDMixin):
    __tablename__ = "audit_log"

    action: Mapped[str] = mapped_column(String(50), nullable=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    case_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("cases.id"), nullable=True)
    
    target_resource: Mapped[str | None] = mapped_column(String(200), nullable=True)
    target_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    
    details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    
    ip_address = mapped_column(INET, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    
    user = relationship("User")
    case = relationship("Case")
