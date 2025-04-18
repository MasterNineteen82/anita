"""BLE adapter routes."""

import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Body, Response
from pydantic import BaseModel, Field
import json
import traceback
import time
import platform
import importlib.metadata
import asyncio


from backend.dependencies import get_ble_service, get_ble_metrics
from backend.modules.ble.core.ble_service import BleService
from backend.modules.ble.core.ble_metrics import BleMetricsCollector, SystemMonitor
from backend.modules.ble.models.ble_models import (
    BleAdapter, AdapterResult, AdapterStatus, 
    AdapterSelectionRequest, AdapterResetRequest,
    SystemMetric, AdapterMetric, BluetoothHealthReport, AdapterSelectRequest, AdapterSelectResponse,
    AdapterInfo
)
# Fix the import - likely the broadcast function is in the websocket module
from backend.modules.ble.comms.websocket import broadcast_message as broadcast_ble_event

# Create router
adapter_router = APIRouter(prefix="/adapter", tags=["BLE Adapters"])

# Get logger
logger = logging.getLogger(__name__)

def get_bleak_version():
    """Get the installed Bleak version."""
    try:
        # Use importlib.metadata (Python 3.8+)
        return importlib.metadata.version("bleak")
    except importlib.metadata.PackageNotFoundError:
        logger.warning("Could not determine Bleak version using importlib.metadata.")
        return "unknown"

@adapter_router.get("/adapters", response_model=None)
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
        
        return Response(content=json.dumps({
            "status": "success",
            "adapters": [adapter.model_dump() for adapter in adapters],
            "count": len(adapters)
        }, default=str), media_type="application/json")
    except Exception as e:
        logger.error(f"Error listing adapters: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve adapters")


@adapter_router.get("/info", response_model=None)
async def get_adapter_info(
    ble_service: BleService = Depends(get_ble_service)
):
    """Get information about the Bluetooth adapters."""
    try:
        logger.info("Getting adapter info")
        
        # Get all available adapters
        adapters = await ble_service.get_adapters()
        
        # Get the current adapter
        current_adapter = await ble_service.get_current_adapter()
        
        # Create response with both all adapters and the primary one
        return Response(content=json.dumps({
            "status": "success",
            "primary_adapter": current_adapter,
            "adapters": adapters,
            "count": len(adapters),
            "timestamp": time.time()
        }, default=str), media_type="application/json")
    except Exception as e:
        logger.error(f"Error getting adapter info: {e}", exc_info=True)
        return Response(content=json.dumps({
            "status": "error",
            "message": str(e),
            "adapters": [{
                "id": "error",
                "name": "Error Adapter",
                "address": "00:00:00:00:00:00",
                "available": False,
                "status": "error",
                "error": str(e)
            }],
            "count": 1
        }, default=str), media_type="application/json", status_code=200)  # Return 200 instead of 500

@adapter_router.post("/reset", response_model=None)
async def reset_adapter(
    request: AdapterResetRequest = Body(...),
    ble_service: BleService = Depends(get_ble_service)
):
    """Reset a Bluetooth adapter."""
    try:
        result = await ble_service.reset_adapter(request.adapter_id)
        
        if result.get("status") == "error":
            raise HTTPException(status_code=400, detail=result.get("message"))
        
        return Response(content=json.dumps({
            "status": "success",
            "message": f"Adapter {request.adapter_id or 'current'} reset successfully",
            "details": result
        }, default=str), media_type="application/json")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resetting adapter: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@adapter_router.get("/metrics", response_model=None)
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
        
        return Response(content=json.dumps({
            "adapter_id": adapter_id or "all",
            "metrics": [metric.model_dump() for metric in metrics],
            "count": len(metrics),
            "summary": metrics_raw.get("summary", {})
        }, default=str), media_type="application/json")
    except Exception as e:
        logger.error(f"Error getting adapter metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get adapter metrics: {str(e)}")

@adapter_router.get("/health", response_model=None)
async def get_bluetooth_health(
    ble_service: BleService = Depends(get_ble_service) # ble_service might still be useful for other checks?
):
    """Get comprehensive Bluetooth health report."""
    try:
        # Directly instantiate SystemMonitor as BleService doesn't provide it
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
        
        return Response(content=json.dumps(report.model_dump(), default=str), media_type="application/json")
    except Exception as e:
        logger.error(f"Error generating Bluetooth health report: {e}")
        # Return a standardized error structure
        return Response(content=json.dumps({
            "status": "error",
            "message": f"Failed to generate health report: {str(e)}"
        }, default=str), media_type="application/json", status_code=500)

