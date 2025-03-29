"""Bluetooth service-related routes."""

import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Path

from backend.dependencies import get_ble_service
from backend.modules.ble.ble_service import BleService

# Create router
service_router = APIRouter(prefix="/service", tags=["BLE Services"])

# Get logger
logger = logging.getLogger(__name__)

@service_router.get("/list")
async def list_services(ble_service: BleService = Depends(get_ble_service)):
    """Get all services from the connected device."""
    try:
        if not ble_service.is_connected():
            raise HTTPException(status_code=400, detail="No device connected")
        
        services = await ble_service.get_services()
        return {
            "services": services,
            "count": len(services)
        }
    except Exception as e:
        logger.error(f"Error listing services: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@service_router.get("/{service_uuid}")
async def get_service_info(
    service_uuid: str = Path(..., description="UUID of the service"),
    ble_service: BleService = Depends(get_ble_service)
):
    """Get detailed information about a specific service."""
    try:
        if not ble_service.is_connected():
            raise HTTPException(status_code=400, detail="No device connected")
        
        service_info = await ble_service.get_service_info(service_uuid)
        
        if not service_info:
            raise HTTPException(status_code=404, detail=f"Service {service_uuid} not found")
        
        return service_info
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting service info: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@service_router.get("/{service_uuid}/characteristics")
async def get_characteristics(
    service_uuid: str = Path(..., description="UUID of the service"),
    ble_service: BleService = Depends(get_ble_service)
):
    """Get all characteristics for a specific service."""
    try:
        if not ble_service.is_connected():
            raise HTTPException(status_code=400, detail="No device connected")
        
        characteristics = await ble_service.get_characteristics(service_uuid)
        return {
            "characteristics": characteristics,
            "count": len(characteristics)
        }
    except Exception as e:
        logger.error(f"Error getting characteristics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@service_router.get("/{service_uuid}/characteristics/{char_uuid}")
async def get_characteristic_info(
    service_uuid: str = Path(..., description="UUID of the service"),
    char_uuid: str = Path(..., description="UUID of the characteristic"),
    ble_service: BleService = Depends(get_ble_service)
):
    """Get detailed information about a specific characteristic."""
    try:
        if not ble_service.is_connected():
            raise HTTPException(status_code=400, detail="No device connected")
        
        char_info = await ble_service.get_characteristic_info(service_uuid, char_uuid)
        
        if not char_info:
            raise HTTPException(status_code=404, detail=f"Characteristic {char_uuid} not found in service {service_uuid}")
        
        return char_info
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting characteristic info: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@service_router.get("/{service_uuid}/characteristics/{char_uuid}/descriptors")
async def get_descriptors(
    service_uuid: str = Path(..., description="UUID of the service"),
    char_uuid: str = Path(..., description="UUID of the characteristic"),
    ble_service: BleService = Depends(get_ble_service)
):
    """Get all descriptors for a specific characteristic."""
    try:
        if not ble_service.is_connected():
            raise HTTPException(status_code=400, detail="No device connected")
        
        descriptors = await ble_service.get_descriptors(service_uuid, char_uuid)
        return {
            "descriptors": descriptors,
            "count": len(descriptors)
        }
    except Exception as e:
        logger.error(f"Error getting descriptors: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@service_router.get("/active-notifications")
async def get_active_notifications(ble_service: BleService = Depends(get_ble_service)):
    """Get a list of characteristics with active notifications."""
    try:
        if not ble_service.is_connected():
            raise HTTPException(status_code=400, detail="No device connected")
        
        notifications = ble_service.get_active_notifications()
        return {
            "characteristics": notifications,
            "count": len(notifications)
        }
    except Exception as e:
        logger.error(f"Error getting active notifications: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))