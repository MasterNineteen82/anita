"""Bluetooth health and diagnostic routes.

This module provides routes for health monitoring and diagnostics of the BLE system:
- Health reports and system status
- BLE stack information
- Metrics collection and retrieval
- System diagnostics and troubleshooting tools
"""

import logging
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from pydantic import BaseModel, Field

from backend.dependencies import get_ble_service, get_ble_metrics
from backend.modules.ble.core.ble_service import BleService
from backend.modules.ble.core.ble_metrics import BleMetricsCollector, SystemMonitor
from backend.modules.ble.models.ble_models import (
    BluetoothHealthReport, SystemMetric, DiagnosticRequest, 
    DiagnosticResult, MetricsResponse, StackInfo, ResetResponse
)

# Create router
health_router = APIRouter(prefix="/health", tags=["BLE Health & Diagnostics"])

# Get logger
logger = logging.getLogger(__name__)

@health_router.get("/report", response_model=BluetoothHealthReport)
async def get_health_report(
    ble_service: BleService = Depends(get_ble_service),
    ble_metrics: BleMetricsCollector = Depends(get_ble_metrics)
):
    """
    Get a comprehensive health report for BLE functionality.
    
    Provides a detailed assessment of the Bluetooth system, including:
    - Adapter status
    - Connection information
    - System resources
    - Operation metrics
    - Warnings and recommendations
    
    Returns:
        BluetoothHealthReport: Comprehensive health information
    """
    try:
        # Get the system monitor
        system_monitor = ble_metrics.system_monitor if hasattr(ble_metrics, "system_monitor") else None
        
        if not system_monitor:
            system_monitor = SystemMonitor()
        
        # Generate health report
        report_raw = await system_monitor.get_bluetooth_health_report()
        
        # Add BLE manager status
        ble_manager_status = {
            "connected": ble_service.is_connected(),
            "device": ble_service.get_connected_device_address() if ble_service.is_connected() else None,
            "connection_uptime": ble_service.get_connection_uptime() if ble_service.is_connected() else None,
        }
        
        # Try to get adapter info
        try:
            adapter_info = await ble_service.get_adapter_info()
            ble_manager_status["adapter"] = adapter_info
        except Exception as adapter_err:
            logger.warning(f"Error getting adapter info: {adapter_err}")
            ble_manager_status["adapter_error"] = str(adapter_err)
        
        # Add metrics summary if available
        metrics_summary = {}
        if hasattr(ble_metrics, "get_metrics_summary"):
            metrics_summary = ble_metrics.get_metrics_summary()
        
        # Create the model with all data
        report = BluetoothHealthReport(
            timestamp=report_raw.get("timestamp"),
            adapter_status=report_raw.get("adapter_status", {}),
            system_resources=report_raw.get("system_resources", {}),
            ble_operations=report_raw.get("ble_operations", {}),
            connection_status=ble_manager_status,
            metrics=metrics_summary,
            errors=report_raw.get("errors", []),
            warnings=report_raw.get("warnings", []),
            recommendations=report_raw.get("recommendations", [])
        )
        
        return report
    except Exception as e:
        logger.error(f"Error generating health report: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@health_router.get("/stack", response_model=StackInfo)
async def get_bluetooth_stack_info(ble_service: BleService = Depends(get_ble_service)):
    """
    Get information about the Bluetooth stack.
    
    Returns details about the Bluetooth stack implementation being used:
    - Driver information
    - Library versions
    - Backend details
    - Platform-specific information
    
    Returns:
        StackInfo: Information about the Bluetooth stack
    """
    try:
        stack_info_raw = await ble_service.get_bluetooth_stack_info()
        
        # Convert to Pydantic model
        stack_info = StackInfo(
            platform=stack_info_raw.get("platform", {}),
            bleak_version=stack_info_raw.get("bleak_version"),
            backend=stack_info_raw.get("backend"),
            driver_info=stack_info_raw.get("driver_info", {}),
            system_libraries=stack_info_raw.get("system_libraries", {}),
            capabilities=stack_info_raw.get("capabilities", [])
        )
        
        return stack_info
    except Exception as e:
        logger.error(f"Error getting Bluetooth stack info: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@health_router.post("/reset", response_model=ResetResponse)
async def reset_bluetooth(ble_service: BleService = Depends(get_ble_service)):
    """
    Attempt to reset the Bluetooth stack.
    
    This will attempt to reset the Bluetooth system, which may help resolve issues.
    Warning: This will disconnect any connected devices and might
    temporarily disrupt Bluetooth functionality.
    
    Returns:
        ResetResponse: Result of the reset operation
    """
    try:
        reset_result_raw = await ble_service.reset_bluetooth()
        
        # Convert to Pydantic model
        reset_result = ResetResponse(
            success=reset_result_raw.get("success", False),
            message=reset_result_raw.get("message", ""),
            adapter_status=reset_result_raw.get("adapter_status", {}),
            error=reset_result_raw.get("error"),
            actions_taken=reset_result_raw.get("actions_taken", [])
        )
        
        return reset_result
    except Exception as e:
        logger.error(f"Error resetting Bluetooth: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@health_router.get("/metrics", response_model=MetricsResponse)
async def get_ble_metrics(
    metric_type: Optional[str] = Query(None, description="Type of metrics to retrieve (operations, devices, adapters, all)"),
    limit: int = Query(100, description="Maximum number of metrics to return"),
    ble_metrics: BleMetricsCollector = Depends(get_ble_metrics)
):
    """
    Get BLE operation metrics.
    
    Retrieves performance and usage metrics for various aspects of the BLE system.
    Can be filtered by metric type.
    
    Parameters:
        - metric_type: Type of metrics to retrieve (operations, devices, adapters, all)
        - limit: Maximum number of metrics to return per category
    
    Returns:
        MetricsResponse: Collected metrics data
    """
    try:
        metrics_raw = {}
        
        if not metric_type or metric_type == "all":
            metrics_raw = ble_metrics.get_all_metrics(limit=limit)
        elif metric_type == "operations":
            metrics_raw = ble_metrics.get_operation_metrics(limit=limit)
        elif metric_type == "devices":
            metrics_raw = ble_metrics.get_device_metrics(limit=limit)
        elif metric_type == "adapters":
            metrics_raw = ble_metrics.get_adapter_metrics(limit=limit)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown metric type: {metric_type}")
        
        # Create metrics response model
        metrics_response = MetricsResponse(
            metric_type=metric_type or "all",
            operation_metrics=metrics_raw.get("operations", []),
            device_metrics=metrics_raw.get("devices", []),
            adapter_metrics=metrics_raw.get("adapters", []),
            system_metrics=metrics_raw.get("system", []),
            counts={
                "operations": len(metrics_raw.get("operations", [])),
                "devices": len(metrics_raw.get("devices", [])),
                "adapters": len(metrics_raw.get("adapters", [])),
                "system": len(metrics_raw.get("system", []))
            },
            summary=metrics_raw.get("summary", {})
        )
        
        return metrics_response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting BLE metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@health_router.post("/diagnostics", response_model=DiagnosticResult)
async def run_diagnostics(
    request: DiagnosticRequest = None,
    ble_service: BleService = Depends(get_ble_service)
):
    """
    Run diagnostics on the BLE subsystem.
    
    Performs a series of diagnostic tests on the BLE system to identify issues.
    Options can be provided to customize the diagnostic tests.
    
    Parameters:
        - request: Optional configuration for the diagnostics
    
    Returns:
        DiagnosticResult: Results of the diagnostic tests
    """
    try:
        # If no request object provided, create a default one
        if not request:
            request = DiagnosticRequest()
        
        # Run diagnostics with options from request
        diagnostics_raw = await ble_service.run_diagnostics(
            check_adapter=request.check_adapter,
            test_scan=request.test_scan,
            scan_duration=request.scan_duration,
            deep_hardware_check=request.deep_hardware_check,
            check_system=request.check_system
        )
        
        # Create diagnostic result model
        diagnostics_result = DiagnosticResult(
            timestamp=diagnostics_raw.get("timestamp"),
            success=diagnostics_raw.get("success", False),
            tests=diagnostics_raw.get("tests", []),
            issues=diagnostics_raw.get("issues", []),
            hardware_status=diagnostics_raw.get("hardware_status", {}),
            stack_status=diagnostics_raw.get("stack_status", {}),
            recommendations=diagnostics_raw.get("recommendations", [])
        )
        
        return diagnostics_result
    except Exception as e:
        logger.error(f"Error running diagnostics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@health_router.get("/system")
async def get_system_metrics(ble_metrics: BleMetricsCollector = Depends(get_ble_metrics)):
    """
    Get system resource metrics.
    
    Retrieves information about system resources:
    - CPU usage
    - Memory usage
    - Disk usage
    - Network activity
    
    Returns:
        SystemMetric: Current system resource usage
    """
    try:
        system_monitor = ble_metrics.system_monitor if hasattr(ble_metrics, "system_monitor") else None
        
        if not system_monitor:
            system_monitor = SystemMonitor()
        
        # Get system metrics
        metrics_raw = await system_monitor.get_system_metrics()
        
        # Convert to Pydantic model
        system_metric = SystemMetric(
            timestamp=metrics_raw.get("timestamp"),
            cpu_percent=metrics_raw.get("cpu_percent"),
            memory_percent=metrics_raw.get("memory_percent"),
            disk_percent=metrics_raw.get("disk_percent"),
            network_sent=metrics_raw.get("network_sent"),
            network_recv=metrics_raw.get("network_recv")
        )
        
        return system_metric
    except Exception as e:
        logger.error(f"Error getting system metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@health_router.post("/clear-metrics")
async def clear_metrics(
    metric_type: Optional[str] = Query(None, description="Type of metrics to clear (operations, devices, adapters, all)"),
    ble_metrics: BleMetricsCollector = Depends(get_ble_metrics)
):
    """
    Clear collected metrics.
    
    Removes stored metrics data. Can be filtered by metric type.
    
    Parameters:
        - metric_type: Type of metrics to clear (operations, devices, adapters, all)
    
    Returns:
        Status message
    """
    try:
        if not metric_type or metric_type == "all":
            ble_metrics.clear_all_metrics()
            message = "All metrics cleared"
        elif metric_type == "operations":
            ble_metrics.clear_operation_metrics()
            message = "Operation metrics cleared"
        elif metric_type == "devices":
            ble_metrics.clear_device_metrics()
            message = "Device metrics cleared"
        elif metric_type == "adapters":
            ble_metrics.clear_adapter_metrics()
            message = "Adapter metrics cleared"
        else:
            raise HTTPException(status_code=400, detail=f"Unknown metric type: {metric_type}")
        
        return {
            "status": "success",
            "message": message
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error clearing metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))