from datetime import datetime
import uuid
from sqlalchemy.orm import declarative_base, Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy import DateTime
from sqlalchemy.dialects.postgresql import UUID

Base = declarative_base()

class UUIDMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
