from typing import List, Optional

from fastapi import APIRouter, Depends

from app.core.security import get_current_user
from app.schemas.clinical_guideline import ClinicalGuideline
from app.services.clinical_guideline_service import ClinicalGuidelineService

router = APIRouter()
guideline_service = ClinicalGuidelineService()


@router.get("/search", response_model=List[ClinicalGuideline])
async def search_guidelines(
    topic: Optional[str] = None, current_user: dict = Depends(get_current_user)
):
    return await guideline_service.search(topic)
