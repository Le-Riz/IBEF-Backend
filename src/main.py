from fastapi import FastAPI
from pydantic_settings import BaseSettings

from routers.api import router as api_router
from schemas import AppHealthOK

class Settings(BaseSettings):
    app_name: str = "IBEF Backend API"
    debug: bool = True


settings = Settings()

app = FastAPI(title=settings.app_name, debug=settings.debug)


@app.get("/", tags=["meta"])
async def read_root() -> dict[str, str]:
    return {"message": settings.app_name}


@app.get("/health", tags=["meta"], response_model=AppHealthOK)
async def healthcheck() -> AppHealthOK:
    return AppHealthOK(status="ok", app=settings.app_name)


# mount API router under /api
app.include_router(api_router, prefix="/api")
