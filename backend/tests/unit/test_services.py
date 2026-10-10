from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import event

import app.db.models  # noqa: F401 — register models with SQLAlchemy
from app.db.base import Base
from app.schemas.case import CaseCreate
from app.schemas.facility import AntivenomFacilityCreate
from app.services.audit_service import AuditService
from app.services.case_service import CaseService
from app.services.facility_service import FacilityService


@pytest.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    # Track original server_defaults and column types for columns we need to fix for SQLite compatibility
    overridden_defaults = {}
    overridden_types = {}

    try:
        # Fix PostgreSQL-specific defaults and types that don't work in SQLite
        if engine.dialect.name == "sqlite":
            from sqlalchemy.schema import DefaultClause
            from sqlalchemy.sql.elements import TextClause
            from sqlalchemy import String
            from sqlalchemy.dialects.postgresql import INET
            from geoalchemy2.types import Geometry, Geography

            # Find columns with PostgreSQL-specific types and defaults and replace with SQLite-compatible ones
            for table in Base.metadata.tables.values():
                for column in table.columns:
                    # Fix INET type (used for ip_address) to String for SQLite
                    if isinstance(column.type, INET):
                        # Store original type for restoration
                        overridden_types[column] = column.type
                        # Replace with String (SQLite-compatible)
                        column.type = String()

                    # Fix Geometry and Geography types to String for SQLite
                    elif isinstance(column.type, (Geometry, Geography)):
                        # Store original type for restoration
                        overridden_types[column] = column.type
                        # Replace with String (SQLite-compatible)
                        column.type = String()

                    # Fix PostgreSQL::jsonb casts in server defaults
                    if (column.server_default is not None and
                        isinstance(column.server_default, DefaultClause) and
                        isinstance(column.server_default.arg, TextClause) and
                        "::jsonb" in column.server_default.arg.text):
                        # Store original default for restoration
                        overridden_defaults[column] = column.server_default
                        # Extract the TextClause and remove the ::jsonb cast
                        original_text = column.server_default.arg.text
                        # Remove the ::jsonb cast to make it SQLite-compatible
                        sqlite_compatible_text = original_text.replace("::jsonb", "")
                        # Create new server default with SQLite-compatible text
                        column.server_default = DefaultClause(TextClause(sqlite_compatible_text))


        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with Session() as session:
            yield session

    finally:
        # Restore original server_defaults
        for column, original_default in overridden_defaults.items():
            column.server_default = original_default
        # Restore original column types
        for column, original_type in overridden_types.items():
            column.type = original_type

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
