from fastapi import APIRouter

from app.api.v1 import (
    antivenom,
    cases,
    clinical_assessment,
    clinical_guidelines,
    clinical_references,
    facilities,
    facility_inventory,
    ml_inference,
    surveillance,
)

router = APIRouter()

router.include_router(cases.router, prefix="/cases", tags=["cases"])
router.include_router(facilities.router, prefix="/facilities", tags=["facilities"])
router.include_router(facility_inventory.router, prefix="/facilities", tags=["facility-inventory"])
router.include_router(clinical_assessment.router, prefix="/assessment", tags=["clinical-assessment"])
router.include_router(antivenom.router, prefix="/antivenom", tags=["antivenom"])
router.include_router(surveillance.router, prefix="/surveillance", tags=["surveillance"])
router.include_router(clinical_guidelines.router, prefix="/guidelines", tags=["guidelines"])
router.include_router(clinical_references.router, prefix="/clinical-references", tags=["clinical-references"])
router.include_router(ml_inference.router)
