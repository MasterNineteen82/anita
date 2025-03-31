"""Bluetooth service-related routes."""

import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Path

from backend.dependencies import get_ble_service
from backend.modules.ble.core.ble_service import BleService
from backend.modules.ble.models.ble_models import (
    BleService as BleServiceModel,
    BleCharacteristic, 
    BleDescriptor,
    ServicesResult,
    CharacteristicsResult,
    DescriptorsResult,
    NotificationsResult
)

# Create router
service_router = APIRouter(prefix="/service", tags=["BLE Services"])

# Get logger
logger = logging.getLogger(__name__)

def ensure_device_connected(ble_service: BleService):
    """Ensure a BLE device is connected before performing operations."""
    if not ble_service.is_connected():
        raise HTTPException(status_code=400, detail="No device connected")

@service_router.get("/list")
async def list_services(ble_service: BleService = Depends(get_ble_service)):
    """Get all services from the connected device."""
    try:
        ensure_device_connected(ble_service)  # Check connection
        services_raw = await ble_service.get_services()
        
        # Convert to Pydantic models
        services = []
        for svc in services_raw:
            service = BleServiceModel(
                uuid=svc.get("uuid"),
                description=svc.get("description", "Unknown Service"),
                characteristics=[
                    BleCharacteristic(**char) for char in svc.get("characteristics", [])
                ]
            )
            services.append(service)
        
        result = ServicesResult(services=services, count=len(services))
        return result.dict()
    except HTTPException:
        raise
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
        ensure_device_connected(ble_service)  # Check connection
        service_info = await ble_service.get_service_info(service_uuid)
        
        if not service_info:
            raise HTTPException(status_code=404, detail=f"Service {service_uuid} not found")
        
        # Convert to Pydantic model
        service = BleServiceModel(
            uuid=service_info.get("uuid"),
            description=service_info.get("description", "Unknown Service"),
            characteristics=[
                BleCharacteristic(**char) for char in service_info.get("characteristics", [])
            ]
        )
        
        return service.dict()
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
        ensure_device_connected(ble_service)  # Check connection
        chars_raw = await ble_service.get_characteristics(service_uuid)
        
        # Convert to Pydantic models
        characteristics = [
            BleCharacteristic(
                uuid=char.get("uuid"),
                description=char.get("description", "Unknown Characteristic"),
                properties=char.get("properties", []),
                handle=char.get("handle")
            ) for char in chars_raw
        ]
        
        result = CharacteristicsResult(
            service_uuid=service_uuid,
            characteristics=characteristics,
            count=len(characteristics)
        )
        
        return result.dict()
    except HTTPException:
        raise
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
        ensure_device_connected(ble_service)  # Check connection
        char_info = await ble_service.get_characteristic_info(service_uuid, char_uuid)
        
        if not char_info:
            raise HTTPException(
                status_code=404, 
                detail=f"Characteristic {char_uuid} not found in service {service_uuid}"
            )
        
        # Convert to Pydantic model
        characteristic = BleCharacteristic(
            uuid=char_info.get("uuid"),
            description=char_info.get("description", "Unknown Characteristic"),
            properties=char_info.get("properties", []),
            handle=char_info.get("handle"),
            descriptors=[
                BleDescriptor(**desc) for desc in char_info.get("descriptors", [])
            ]
        )
        
        return characteristic.dict()
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
        ensure_device_connected(ble_service)  # Check connection
        desc_raw = await ble_service.get_descriptors(service_uuid, char_uuid)
        
        # Convert to Pydantic models
        descriptors = [
            BleDescriptor(
                uuid=desc.get("uuid"),
                handle=desc.get("handle"),
                description=desc.get("description", "Unknown Descriptor")
            ) for desc in desc_raw
        ]
        
        result = DescriptorsResult(
            service_uuid=service_uuid,
            characteristic_uuid=char_uuid,
            descriptors=descriptors,
            count=len(descriptors)
        )
        
        return result.dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting descriptors: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@service_router.get("/active-notifications")
async def get_active_notifications(ble_service: BleService = Depends(get_ble_service)):
    """Get a list of characteristics with active notifications."""
    try:
        ensure_device_connected(ble_service)  # Check connection
        notifications_raw = ble_service.get_active_notifications()
        
        # Create response model
        result = NotificationsResult(
            characteristics=notifications_raw,
            count=len(notifications_raw)
        )
        
        return result.dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting active notifications: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@service_router.get("/known-services")
async def get_known_services():
    """Get a list of known BLE service UUIDs and their descriptions."""
    try:
        # Common BLE services with their descriptions
        known_services = {
            "1800": "Generic Access",
            "1801": "Generic Attribute",
            "1802": "Immediate Alert",
            "1803": "Link Loss",
            "1804": "Tx Power",
            "1805": "Current Time Service",
            "1806": "Reference Time Update Service",
            "1807": "Next DST Change Service",
            "1808": "Glucose",
            "1809": "Health Thermometer",
            "180A": "Device Information",
            "180D": "Heart Rate",
            "180E": "Phone Alert Status Service",
            "180F": "Battery Service",
            "1810": "Blood Pressure",
            "1811": "Alert Notification Service",
            "1812": "Human Interface Device",
            "1813": "Scan Parameters",
            "1814": "Running Speed and Cadence",
            "1815": "Automation IO",
            "1816": "Cycling Speed and Cadence",
            "1818": "Cycling Power",
            "1819": "Location and Navigation",
            "181A": "Environmental Sensing",
            "181B": "Body Composition",
            "181C": "User Data",
            "181D": "Weight Scale",
            "181E": "Bond Management",
            "181F": "Continuous Glucose Monitoring",
            "1820": "Internet Protocol Support",
            "1821": "Indoor Positioning",
            "1822": "Pulse Oximeter",
            "1823": "HTTP Proxy",
            "1824": "Transport Discovery",
            "1825": "Object Transfer",
            "1826": "Fitness Machine",
            "1827": "Mesh Provisioning",
            "1828": "Mesh Proxy",
            "1829": "Reconnection Configuration",
            "183A": "Insulin Delivery",
            "183B": "Binary Sensor",
            "183C": "Emergency Configuration",
            "FEF5": "Apple Continuity Service"
        }
        
        # Format for response
        services = [
            {"uuid": f"0000{uuid}-0000-1000-8000-00805f9b34fb", "name": name, "shortId": uuid}
            for uuid, name in known_services.items()
        ]
        
        return {"services": services, "count": len(services)}
    except Exception as e:
        logger.error(f"Error getting known services: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@service_router.get("/battery")
async def get_battery_service(ble_service: BleService = Depends(get_ble_service)):
    """Get battery service information from the connected device."""
    try:
        ensure_device_connected(ble_service)  # Check connection
        
        try:
            # Try to find and read battery level
            battery_info = await ble_service.get_battery_info()
            return battery_info
        except Exception as battery_err:
            logger.warning(f"Error reading battery service: {battery_err}")
            return {
                "available": False,
                "error": "Battery service not available or couldn't be read",
                "level": None
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error accessing battery service: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@service_router.get("/device-info")
async def get_device_info_service(ble_service: BleService = Depends(get_ble_service)):
    """Get device information service details from the connected device."""
    try:
        ensure_device_connected(ble_service)  # Check connection
        
        try:
            # Try to find and read device information service
            device_info = await ble_service.get_device_information()
            return device_info
        except Exception as info_err:
            logger.warning(f"Error reading device information service: {info_err}")
            return {
                "available": False,
                "error": "Device Information service not available or couldn't be read",
                "manufacturer": None,
                "model": None,
                "serial": None,
                "firmware": None
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error accessing device information service: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))