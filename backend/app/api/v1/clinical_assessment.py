
import logging

from fastapi import APIRouter, Depends

from app.core.security import get_current_user
from app.schemas.assessment import ClinicalAssessmentRequest
from app.services.antivenom_service import AntivenomService
from app.services.clinical_assessment_service import build_assessment

logger = logging.getLogger(__name__)

router = APIRouter()
antivenom_service = AntivenomService()


@router.post("/evaluate")
async def evaluate_integrated_assessment(
    payload: ClinicalAssessmentRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    result = build_assessment(payload)

    taxonomy = payload.taxonomy
    verified_taxonomy_available = bool(
        taxonomy.verified
        and taxonomy.source
        and (taxonomy.species or taxonomy.genus)
    )

    if verified_taxonomy_available:
        try:
            references = await antivenom_service.lookup(
                taxonomy.species,
                taxonomy.genus,
                payload.state,
            )

            result["antivenom_assessment"]["reference_matches"] = [
                item.model_dump(mode="json")
                if hasattr(item, "model_dump")
                else item
                for item in references
            ]

            result["antivenom_assessment"]["reference_lookup_status"] = (
                "MATCHES_FOUND"
                if references
                else "NO_CATALOGUE_MATCH"
            )
        except Exception as exc:
            logger.warning(
                "Assessment succeeded but antivenom catalogue lookup failed: %s",
                type(exc).__name__,
            )
            result["antivenom_assessment"]["reference_lookup_status"] = (
                "CATALOGUE_LOOKUP_FAILED"
            )
            result["antivenom_assessment"]["reference_lookup_note"] += (
                " The catalogue search failed; check the reference service separately."
            )

    return result
