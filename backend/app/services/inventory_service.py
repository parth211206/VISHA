from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DataNotFoundError
from app.db.models.facility import AntivenomFacility
from app.db.models.inventory import AntivenomInventory
from app.schemas.inventory import InventoryItemCreate, InventoryItemUpdate
from app.services.audit_service import AuditService


def _audit_user_id(current_user: dict) -> UUID | None:
    """The prototype's development identity may not contain a database UUID."""
    raw = current_user.get("id")
    if raw is None:
        return None
    try:
        return raw if isinstance(raw, UUID) else UUID(str(raw))
    except (TypeError, ValueError, AttributeError):
        return None


class AntivenomInventoryService:
    def __init__(self, audit_service: AuditService):
        self.audit_service = audit_service

    async def _ensure_facility(
        self, db: AsyncSession, facility_id: UUID
    ) -> AntivenomFacility:
        facility = await db.get(AntivenomFacility, facility_id)
        if facility is None:
            raise DataNotFoundError("Facility not found")
        return facility

    async def list_items(
        self, db: AsyncSession, facility_id: UUID
    ) -> list[AntivenomInventory]:
        await self._ensure_facility(db, facility_id)

        stmt = (
            select(AntivenomInventory)
            .where(AntivenomInventory.facility_id == facility_id)
            .order_by(
                AntivenomInventory.product_name.asc(),
                AntivenomInventory.expiry_date.asc().nullslast(),
            )
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def _get_item(
        self,
        db: AsyncSession,
        facility_id: UUID,
        inventory_id: UUID,
    ) -> AntivenomInventory:
        await self._ensure_facility(db, facility_id)

        stmt = select(AntivenomInventory).where(
            AntivenomInventory.id == inventory_id,
            AntivenomInventory.facility_id == facility_id,
        )
        result = await db.execute(stmt)
        item = result.scalar_one_or_none()

        if item is None:
            raise DataNotFoundError("Inventory record not found")

        return item

    async def create_item(
        self,
        db: AsyncSession,
        facility_id: UUID,
        item_in: InventoryItemCreate,
        current_user: dict,
    ) -> AntivenomInventory:
        await self._ensure_facility(db, facility_id)

        data = item_in.model_dump()
        confirmed = (
            data["verification_status"] == "FACILITY_REPORTED_CONFIRMED"
        )
        data["last_verified_at"] = (
            datetime.now(timezone.utc) if confirmed else None
        )

        item = AntivenomInventory(facility_id=facility_id, **data)
        db.add(item)

        try:
            await db.flush()

            await self.audit_service.log_action(
                user_id=_audit_user_id(current_user),
                action="CREATE_INVENTORY_ITEM",
                payload={
                    "facility_id": str(facility_id),
                    "product_name": item.product_name,
                    "quantity_units": item.quantity_units,
                    "verification_status": item.verification_status,
                },
                db=db,
                target_resource="antivenom_inventory",
                target_id=str(item.id),
            )

            await db.commit()
            await db.refresh(item)
            return item
        except Exception:
            await db.rollback()
            raise

    async def update_item(
        self,
        db: AsyncSession,
        facility_id: UUID,
        inventory_id: UUID,
        item_in: InventoryItemUpdate,
        current_user: dict,
    ) -> AntivenomInventory:
        item = await self._get_item(db, facility_id, inventory_id)
        data = item_in.model_dump(exclude_unset=True)

        if not data:
            return item

        stock_fields = {
            "product_name",
            "manufacturer",
            "formulation",
            "batch_number",
            "expiry_date",
            "quantity_units",
            "unit_label",
            "low_stock_threshold",
        }

        # Stock changes invalidate an earlier confirmation unless this request
        # explicitly supplies a new facility-reported confirmation and source.
        if stock_fields.intersection(data):
            if data.get("verification_status") != "FACILITY_REPORTED_CONFIRMED":
                data["verification_status"] = "MANUALLY_REPORTED"
                data["last_verified_at"] = None

        if "verification_status" in data:
            if data["verification_status"] == "FACILITY_REPORTED_CONFIRMED":
                data["last_verified_at"] = datetime.now(timezone.utc)
            else:
                data["last_verified_at"] = None

        try:
            for field, value in data.items():
                setattr(item, field, value)

            await self.audit_service.log_action(
                user_id=_audit_user_id(current_user),
                action="UPDATE_INVENTORY_ITEM",
                payload={
                    "facility_id": str(facility_id),
                    "inventory_id": str(inventory_id),
                    "fields_updated": list(data.keys()),
                },
                db=db,
                target_resource="antivenom_inventory",
                target_id=str(item.id),
            )

            await db.commit()
            await db.refresh(item)
            return item
        except Exception:
            await db.rollback()
            raise
