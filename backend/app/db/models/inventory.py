from datetime import date
import uuid

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDMixin, TimestampMixin


class AntivenomInventory(Base, UUIDMixin, TimestampMixin):
    """Facility-reported antivenom inventory; not a treatment recommendation."""

    __tablename__ = "antivenom_inventory"

    __table_args__ = (
        CheckConstraint(
            "quantity_units >= 0",
            name="ck_antivenom_inventory_quantity_nonnegative",
        ),
        CheckConstraint(
            "low_stock_threshold >= 0",
            name="ck_antivenom_inventory_threshold_nonnegative",
        ),
        CheckConstraint(
            "verification_status IN "
            "('UNVERIFIED', 'MANUALLY_REPORTED', "
            "'FACILITY_REPORTED_CONFIRMED')",
            name="ck_antivenom_inventory_verification_status",
        ),
        Index("ix_antivenom_inventory_facility_id", "facility_id"),
        Index("ix_antivenom_inventory_product_name", "product_name"),
    )

    facility_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("antivenom_facilities.id", ondelete="CASCADE"),
        nullable=False,
    )

    product_name: Mapped[str] = mapped_column(String(300), nullable=False)
    manufacturer: Mapped[str | None] = mapped_column(String(300), nullable=True)
    formulation: Mapped[str | None] = mapped_column(String(200), nullable=True)
    batch_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    quantity_units: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    unit_label: Mapped[str] = mapped_column(
        String(40), nullable=False, default="vials",
        server_default=text("'vials'")
    )
    low_stock_threshold: Mapped[int] = mapped_column(
        Integer, nullable=False, default=10, server_default=text("10")
    )

    verification_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="UNVERIFIED",
        server_default=text("'UNVERIFIED'")
    )
    verification_source: Mapped[str | None] = mapped_column(
        String(300), nullable=True
    )
    last_verified_at: Mapped[object | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    @property
    def availability_status(self) -> str:
        """Report inventory status without making a clinical recommendation."""
        from app.core.inventory_status import derive_inventory_status

        return derive_inventory_status(
            verification_status=self.verification_status,
            last_verified_at=self.last_verified_at,
            expiry_date=self.expiry_date,
            quantity_units=self.quantity_units,
            low_stock_threshold=self.low_stock_threshold,
        )
