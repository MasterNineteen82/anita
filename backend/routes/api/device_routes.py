from fastapi import APIRouter, HTTPException, Query, Depends, status
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
import logging
import time
from backend.modules.device_manager import DeviceManager
from backend.logging.logging_config import get_api_logger
from ..utils import handle_errors
# Import common models
from backend.models import ErrorResponse, SuccessResponse, ReaderResponse, ReadersResponse

# Define specific models for this module
class SimulationRequest(BaseModel):
    enabled: bool = Field(..., description="Enable or disable simulation mode")

# Use the router definition as is
router = APIRouter(
    prefix="/devices",
    tags=["devices"],
    responses={
        404: {"description": "Not found", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse}
    }
)
logger = get_api_logger()

@router.get("/readers", response_model=ReadersResponse)
@handle_errors
async def list_readers(force_refresh: bool = Query(False, description="Force fresh device discovery")):
    """
    List all available card readers.
    
    Returns a list of available smartcard and NFC readers in the system.
    Set force_refresh=true to bypass cache and get fresh device data.
    """
    logger.info(f"API call: list_readers with force_refresh={force_refresh}")
    try:
        result = await DeviceManager.list_smartcard_readers(force_refresh)
        logger.debug(f"Found readers: {result}")
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list readers: {str(e)}"
        )

@router.get("/readers/{reader_name}/select")
@handle_errors
async def select_reader(reader_name: str):
    """
    Select a specific reader for operations.
    
    This endpoint selects a reader to be used for subsequent card operations.
    If the reader doesn't exist, a 404 error is returned.
    """
    logger.info(f"API call: select_reader {reader_name}")
    try:
        # Check if reader exists first
        readers_result = await DeviceManager.list_smartcard_readers(force_refresh=False)
        if readers_result['status'] == 'success':
            reader_names = [r['name'] for r in readers_result['data']['readers']]
            if reader_name not in reader_names:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Reader '{reader_name}' not found. Available readers: {reader_names}"
                )
        return await DeviceManager.select_reader(reader_name)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to select reader: {str(e)}"
        )

@router.get("/readers/{reader_name}/health")
@handle_errors
async def check_reader_health(reader_name: str):
    """
    Check the health status of a specific reader.
    
    Returns detailed health information about the specified reader.
    If the reader is not responding or has issues, appropriate status codes are returned.
    """
    logger.info(f"API call: check_reader_health {reader_name}")
    try:
        result = await DeviceManager.check_reader_health(reader_name)
        # Set appropriate status code based on health check result
        if result['status'] == 'error':
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=result['message']
            )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check reader health: {str(e)}"
        )

@router.post("/readers/{reader_name}/read")
async def read_card(
    reader_name: str, 
    options: Optional[Dict] = None
):
    """Read data from a card"""
    try:
        return await DeviceManager.read_card(reader_name, options)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read card: {str(e)}"
        )

@router.post("/simulation")
@handle_errors
async def set_simulation_mode(simulation: SimulationRequest):
    """
    Toggle simulation mode for testing without physical devices.
    
    This is useful for development and testing when physical readers are not available.
    """
    logger.info(f"API call: set_simulation_mode {simulation.enabled}")
    try:
        return await DeviceManager.set_simulation_mode(simulation.enabled)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to set simulation mode: {str(e)}"
        )

@router.get("/nfc")
@handle_errors
async def discover_nfc():
    """
    Discover NFC devices only.
    
    Returns information about connected NFC devices and their capabilities.
    """
    logger.info("API call: discover_nfc")
    try:
        result = await DeviceManager.discover_nfc_device()
        # Check for timeout errors which can happen with NFC discovery
        if result['status'] == 'error' and 'timeout' in result.get('data', {}).get('message', '').lower():
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="NFC device discovery timed out"
            )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to discover NFC devices: {str(e)}"
        )

@router.get("/status")
@handle_errors
async def device_system_status():
    """
    Get overall status of the device management system.
    
    Returns information about system status, including available readers,
    simulation mode status, and any detected issues.
    """
    logger.info("API call: device_system_status")
    
    # Gather status from multiple sources
    readers_result = await DeviceManager.list_smartcard_readers(force_refresh=False)
    nfc_result = await DeviceManager.discover_nfc_device()
    
    status_report = {
        "status": "healthy" if readers_result['status'] == 'success' else "degraded",
        "data": {
            "readers": readers_result.get('data', {}).get('readers', []),
            "nfc_device": nfc_result.get('data', {}).get('device'),
            "simulation_mode": any(r.get('simulation', False) for r in readers_result.get('data', {}).get('readers', [])),
            "timestamp": int(time.time())
        }
    }
    
    return status_report