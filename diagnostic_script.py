"""
Diagnostic script to identify FastAPI response model issues.
"""

import json
import logging
from typing import List, Dict, Any, Callable
from fastapi import FastAPI, APIRouter, Depends, HTTPException, Response
from fastapi.routing import APIRoute
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Mock BLE Service and Data
class MockBleService:
    def get_saved_devices(self) -> List[Dict[str, Any]]:
        return [{"address": "12:34:56:78:90:AB", "name": "Test Device"}]

def get_mock_ble_service() -> MockBleService:
    return MockBleService()

# Mock Data Transfer Object (DTO)
class BondedDevice(BaseModel):
    address: str
    name: str

# Diagnostic Functions
def check_route_response(route: APIRoute):
    """
    Check if a route is using a direct Response or a response_model.
    """
    if route.response_model:
        logger.info(f"Route '{route.path}' uses response_model: {route.response_model}")
    else:
        logger.warning(f"Route '{route.path}' does NOT use response_model.")

def check_dependency_return_type(dependency: Callable):
    """
    Check the return type annotation of a dependency.
    """
    return_type = getattr(dependency, "__annotations__", {}).get("return")
    logger.info(f"Dependency '{dependency.__name__}' return type: {return_type}")

def check_dependency_serializability(dependency: Callable):
    """
    Check if the return type of a dependency is serializable.
    """
    try:
        result = dependency()  # Call the dependency
        json.dumps(result, default=str)  # Attempt to serialize
        logger.info(f"Dependency '{dependency.__name__}' return type is serializable.")
    except Exception as e:
        logger.error(f"Dependency '{dependency.__name__}' return type is NOT serializable: {e}")

# API Routes
router = APIRouter()

@router.get("/bonded", response_model=List[BondedDevice])
async def list_bonded_devices(ble_service: MockBleService = Depends(get_mock_ble_service)):
    """Get list of bonded/saved devices."""
    devices = ble_service.get_saved_devices()
    # Manually create DTO instances
    bonded_devices = [BondedDevice(**device) for device in devices]
    return bonded_devices

@router.get("/bonded_direct", response_model=List[Dict[str, Any]])
async def list_bonded_devices_direct(ble_service: MockBleService = Depends(get_mock_ble_service)):
    """Get list of bonded/saved devices using direct Response."""
    devices = ble_service.get_saved_devices()
    return Response(content=json.dumps(devices, default=str), media_type="application/json")

# FastAPI App
app = FastAPI()
app.include_router(router)

# Diagnostic Endpoint
@app.get("/_diagnostics")
async def run_diagnostics():
    """
    Run diagnostics on the API routes and dependencies.
    """
    logger.info("Running diagnostics...")
    for route in app.routes:
        if isinstance(route, APIRoute):
            check_route_response(route)
            # Only check dependencies for routes that use them
            if route.path != "/_diagnostics":
                for dependant in route.dependant.dependencies:
                    if dependant.call:
                        check_dependency_return_type(dependant.call)
                        check_dependency_serializability(dependant.call)
    return {"status": "Diagnostics complete. Check logs."}

if __name__ == "__main__":
    import uvicorn
    try:
        uvicorn.run(app, host="0.0.0.0", port=8001)  # Changed port to 8001
    except Exception as e:
        logger.error(f"Failed to start the diagnostic script: {e}")