"""FastAPI application entry point for the India Snakebite CDS prototype."""
from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

# Make the repository root importable before loading API routers. The ML code lives
# in <project>/ml while Uvicorn's app module is <project>/backend/app/main.py.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
project_root_text = str(PROJECT_ROOT)
if project_root_text not in sys.path:
    sys.path.insert(0, project_root_text)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import router as v1_router
from app.core.config import get_settings
from app.core.exceptions import create_exception_handlers
from app.core.logging_config import setup_logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    setup_logging(settings)
    logger.info("Starting up Snakebite CDS backend...")
    # The ML model loads lazily on the first prediction request. Health checks and
    # the UI can still run when a model dependency/checkpoint needs troubleshooting.
    yield
    logger.info("Shutting down Snakebite CDS backend...")


app = FastAPI(
    title="India Snakebite CDS API",
    description="Clinical Decision Support and Epidemiological Surveillance API",
    version="0.2.0",
    lifespan=lifespan,
)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
create_exception_handlers(app)
app.include_router(
    v1_router,
    prefix=settings.app.api_prefix if hasattr(settings.app, "api_prefix") else "/api/v1",
)


@app.get("/health", tags=["system"])
async def health_check() -> dict[str, str]:
    settings = get_settings()
    return {"status": "ok", "version": app.version, "environment": settings.app.env}


frontend_dir = PROJECT_ROOT / "frontend" / "public"
if not frontend_dir.is_dir():
    logger.warning("Frontend static directory not found: %s", frontend_dir)
else:
    # Register last so API routes /health remain higher priority than the static catch-all.
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
