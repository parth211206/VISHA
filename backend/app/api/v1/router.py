from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()

def create_stub_router(name: str):
    r = APIRouter()
    @r.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
    async def stub_endpoint(path: str):
        return JSONResponse(status_code=501, content={"status": "not_implemented", "endpoint": name})
    return r

# Create stubs for the different modules
router.include_router(create_stub_router("cases"), prefix="/cases", tags=["cases"])
router.include_router(create_stub_router("taxonomy"), prefix="/taxonomy", tags=["taxonomy"])
router.include_router(create_stub_router("analysis"), prefix="/analysis", tags=["analysis"])
router.include_router(create_stub_router("antivenom"), prefix="/antivenom", tags=["antivenom"])
router.include_router(create_stub_router("surveillance"), prefix="/surveillance", tags=["surveillance"])
router.include_router(create_stub_router("auth"), prefix="/auth", tags=["auth"])
