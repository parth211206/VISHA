from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator


VerificationStatus = Literal[
    "UNVERIFIED",
    "MANUALLY_REPORTED",
    "FACILITY_REPORTED_CONFIRMED",
]


class InventoryItemCreate(BaseModel):
    product_name: str = Field(min_length=1, max_length=300)
    manufacturer: str | None = Field(default=None, max_length=300)
    formulation: str | None = Field(default=None, max_length=200)
    batch_number: str | None = Field(default=None, max_length=100)
    expiry_date: date | None = None

    quantity_units: int = Field(ge=0)
    unit_label: str = Field(default="vials", min_length=1, max_length=40)
    low_stock_threshold: int = Field(default=10, ge=0)

    verification_status: VerificationStatus = "UNVERIFIED"
    verification_source: str | None = Field(default=None, max_length=300)
    notes: str | None = None

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @model_validator(mode="after")
    def validate_facility_confirmation(self):
        if (
            self.verification_status == "FACILITY_REPORTED_CONFIRMED"
            and not self.verification_source
        ):
            raise ValueError(
                "A source is required when the facility reports confirmation."
            )
        return self


class InventoryItemUpdate(BaseModel):
    product_name: str | None = Field(default=None, min_length=1, max_length=300)
    manufacturer: str | None = Field(default=None, max_length=300)
    formulation: str | None = Field(default=None, max_length=200)
    batch_number: str | None = Field(default=None, max_length=100)
    expiry_date: date | None = None

    quantity_units: int | None = Field(default=None, ge=0)
    unit_label: str | None = Field(default=None, min_length=1, max_length=40)
    low_stock_threshold: int | None = Field(default=None, ge=0)

    verification_status: VerificationStatus | None = None
    verification_source: str | None = Field(default=None, max_length=300)
    notes: str | None = None

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @model_validator(mode="after")
    def validate_update(self):
        required_fields = (
            "product_name",
            "quantity_units",
            "unit_label",
            "low_stock_threshold",
        )

        for name in required_fields:
            if name in self.model_fields_set and getattr(self, name) is None:
                raise ValueError(f"{name} cannot be null.")

        if (
            self.verification_status == "FACILITY_REPORTED_CONFIRMED"
            and not self.verification_source
        ):
            raise ValueError(
                "A source is required when the facility reports confirmation."
            )

        return self


class InventoryItemResponse(BaseModel):
    id: UUID
    facility_id: UUID
    product_name: str
    manufacturer: str | None
    formulation: str | None
    batch_number: str | None
    expiry_date: date | None

    quantity_units: int
    unit_label: str
    low_stock_threshold: int

    verification_status: VerificationStatus
    verification_source: str | None
    last_verified_at: datetime | None
    notes: str | None

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def availability_status(self) -> str:
        from app.core.inventory_status import derive_inventory_status

        return derive_inventory_status(
            verification_status=self.verification_status,
            last_verified_at=self.last_verified_at,
            expiry_date=self.expiry_date,
            quantity_units=self.quantity_units,
            low_stock_threshold=self.low_stock_threshold,
        )
