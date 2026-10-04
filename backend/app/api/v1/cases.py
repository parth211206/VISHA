from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.schemas.case import CaseCreate, CaseResponse, CaseUpdate
from app.schemas.clinical import ClinicalEvidenceCreate, ClinicalEvidenceResponse
from app.schemas.prediction import PredictionCreate, PredictionResponse
from app.schemas.review import ClinicianReviewCreate, ClinicianReviewResponse
from app.services.audit_service import AuditService
from app.services.case_service import CaseService
from app.services.clinical_service import ClinicalService
from app.services.prediction_service import PredictionService
from app.services.review_service import ReviewService

router = APIRouter()
audit_service = AuditService()
case_service = CaseService(audit_service)
prediction_service = PredictionService(audit_service)
clinical_service = ClinicalService(audit_service)
review_service = ReviewService(audit_service)


@router.post("/", response_model=CaseResponse)
async def create_case(
    case_in: CaseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return await case_service.create_case(db, case_in, current_user)


@router.get("/{case_id}", response_model=CaseResponse)
async def get_case(
    case_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return await case_service.get_case(db, case_id)


@router.patch("/{case_id}", response_model=CaseResponse)
async def update_case(
    case_id: UUID,
    case_in: CaseUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return await case_service.update_case(db, case_id, case_in, current_user)


@router.post("/{case_id}/predictions", response_model=PredictionResponse)
async def create_prediction(
    case_id: UUID,
    prediction_in: PredictionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return await prediction_service.create_prediction(db, case_id, prediction_in, current_user)


@router.get("/{case_id}/predictions", response_model=List[PredictionResponse])
async def get_predictions(
    case_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return await prediction_service.get_case_predictions(db, case_id)


@router.post("/{case_id}/clinical-evidence", response_model=ClinicalEvidenceResponse)
async def create_clinical_evidence(
    case_id: UUID,
    evidence_in: ClinicalEvidenceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return await clinical_service.create_clinical_evidence(db, case_id, evidence_in, current_user)


@router.get("/{case_id}/clinical-evidence", response_model=List[ClinicalEvidenceResponse])
async def get_clinical_evidence(
    case_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return await clinical_service.get_case_clinical_evidence(db, case_id)


@router.post("/{case_id}/reviews", response_model=ClinicianReviewResponse)
async def create_review(
    case_id: UUID,
    review_in: ClinicianReviewCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return await review_service.create_review(db, case_id, review_in, current_user)


@router.get("/{case_id}/reviews", response_model=List[ClinicianReviewResponse])
async def get_reviews(
    case_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return await review_service.get_case_reviews(db, case_id)
