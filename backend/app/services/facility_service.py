from typing import List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DataNotFoundError
from app.db.models.facility import AntivenomFacility
from app.schemas.facility import AntivenomFacilityCreate, AntivenomFacilityUpdate
from app.services.audit_service import AuditService


class FacilityService:
    def __init__(self, audit_service: AuditService):
        self.audit_service = audit_service

    async def get_facility(self, db: AsyncSession, facility_id: UUID) -> AntivenomFacility:
        facility = await db.get(AntivenomFacility, facility_id)
        if not facility:
            raise DataNotFoundError("Facility not found")
        return facility

    async def get_facilities(
        self, db: AsyncSession, skip: int = 0, limit: int = 100
    ) -> List[AntivenomFacility]:
        stmt = select(AntivenomFacility).offset(skip).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def create_facility(
        self, db: AsyncSession, facility_in: AntivenomFacilityCreate, current_user: dict
    ) -> AntivenomFacility:
        facility = AntivenomFacility(**facility_in.model_dump())
        db.add(facility)
        await db.flush()

        await self.audit_service.log_action(
            user_id=UUID(current_user["id"])
            if isinstance(current_user.get("id"), str)
            else current_user.get("id"),
            action="CREATE_FACILITY",
            payload={"facility_name": facility.name},
            db=db,
            target_resource="facility",
            target_id=str(facility.id),
        )
        await db.commit()
        await db.refresh(facility)
        return facility

    async def update_facility(
        self,
        db: AsyncSession,
        facility_id: UUID,
        facility_in: AntivenomFacilityUpdate,
        current_user: dict,
    ) -> AntivenomFacility:
        facility = await self.get_facility(db, facility_id)

        update_data = facility_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(facility, field, value)

        await self.audit_service.log_action(
            user_id=UUID(current_user["id"])
            if isinstance(current_user.get("id"), str)
            else current_user.get("id"),
            action="UPDATE_FACILITY",
            payload={"fields_updated": list(update_data.keys())},
            db=db,
            target_resource="facility",
            target_id=str(facility.id),
        )
        await db.commit()
        await db.refresh(facility)
        return facility
