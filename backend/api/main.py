"""FastAPI entry point, independent from the Streamlit application."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import settings
from .logging_config import configure_logging
from .routes.health import router as health_router
from .routes.auth import router as auth_router
from .routes.webrtc import router as webrtc_router
from .routes.workouts import router as workouts_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Configure logging and report application lifecycle events."""
    settings.validate_production()
    configure_logging()
    logger.info("Starting FastAPI backend in %s environment", settings.environment)
    yield
    logger.info("Stopping FastAPI backend")


app = FastAPI(
    title="AI Gym Coach API",
    description="Backend API for the AI Gym Coach application.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Log unexpected failures and return a consistent JSON error response."""
    logger.exception("Unhandled request error: %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


app.include_router(health_router)
app.include_router(auth_router)
app.include_router(workouts_router)
app.include_router(webrtc_router)
