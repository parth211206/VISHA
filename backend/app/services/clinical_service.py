from typing import List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DataNotFoundError
from app.db.models.clinical import ClinicalEvidence
from app.schemas.clinical import ClinicalEvidenceCreate
from app.services.audit_service import AuditService


class ClinicalService:
    def __init__(self, audit_service: AuditService):
        self.audit_service = audit_service

    async def get_clinical_evidence(self, db: AsyncSession, evidence_id: UUID) -> ClinicalEvidence:
        evidence = await db.get(ClinicalEvidence, evidence_id)
        if not evidence:
            raise DataNotFoundError("Clinical evidence not found")
        return evidence

    async def get_case_clinical_evidence(
        self, db: AsyncSession, case_id: UUID
    ) -> List[ClinicalEvidence]:
        stmt = select(ClinicalEvidence).where(ClinicalEvidence.case_id == case_id)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def create_clinical_evidence(
        self,
        db: AsyncSession,
        case_id: UUID,
        evidence_in: ClinicalEvidenceCreate,
        current_user: dict,
    ) -> ClinicalEvidence:
        evidence = ClinicalEvidence(**evidence_in.model_dump(), case_id=case_id)
        db.add(evidence)
        await db.flush()

        user_id = (
            UUID(current_user["id"]) if isinstance(current_user["id"], str) else current_user["id"]
        )

        await self.audit_service.log_action(
            user_id=user_id,
            action="CREATE_CLINICAL_EVIDENCE",
            payload={"syndrome": evidence.syndrome},
            db=db,
            case_id=case_id,
            target_resource="clinical_evidence",
            target_id=str(evidence.id),
        )

        await db.commit()
        await db.refresh(evidence)
        return evidence
