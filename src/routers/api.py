from fastapi import APIRouter

from routers import data, raw, history, test

router = APIRouter()

# include sub-routers
router.include_router(data.router)
router.include_router(raw.router)
router.include_router(test.router)
router.include_router(history.router)
