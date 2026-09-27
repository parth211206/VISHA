from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.core.config import get_settings
from app.core.logging_config import setup_logging
from app.core.exceptions import create_exception_handlers
from app.api.v1.router import router as v1_router

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    setup_logging(settings)
    logger.info("Starting up Snakebite CDS backend...")
    # Add DB connection check here later
    yield
    logger.info("Shutting down Snakebite CDS backend...")

app = FastAPI(
    title="India Snakebite CDS API",
    description="Clinical Decision Support and Epidemiological Surveillance API",
    version="0.1.0",
    lifespan=lifespan
)

# CORS configuration
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Update for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register exceptions
create_exception_handlers(app)

# Mount API v1
app.include_router(v1_router, prefix=settings.app.api_prefix if hasattr(settings.app, 'api_prefix') else "/api/v1")

@app.get("/health", tags=["system"])
async def health_check():
    settings = get_settings()
    return {
        "status": "ok",
        "version": "0.1.0",
        "environment": settings.app.env
    }
