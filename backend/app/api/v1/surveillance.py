from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.schemas.surveillance import SurveillanceRecordCreate, SurveillanceRecordResponse
from app.services.audit_service import AuditService
from app.services.surveillance_service import SurveillanceService

router = APIRouter()
audit_service = AuditService()
surveillance_service = SurveillanceService(audit_service)


@router.post("/", response_model=SurveillanceRecordResponse)
async def create_surveillance_record(
    record_in: SurveillanceRecordCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return await surveillance_service.create_record(db, record_in, current_user)


@router.get("/{record_id}", response_model=SurveillanceRecordResponse)
async def get_surveillance_record(
    record_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return await surveillance_service.get_record(db, record_id)
