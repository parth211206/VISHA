from typing import List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DataNotFoundError
from app.db.models.prediction import CasePrediction
from app.schemas.prediction import PredictionCreate
from app.services.audit_service import AuditService


class PredictionService:
    def __init__(self, audit_service: AuditService):
        self.audit_service = audit_service

    async def get_prediction(self, db: AsyncSession, prediction_id: UUID) -> CasePrediction:
        prediction = await db.get(CasePrediction, prediction_id)
        if not prediction:
            raise DataNotFoundError("Prediction not found")
        return prediction

    async def get_case_predictions(self, db: AsyncSession, case_id: UUID) -> List[CasePrediction]:
        stmt = select(CasePrediction).where(CasePrediction.case_id == case_id)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def create_prediction(
        self, db: AsyncSession, case_id: UUID, prediction_in: PredictionCreate, current_user: dict
    ) -> CasePrediction:
        prediction = CasePrediction(**prediction_in.model_dump(), case_id=case_id)
        db.add(prediction)
        await db.flush()

        user_id = (
            UUID(current_user["id"]) if isinstance(current_user["id"], str) else current_user["id"]
        )

        await self.audit_service.log_action(
            user_id=user_id,
            action="CREATE_PREDICTION",
            payload={"source": prediction.source},
            db=db,
            case_id=case_id,
            target_resource="prediction",
            target_id=str(prediction.id),
        )

        await db.commit()
        await db.refresh(prediction)
        return prediction
