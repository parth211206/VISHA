from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.schemas.case import CaseCreate
from app.schemas.facility import AntivenomFacilityCreate
from app.services.audit_service import AuditService
from app.services.case_service import CaseService
from app.services.facility_service import FacilityService


@pytest.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as session:
        yield session

    await engine.dispose()


@pytest.fixture
def current_user():
    return {"id": str(uuid4()), "username": "testuser", "role": "clinician"}


@pytest.fixture
def audit_service():
    return AuditService()


@pytest.mark.asyncio
async def test_create_case(db_session, current_user, audit_service):
    service = CaseService(audit_service)
    case_in = CaseCreate(patient_age_years=30)

    case = await service.create_case(db_session, case_in, current_user)

    assert case.id is not None
    assert case.patient_age_years == 30
    assert case.case_number.startswith("CASE-")


@pytest.mark.asyncio
async def test_create_facility(db_session, current_user, audit_service):
    service = FacilityService(audit_service)
    facility_in = AntivenomFacilityCreate(name="Test Hospital", state="Maharashtra")

    facility = await service.create_facility(db_session, facility_in, current_user)

    assert facility.id is not None
    assert facility.name == "Test Hospital"
    assert facility.state == "Maharashtra"
