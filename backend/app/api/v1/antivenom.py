from typing import List, Optional

from fastapi import APIRouter, Depends

from app.core.security import get_current_user
from app.schemas.antivenom import AntivenomReference
from app.services.antivenom_service import AntivenomService

router = APIRouter()
antivenom_service = AntivenomService()


@router.get("/lookup", response_model=List[AntivenomReference])
async def lookup_antivenom(
    species: Optional[str] = None,
    genus: Optional[str] = None,
    state: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    return await antivenom_service.lookup(species, genus, state)
