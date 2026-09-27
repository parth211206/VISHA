from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Boolean, text
from app.db.base import Base, UUIDMixin, TimestampMixin
import uuid

class User(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="clinician")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    cases_created = relationship("Case", back_populates="creator", foreign_keys="Case.created_by")
    cases_assigned = relationship("Case", back_populates="assignee", foreign_keys="Case.assigned_to")
