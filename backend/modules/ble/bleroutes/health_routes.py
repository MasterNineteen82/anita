"""Bluetooth health and diagnostic routes."""

import logging
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query

from backend.dependencies import get_ble_service, get_ble_metrics
from backend.modules.ble.ble_service import BleService
from backend.modules.ble.ble_metrics import BleMetricsCollector, SystemMonitor

# Create router
health_router = APIRouter(prefix="/health", tags=["BLE Health & Diagnostics"])

# Get logger
logger = logging.getLogger(__name__)

@health_router.get("/report")
async def get_health_report(
    ble_service: BleService = Depends(get_ble_service),
    ble_metrics: BleMetricsCollector = Depends(get_ble_metrics)
):
    """Get a comprehensive health report for BLE functionality."""
    try:
        # Get the system monitor
        system_monitor = ble_metrics.system_monitor if hasattr(ble_metrics, "system_monitor") else None
        
        if not system_monitor:
            system_monitor = SystemMonitor()
        
        # Generate health report
        report = system_monitor.get_bluetooth_health_report()
        
        # Add BLE manager status
        report["ble_manager"] = {
            "connected": ble_service.is_connected(),
            "device": ble_service.get_connected_device_address() if ble_service.is_connected() else None,
            "connection_uptime": ble_service.get_connection_uptime() if ble_service.is_connected() else None,
            "adapter": await ble_service.get_adapter_info()
        }
        
        # Add metrics summary
        if hasattr(ble_metrics, "get_metrics_summary"):
            report["metrics"] = ble_metrics.get_metrics_summary()
        
        return report
    except Exception as e:
        logger.error(f"Error generating health report: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@health_router.get("/stack")
async def get_bluetooth_stack_info(ble_service: BleService = Depends(get_ble_service)):
    """Get information about the Bluetooth stack."""
    try:
        stack_info = await ble_service.get_bluetooth_stack_info()
        return stack_info
    except Exception as e:
        logger.error(f"Error getting Bluetooth stack info: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@health_router.post("/reset")
async def reset_bluetooth(ble_service: BleService = Depends(get_ble_service)):
    """Attempt to reset the Bluetooth stack."""
    try:
        reset_result = await ble_service.reset_bluetooth()
        return reset_result
    except Exception as e:
        logger.error(f"Error resetting Bluetooth: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@health_router.get("/metrics")
async def get_ble_metrics(
    metric_type: Optional[str] = Query(None, description="Type of metrics to retrieve (operations, devices, adapters, all)"),
    ble_metrics: BleMetricsCollector = Depends(get_ble_metrics)
):
    """Get BLE operation metrics."""
    try:
        if not metric_type or metric_type == "all":
            return ble_metrics.get_all_metrics()
        elif metric_type == "operations":
            return ble_metrics.get_operation_metrics()
        elif metric_type == "devices":
            return ble_metrics.get_device_metrics()
        elif metric_type == "adapters":
            return ble_metrics.get_adapter_metrics()
        else:
            raise HTTPException(status_code=400, detail=f"Unknown metric type: {metric_type}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting BLE metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@health_router.post("/diagnostics")
async def run_diagnostics(ble_service: BleService = Depends(get_ble_service)):
    """Run diagnostics on the BLE subsystem."""
    try:
        diagnostics_results = await ble_service.run_diagnostics()
        return diagnostics_results
    except Exception as e:
        logger.error(f"Error running diagnostics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))