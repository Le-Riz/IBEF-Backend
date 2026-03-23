"""Main API router aggregating all sub-routers.

This module serves as the entry point for all API endpoints, combining routers
for history, test management, sensor operations, and graphique data visualization.
"""

from fastapi import APIRouter

from routers import history, test, sensor, graphique

router = APIRouter()

# include sub-routers
router.include_router(history.router)
router.include_router(test.router)
router.include_router(sensor.router)
router.include_router(graphique.router)
