from fastapi import APIRouter

# Import all endpoint routers
from .endpoints.ble import router as ble_router

# Create the main API router
api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(ble_router, prefix="/ble", tags=["bluetooth"])