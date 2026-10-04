from fastapi import APIRouter

from app.api.v1 import (
    antivenom,
    cases,
    clinical_guidelines,
    facilities,
    surveillance,
)

router = APIRouter()

router.include_router(cases.router, prefix="/cases", tags=["cases"])
router.include_router(facilities.router, prefix="/facilities", tags=["facilities"])
router.include_router(antivenom.router, prefix="/antivenom", tags=["antivenom"])
router.include_router(surveillance.router, prefix="/surveillance", tags=["surveillance"])
router.include_router(clinical_guidelines.router, prefix="/guidelines", tags=["guidelines"])
