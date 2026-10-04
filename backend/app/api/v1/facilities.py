from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.schemas.facility import (
    AntivenomFacilityCreate,
    AntivenomFacilityResponse,
    AntivenomFacilityUpdate,
)
from app.services.audit_service import AuditService
from app.services.facility_service import FacilityService

router = APIRouter()
audit_service = AuditService()
facility_service = FacilityService(audit_service)


@router.post("/", response_model=AntivenomFacilityResponse)
async def create_facility(
    facility_in: AntivenomFacilityCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return await facility_service.create_facility(db, facility_in, current_user)


@router.get("/{facility_id}", response_model=AntivenomFacilityResponse)
async def get_facility(
    facility_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return await facility_service.get_facility(db, facility_id)


@router.patch("/{facility_id}", response_model=AntivenomFacilityResponse)
async def update_facility(
    facility_id: UUID,
    facility_in: AntivenomFacilityUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return await facility_service.update_facility(db, facility_id, facility_in, current_user)
