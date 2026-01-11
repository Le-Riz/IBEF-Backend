from fastapi import APIRouter

from routers import history, test, sensor

router = APIRouter()

# include sub-routers
router.include_router(history.router)
router.include_router(test.router)
router.include_router(sensor.router)
