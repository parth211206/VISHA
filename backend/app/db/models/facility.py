from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import Boolean, String, Text
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base, UUIDMixin


class AntivenomFacility(Base, UUIDMixin):
    __tablename__ = "antivenom_facilities"

    name: Mapped[str] = mapped_column(String(300), nullable=False)
    facility_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    district: Mapped[str | None] = mapped_column(String(100), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)

    coordinates = mapped_column(Geometry("POINT", srid=4326), nullable=True)

    contact_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(200), nullable=True)

    has_polyvalent_asv: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    has_icu: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_verified: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
