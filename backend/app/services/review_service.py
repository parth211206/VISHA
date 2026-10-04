from typing import List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DataNotFoundError
from app.db.models.review import ClinicianReview
from app.schemas.review import ClinicianReviewCreate
from app.services.audit_service import AuditService


class ReviewService:
    def __init__(self, audit_service: AuditService):
        self.audit_service = audit_service

    async def get_review(self, db: AsyncSession, review_id: UUID) -> ClinicianReview:
        review = await db.get(ClinicianReview, review_id)
        if not review:
            raise DataNotFoundError("Review not found")
        return review

    async def get_case_reviews(self, db: AsyncSession, case_id: UUID) -> List[ClinicianReview]:
        stmt = select(ClinicianReview).where(ClinicianReview.case_id == case_id)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def create_review(
        self, db: AsyncSession, case_id: UUID, review_in: ClinicianReviewCreate, current_user: dict
    ) -> ClinicianReview:
        user_id = (
            UUID(current_user["id"]) if isinstance(current_user["id"], str) else current_user["id"]
        )

        review = ClinicianReview(**review_in.model_dump(), case_id=case_id, reviewed_by=user_id)
        db.add(review)
        await db.flush()

        await self.audit_service.log_action(
            user_id=user_id,
            action="CREATE_REVIEW",
            payload={"clinician_diagnosis": review.clinician_diagnosis},
            db=db,
            case_id=case_id,
            target_resource="review",
            target_id=str(review.id),
        )

        await db.commit()
        await db.refresh(review)
        return review
