import uuid
from typing import List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DataNotFoundError
from app.db.models.case import Case
from app.schemas.case import CaseCreate, CaseUpdate
from app.services.audit_service import AuditService


class CaseService:
    def __init__(self, audit_service: AuditService):
        self.audit_service = audit_service

    async def get_case(self, db: AsyncSession, case_id: UUID) -> Case:
        case = await db.get(Case, case_id)
        if not case:
            raise DataNotFoundError("Case not found")
        return case

    async def get_cases(self, db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Case]:
        stmt = select(Case).offset(skip).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def create_case(self, db: AsyncSession, case_in: CaseCreate, current_user: dict) -> Case:
        case_number = f"CASE-{uuid.uuid4().hex[:8].upper()}"
        user_id = (
            UUID(current_user["id"]) if isinstance(current_user["id"], str) else current_user["id"]
        )

        case = Case(
            **case_in.model_dump(),
            case_number=case_number,
            created_by=user_id,
        )
        db.add(case)
        await db.flush()

        await self.audit_service.log_action(
            user_id=user_id,
            action="CREATE_CASE",
            payload={"case_number": case_number},
            db=db,
            case_id=case.id,
            target_resource="case",
            target_id=str(case.id),
        )

        await db.commit()
        await db.refresh(case)
        return case

    async def update_case(
        self, db: AsyncSession, case_id: UUID, case_in: CaseUpdate, current_user: dict
    ) -> Case:
        case = await self.get_case(db, case_id)

        update_data = case_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(case, field, value)

        user_id = (
            UUID(current_user["id"]) if isinstance(current_user["id"], str) else current_user["id"]
        )

        await self.audit_service.log_action(
            user_id=user_id,
            action="UPDATE_CASE",
            payload={"fields_updated": list(update_data.keys())},
            db=db,
            case_id=case.id,
            target_resource="case",
            target_id=str(case.id),
        )

        await db.commit()
        await db.refresh(case)
        return case
