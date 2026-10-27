from fastapi import APIRouter, HTTPException

from app.schemas.clinical_reference import ClinicalReferenceList
from app.services.clinical_references_service import ClinicalReferencesService


router = APIRouter()


@router.get(
    "/",
    response_model=ClinicalReferenceList,
    tags=["clinical-references"],
)
async def list_clinical_references():
    """Return the validated clinical guideline reference catalogue.

    This endpoint does not fetch external websites on every request;
    the catalogue is loaded once at service initialisation.

    The returned data require clinician interpretation and must not be
    used to automatically select antivenom or delay emergency care.

    Raises:
        503: if the reference catalogue cannot be loaded or is malformed.
    """
    try:
        service = ClinicalReferencesService()
        refs = service.list_references()
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Clinical reference catalogue unavailable: {exc}",
        ) from exc

    return refs