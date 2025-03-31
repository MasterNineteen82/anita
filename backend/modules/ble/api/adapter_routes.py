"""Bluetooth adapter-related routes."""

import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel, Field

from backend.dependencies import get_ble_service, get_ble_metrics
from backend.modules.ble.core.ble_service import BleService
from backend.modules.ble.core.ble_metrics import BleMetricsCollector, SystemMonitor
from backend.modules.ble.models.ble_models import (
    BleAdapter, AdapterResult, AdapterStatus, 
    AdapterSelectionRequest, AdapterResetRequest,
    SystemMetric, AdapterMetric, BluetoothHealthReport
)

# Create router
adapter_router = APIRouter(prefix="/adapter", tags=["BLE Adapters"])

# Get logger
logger = logging.getLogger(__name__)

@adapter_router.get("/adapters")
async def list_adapters(ble_service: BleService = Depends(get_ble_service)):
    """Get a list of all Bluetooth adapters on the system."""
    try:
        adapters_raw = await ble_service.get_adapters()
        
        # Convert to Pydantic models
        adapters = []
        for adapter in adapters_raw:
            adapter_model = BleAdapter(
                id=adapter.get("id", "unknown"),
                name=adapter.get("name", "Unknown Adapter"),
                available=adapter.get("available", False),
                status=adapter.get("status"),
                error=adapter.get("error"),
                system=adapter.get("system"),
                version=adapter.get("version")
            )
            adapters.append(adapter_model)
        
        result = AdapterResult(adapters=adapters)
        
        return {
            "status": "success",
            "adapters": [adapter.dict() for adapter in adapters],
            "count": len(adapters)
        }
    except Exception as e:
        logger.error(f"Error listing adapters: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve adapters")

@adapter_router.get("/info")
async def get_adapter_info(ble_service: BleService = Depends(get_ble_service)):
    """Get information about the current Bluetooth adapter."""
    try:
        adapter_info_raw = await ble_service.get_adapter_info()
        
        # Convert to Pydantic model
        adapter_info = BleAdapter(
            id=adapter_info_raw.get("id", "unknown"),
            name=adapter_info_raw.get("name", "Unknown Adapter"),
            available=adapter_info_raw.get("available", False),
            status=adapter_info_raw.get("status"),
            error=adapter_info_raw.get("error"),
            system=adapter_info_raw.get("system"),
            version=adapter_info_raw.get("version")
        )
        
        return adapter_info.dict()
    except Exception as e:
        logger.error(f"Error getting adapter info: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@adapter_router.post("/select")
async def select_adapter(
    request: AdapterSelectionRequest = Body(...),
    ble_service: BleService = Depends(get_ble_service)
):
    """Select a specific Bluetooth adapter for use."""
    try:
        # Get the adapter ID
        adapter_id = request.id
        
        if not adapter_id:
            raise HTTPException(status_code=400, detail="Missing adapter ID")
        
        result = await ble_service.select_adapter(adapter_id)
        
        if result.get("status") == "error":
            raise HTTPException(status_code=400, detail=result.get("message"))
        
        # Convert to Pydantic model
        adapter_info = BleAdapter(
            id=result.get("id", adapter_id),
            name=result.get("name", "Unknown Adapter"),
            available=result.get("available", True),
            status=result.get("status", "selected"),
            error=result.get("error")
        )
        
        return {
            "status": "success",
            "message": f"Adapter {adapter_id} selected",
            "adapter": adapter_info.dict()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error selecting adapter: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@adapter_router.post("/reset")
async def reset_adapter(
    request: AdapterResetRequest = Body(...),
    ble_service: BleService = Depends(get_ble_service)
):
    """Reset a Bluetooth adapter."""
    try:
        result = await ble_service.reset_adapter(request.adapter_id)
        
        if result.get("status") == "error":
            raise HTTPException(status_code=400, detail=result.get("message"))
        
        return {
            "status": "success",
            "message": f"Adapter {request.adapter_id or 'current'} reset successfully",
            "details": result
        }
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
        metrics_raw = ble_metrics.get_adapter_metrics(adapter_id)
        
        # Convert raw metrics to Pydantic models
        metrics = []
        for metric in metrics_raw.get("metrics", []):
            adapter_metric = AdapterMetric(
                adapter_id=metric.get("adapter_id", "unknown"),
                operation=metric.get("operation", "unknown"),
                success=metric.get("success", False),
                timestamp=metric.get("timestamp"),
                duration=metric.get("duration"),
                details=metric.get("details", {})
            )
            metrics.append(adapter_metric)
        
        return {
            "adapter_id": adapter_id or "all",
            "metrics": [metric.dict() for metric in metrics],
            "count": len(metrics),
            "summary": metrics_raw.get("summary", {})
        }
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
            from backend.modules.ble.core.ble_metrics import SystemMonitor
            system_monitor = SystemMonitor()
        
        report_raw = await system_monitor.get_bluetooth_health_report()
        
        # Convert to Pydantic model
        report = BluetoothHealthReport(
            timestamp=report_raw.get("timestamp"),
            adapter_status=report_raw.get("adapter_status", {}),
            system_resources=report_raw.get("system_resources", {}),
            ble_operations=report_raw.get("ble_operations", {}),
            connection_status=report_raw.get("connection_status", {}),
            errors=report_raw.get("errors", []),
            warnings=report_raw.get("warnings", []),
            recommendations=report_raw.get("recommendations", [])
        )
        
        return report.dict()
    except Exception as e:
        logger.error(f"Error generating Bluetooth health report: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate health report: {str(e)}")

@adapter_router.post("/power/{state}")
async def set_adapter_power(
    state: str,
    adapter_id: Optional[str] = None,
    ble_service: BleService = Depends(get_ble_service)
):
    """Turn adapter on or off."""
    try:
        if state not in ["on", "off"]:
            raise HTTPException(status_code=400, detail="State must be 'on' or 'off'")
        
        power_on = (state == "on")
        result = await ble_service.set_adapter_power(power_on, adapter_id)
        
        if result.get("success"):
            return {
                "status": "success",
                "message": f"Adapter power set to {state}",
                "adapter_id": adapter_id or "current"
            }
        else:
            raise HTTPException(
                status_code=400, 
                detail=result.get("error", f"Failed to set adapter power to {state}")
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting adapter power: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@adapter_router.get("/system-info")
async def get_system_info(ble_service: BleService = Depends(get_ble_service)):
    """Get system information related to Bluetooth."""
    try:
        system_monitor = ble_service.get_system_monitor()
        if not system_monitor:
            from backend.modules.ble.core.ble_metrics import SystemMonitor
            system_monitor = SystemMonitor()
        
        system_info = await system_monitor.get_system_info()
        
        # Convert to a Pydantic model
        system_metric = SystemMetric(
            timestamp=system_info.get("timestamp"),
            cpu_percent=system_info.get("cpu_percent"),
            memory_percent=system_info.get("memory_percent"),
            disk_percent=system_info.get("disk_percent"),
            network_sent=system_info.get("network_sent"),
            network_recv=system_info.get("network_recv")
        )
        
        return {
            "system": system_info.get("system", {}),
            "bluetooth": system_info.get("bluetooth", {}),
            "resources": system_metric.dict()
        }
    except Exception as e:
        logger.error(f"Error getting system info: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get system info: {str(e)}")