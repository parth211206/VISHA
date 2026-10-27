from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.schemas.inventory import InventoryItemCreate, InventoryItemResponse, InventoryItemUpdate
from app.services.audit_service import AuditService
from app.services.inventory_service import AntivenomInventoryService

router = APIRouter()
inventory_service = AntivenomInventoryService(AuditService())


@router.get(
    "/{facility_id}/inventory",
    response_model=List[InventoryItemResponse],
)
async def list_facility_inventory(
    facility_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """List facility-reported stock records; not a clinical recommendation."""
    return await inventory_service.list_items(db, facility_id)


@router.post(
    "/{facility_id}/inventory",
    response_model=InventoryItemResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_facility_inventory(
    facility_id: UUID,
    item_in: InventoryItemCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return await inventory_service.create_item(
        db, facility_id, item_in, current_user
    )


@router.patch(
    "/{facility_id}/inventory/{inventory_id}",
    response_model=InventoryItemResponse,
)
async def update_facility_inventory(
    facility_id: UUID,
    inventory_id: UUID,
    item_in: InventoryItemUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return await inventory_service.update_item(
        db, facility_id, inventory_id, item_in, current_user
    )
