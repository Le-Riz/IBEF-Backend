from fastapi import FastAPI
from pydantic_settings import BaseSettings
from contextlib import asynccontextmanager
import os
import logging

from routers.api import router as api_router
from schemas import AppHealthOK
from core.service_manager import service_manager
from core.config_loader import config_loader

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    app_name: str = "IBEF Backend API"
    debug: bool = True
    # Allow emulation mode if no serial port is found
    # If False, the app will crash if no serial port is available
    # Can be overridden by environment variable or config file
    emulation_mode: bool = os.getenv("EMULATION_MODE", "").lower() == "true" \
        if os.getenv("EMULATION_MODE") else config_loader.get_emulation_mode()


settings = Settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup/shutdown without deprecated on_event."""
    try:
        logger.info(
            "Starting background services in %s mode", "emulation" if settings.emulation_mode else "hardware"
        )
        await service_manager.start_services(emulation=settings.emulation_mode)
    except Exception as e:
        if settings.emulation_mode:
            logger.error("Failed to start services: %s, falling back to emulation mode", e)
            await service_manager.start_services(emulation=True)
        else:
            logger.error("Failed to start services and emulation mode is disabled: %s", e)
            raise

    try:
        yield
    finally:
        logger.info("Stopping background services")
        service_manager.stop_services()


app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=lifespan)


@app.get("/", tags=["meta"])
async def read_root() -> dict[str, str]:
    return {"message": settings.app_name}


@app.get("/health", tags=["meta"], response_model=AppHealthOK)
async def healthcheck() -> AppHealthOK:
    return AppHealthOK(status="ok", app=settings.app_name)


# mount API router under /api
app.include_router(api_router, prefix="/api")
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
