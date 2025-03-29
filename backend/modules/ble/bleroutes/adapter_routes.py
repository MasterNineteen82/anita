"""Bluetooth adapter-related routes."""

import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException

from backend.dependencies import get_ble_service, get_ble_metrics
from backend.modules.ble.ble_service import BleService
from backend.modules.ble.ble_metrics import BleMetricsCollector, SystemMonitor

# Create router
adapter_router = APIRouter(prefix="/adapter", tags=["BLE Adapters"])

# Get logger
logger = logging.getLogger(__name__)

@adapter_router.get("/list")
async def list_adapters(ble_service: BleService = Depends(get_ble_service)):
    """Get a list of all Bluetooth adapters on the system."""
    try:
        adapters = await ble_service.get_adapters()
        return {
            "status": "success",
            "adapters": adapters,
            "count": len(adapters)
        }
    except Exception as e:
        logger.error(f"Error listing adapters: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@adapter_router.get("/info")
async def get_adapter_info(ble_service: BleService = Depends(get_ble_service)):
    """Get information about the current Bluetooth adapter."""
    try:
        adapter_info = await ble_service.get_adapter_info()
        return adapter_info
    except Exception as e:
        logger.error(f"Error getting adapter info: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@adapter_router.post("/select")
async def select_adapter(adapter: dict, ble_service: BleService = Depends(get_ble_service)):
    """Select a specific Bluetooth adapter for use."""
    try:
        if not adapter:
            raise HTTPException(status_code=400, detail="Missing adapter information")
        
        # Get the adapter ID - could be device_id, address, or index
        adapter_id = adapter.get("id") or adapter.get("device_id") or adapter.get("address")
        
        if not adapter_id:
            raise HTTPException(status_code=400, detail="Missing adapter ID")
        
        result = await ble_service.select_adapter(adapter_id)
        
        if result.get("status") == "error":
            raise HTTPException(status_code=400, detail=result.get("message"))
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error selecting adapter: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@adapter_router.post("/reset")
async def reset_adapter(
    adapter_id: Optional[str] = None, 
    ble_service: BleService = Depends(get_ble_service)
):
    """Reset a Bluetooth adapter."""
    try:
        result = await ble_service.reset_adapter(adapter_id)
        
        if result.get("status") == "error":
            raise HTTPException(status_code=400, detail=result.get("message"))
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resetting adapter: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@adapter_router.get("/metrics")
async def get_adapter_metrics(
    adapter_id: Optional[str] = None,
    ble_metrics: BleMetricsCollector = Depends(get_ble_metrics)
):
    """Get metrics for a specific adapter or all adapters."""
    try:
        metrics = ble_metrics.get_adapter_metrics(adapter_id)
        return metrics
    except Exception as e:
        logger.error(f"Error getting adapter metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get adapter metrics: {str(e)}")

@adapter_router.get("/health")
async def get_bluetooth_health(
    ble_service: BleService = Depends(get_ble_service)
):
    """Get comprehensive Bluetooth health report."""
    try:
        system_monitor = ble_service.get_system_monitor()
        if not system_monitor:
            from backend.modules.ble.ble_metrics import SystemMonitor
            system_monitor = SystemMonitor()
        
        report = await system_monitor.get_bluetooth_health_report()
        return report
    except Exception as e:
        logger.error(f"Error generating Bluetooth health report: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate health report: {str(e)}")