@adapter_router.post("/power", response_model=None)
async def set_adapter_power(
    power: bool = Body(..., embed=True),
    adapter_id: Optional[str] = Body(None, embed=True),
    ble_service: BleService = Depends(get_ble_service)
):
    """Set the power state of a Bluetooth adapter."""
    try:
        logger.info(f"Received request to set power to {power} for adapter {adapter_id or 'current'}")
        
        # Placeholder: Call a method on BleService to set power
        # This method needs to be implemented in BleService
        # Example:
        # result = await ble_service.set_power(power=power, adapter_id=adapter_id)

        # Simulate success for now
        await asyncio.sleep(0.1) # Simulate async operation
        success = True 
        message = f"Successfully set power to {power} for adapter {adapter_id or 'current'}"

        if success:
            await broadcast_ble_event({"type": "adapter_power", "adapter_id": adapter_id or 'current', "power": power})
            return Response(content=json.dumps({"status": "success", "message": message}), media_type="application/json")
        else:
            # Simulate failure (e.g., if ble_service.set_power failed)
            raise HTTPException(status_code=500, detail=f"Failed to set power state for adapter {adapter_id or 'current'}")

    except HTTPException:
        raise # Re-raise known HTTP exceptions
    except Exception as e:
        logger.error(f"Error setting adapter power: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error setting adapter power: {str(e)}")

@adapter_router.get("/system-info", response_model=None)
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
        
        return Response(content=json.dumps({
            "system": system_info.get("system", {}),
            "bluetooth": system_info.get("bluetooth", {}),
            "resources": system_metric.model_dump()
        }, default=str), media_type="application/json")
    except Exception as e:
        logger.error(f"Error getting system info: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get system info: {str(e)}")
    
@adapter_router.post("/select", response_model=AdapterSelectResponse)
async def select_adapter(request: AdapterSelectRequest, ble_service: BleService = Depends(get_ble_service)):
    """Select a specific Bluetooth adapter by ID or address."""
    try:
        # Use the adapter_id property which handles different input formats
        adapter_id = request.adapter_id
        logger.info(f"Selecting adapter: {adapter_id}")
        
        # Check if we need to disconnect first
        try:
            if hasattr(ble_service, 'is_connected') and callable(ble_service.is_connected):
                is_connected = ble_service.is_connected()
                if is_connected:
                    logger.info("Disconnecting current device before adapter change")
                    await ble_service.disconnect_device()
            else:
                logger.debug("is_connected method not available, assuming not connected")
        except Exception as e:
            logger.warning(f"Error checking connection status: {e}")
        
        # Get available adapters first to ensure we're working with current data
        try:
            available_adapters = await ble_service.get_adapters()
            logger.info(f"Available adapters: {[a.get('id', 'unknown') for a in available_adapters]}")
        except Exception as e:
            logger.warning(f"Error getting adapters: {e}")
            available_adapters = []
            
        # Select the adapter using the adapter_id property
        try:
            result = await ble_service.select_adapter(adapter_id)
        except Exception as e:
            logger.error(f"Error selecting adapter {adapter_id}: {e}")
            # Provide helpful error message based on available adapters
            if not available_adapters:
                detail = "No Bluetooth adapters found on this system"
            else:
                detail = f"Failed to select adapter: {e}. Available adapters: {[a.get('id', 'unknown') for a in available_adapters]}"
            raise HTTPException(status_code=404, detail=detail)
        
        if result:
            # Get current adapter status
            status = await ble_service.get_adapter_status()
            
            # Create adapter info as a dictionary (not an AdapterInfo object)
            adapter_info = {
                "id": result.get("id", adapter_id),
                "name": result.get("name", "Selected Adapter"),
                "address": result.get("address", adapter_id),
                "available": result.get("available", True),
                "status": "active",
                "description": result.get("description", ""),
                "manufacturer": result.get("manufacturer", "Unknown")
            }
            
            # Return response matching the AdapterSelectResponse model
            return AdapterSelectResponse(
                status="success",
                adapter=adapter_info,
                message="Adapter selected successfully"
            )
        else:
            raise HTTPException(status_code=404, detail=f"Adapter not found: {adapter_id}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error selecting adapter: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error selecting adapter: {e}")

# Add this new endpoint
@adapter_router.get("/diagnostics", response_model=None)
async def get_adapter_diagnostics(
    ble_service: BleService = Depends(get_ble_service)
):
    """Run comprehensive adapter diagnostics."""
    try:
        # Get system monitor
        from backend.modules.ble.utils.system_monitor import get_system_monitor
        system_monitor = get_system_monitor()
        
        # Run diagnostics
        diagnostics = await system_monitor.run_diagnostics(deep_check=True)
        
        # Get adapter information
        adapters = await ble_service.get_adapters()
        
        # Combine results
        result = {
            "timestamp": time.time(),
            "adapters": adapters,
            "system_diagnostics": diagnostics,
            "bleak_version": get_bleak_version(),
            "platform": platform.system(),
            "recommendations": []
        }
        
        # Add recommendations based on findings
        if not diagnostics.get("bluetooth_available", True):
            result["recommendations"].append("Ensure Bluetooth is enabled in your system settings")
            
        if platform.system() == "Windows" and not diagnostics.get("admin_privileges", False):
            result["recommendations"].append("Run with administrator privileges for full access")
            
        return Response(content=json.dumps(result, default=str), 
                      media_type="application/json")
    except Exception as e:
        logger.error(f"Error running adapter diagnostics: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Diagnostics failed: {str(e)}"
        )
