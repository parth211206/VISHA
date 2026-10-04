from typing import List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DataNotFoundError
from app.db.models.surveillance import SurveillanceRecord
from app.schemas.surveillance import SurveillanceRecordCreate
from app.services.audit_service import AuditService


class SurveillanceService:
    def __init__(self, audit_service: AuditService):
        self.audit_service = audit_service

    async def get_record(self, db: AsyncSession, record_id: UUID) -> SurveillanceRecord:
        record = await db.get(SurveillanceRecord, record_id)
        if not record:
            raise DataNotFoundError("Surveillance record not found")
        return record

    async def get_records(
        self, db: AsyncSession, skip: int = 0, limit: int = 100
    ) -> List[SurveillanceRecord]:
        stmt = select(SurveillanceRecord).offset(skip).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def create_record(
        self, db: AsyncSession, record_in: SurveillanceRecordCreate, current_user: dict
    ) -> SurveillanceRecord:
        user_id = (
            UUID(current_user["id"]) if isinstance(current_user["id"], str) else current_user["id"]
        )

        record = SurveillanceRecord(**record_in.model_dump())
        db.add(record)
        await db.flush()

        await self.audit_service.log_action(
            user_id=user_id,
            action="CREATE_SURVEILLANCE_RECORD",
            payload={"state": record.state, "district": record.district},
            db=db,
            case_id=record.case_id,
            target_resource="surveillance_record",
            target_id=str(record.id),
        )

        await db.commit()
        await db.refresh(record)
        return record
