from fastapi import APIRouter, HTTPException, Depends, Query, Body
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime
from backend.logging.logging_config import get_api_logger
from backend.modules.ble.ble_manager import BLEManager
from ..utils import handle_errors

# filepath: k:\anita\poc\backend\routes\api\alerts_routes.py
from backend.models import (
    ErrorResponse,
    SuccessResponse,
    StatusResponse
)

# Create API router for alerts
router = APIRouter(
    prefix="/api/alerts",
    tags=["alerts"],
    responses={
        404: {"description": "Not found"},
        500: {"description": "Internal server error", "model": ErrorResponse}
    }
)

logger = get_api_logger()
ble_manager = BLEManager(logger)

# In-memory alert storage for this example
# In a production environment, you would use a database
alerts = []
alert_id_counter = 0

# Alert types
ALERT_TYPES = {
    "ble_connect_failed": "BLE Connection Failed",
    "ble_disconnect": "BLE Device Disconnected",
    "ble_scan_error": "BLE Scan Error",
    "ble_read_error": "BLE Read Error",
    "ble_write_error": "BLE Write Error",
    "ble_service_not_found": "BLE Service Not Found",
    "ble_characteristic_not_found": "BLE Characteristic Not Found",
    "ble_permission_denied": "BLE Permission Denied",
    "ble_device_not_found": "BLE Device Not Found"
}

@router.get("/", response_model=List[Dict[str, Any]])
async def get_alerts(
    limit: int = Query(50, description="Maximum number of alerts to return"),
    offset: int = Query(0, description="Number of alerts to skip"),
    type: Optional[str] = Query(None, description="Filter by alert type"),
    acknowledged: Optional[bool] = Query(None, description="Filter by acknowledged status")
):
    """Get a list of system alerts with optional filtering"""
    try:
        filtered_alerts = alerts.copy()
        
        # Apply filters
        if type:
            filtered_alerts = [a for a in filtered_alerts if a["type"] == type]
        
        if acknowledged is not None:
            filtered_alerts = [a for a in filtered_alerts if a["acknowledged"] == acknowledged]
        
        # Apply pagination
        paginated_alerts = filtered_alerts[offset:offset + limit]
        
        return paginated_alerts
    except Exception as e:
        logger.error(f"Error retrieving alerts: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve alerts: {str(e)}")

@router.post("/", response_model=Dict[str, Any])
async def create_alert(
    alert_data: Dict[str, Any] = Body(...)
):
    """Create a new system alert"""
    try:
        global alert_id_counter
        alert_id_counter += 1
        
        # Validate alert type
        alert_type = alert_data.get("type")
        if alert_type not in ALERT_TYPES:
            raise HTTPException(status_code=400, detail=f"Invalid alert type: {alert_type}")
        
        # Create new alert
        new_alert = {
            "id": alert_id_counter,
            "type": alert_type,
            "title": alert_data.get("title", ALERT_TYPES[alert_type]),
            "message": alert_data.get("message", ""),
            "severity": alert_data.get("severity", "warning"),
            "timestamp": datetime.now().isoformat(),
            "source": alert_data.get("source", "system"),
            "acknowledged": False,
            "device_info": alert_data.get("device_info", {})
        }
        
        alerts.append(new_alert)
        logger.info(f"Alert created: {new_alert['title']}")
        
        return new_alert
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error creating alert: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create alert: {str(e)}")

@router.post("/{alert_id}/acknowledge", response_model=Dict[str, Any])
async def acknowledge_alert(alert_id: int):
    """Acknowledge an alert by ID"""
    try:
        # Find the alert
        alert = next((a for a in alerts if a["id"] == alert_id), None)
        if not alert:
            raise HTTPException(status_code=404, detail=f"Alert with ID {alert_id} not found")
        
        # Acknowledge the alert
        alert["acknowledged"] = True
        alert["acknowledged_at"] = datetime.now().isoformat()
        
        logger.info(f"Alert {alert_id} acknowledged")
        return alert
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error acknowledging alert: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to acknowledge alert: {str(e)}")

@router.delete("/{alert_id}", response_model=StatusResponse)
async def delete_alert(alert_id: int):
    """Delete an alert by ID"""
    try:
        # Find the alert
        alert_index = next((i for i, a in enumerate(alerts) if a["id"] == alert_id), None)
        if alert_index is None:
            raise HTTPException(status_code=404, detail=f"Alert with ID {alert_id} not found")
        
        # Remove the alert
        del alerts[alert_index]
        
        logger.info(f"Alert {alert_id} deleted")
        return {"status": "success", "message": f"Alert {alert_id} deleted successfully"}
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error deleting alert: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete alert: {str(e)}")

@router.post("/ble/connection-failed", response_model=Dict[str, Any])
async def ble_connection_failed_alert(
    alert_data: Dict[str, Any] = Body(...)
):
    """Create an alert for BLE connection failure"""
    try:
        device_address = alert_data.get("device_address", "Unknown")
        device_name = alert_data.get("device_name", "Unknown Device")
        error_message = alert_data.get("error_message", "Connection failed")
        
        alert_payload = {
            "type": "ble_connect_failed",
            "title": f"Failed to connect to BLE device: {device_name}",
            "message": error_message,
            "severity": "error",
            "source": "ble_manager",
            "device_info": {
                "address": device_address,
                "name": device_name
            }
        }
        
        return await create_alert(alert_payload)
    except Exception as e:
        logger.error(f"Error creating BLE connection failed alert: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create alert: {str(e)}")

@router.post("/ble/scan-error", response_model=Dict[str, Any])
async def ble_scan_error_alert(
    alert_data: Dict[str, Any] = Body(...)
):
    """Create an alert for BLE scan errors"""
    try:
        error_message = alert_data.get("error_message", "Scan failed")
        
        alert_payload = {
            "type": "ble_scan_error",
            "title": "BLE Scan Failed",
            "message": error_message,
            "severity": "warning",
            "source": "ble_manager"
        }
        
        return await create_alert(alert_payload)
    except Exception as e:
        logger.error(f"Error creating BLE scan error alert: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create alert: {str(e)}")

@router.get("/ble", response_model=List[Dict[str, Any]])
async def get_ble_alerts():
    """Get all BLE-related alerts"""
    try:
        ble_alert_types = [
            "ble_connect_failed", "ble_disconnect", "ble_scan_error",
            "ble_read_error", "ble_write_error", "ble_service_not_found",
            "ble_characteristic_not_found", "ble_permission_denied",
            "ble_device_not_found"
        ]
        
        ble_alerts = [a for a in alerts if a["type"] in ble_alert_types]
        return ble_alerts
    except Exception as e:
        logger.error(f"Error retrieving BLE alerts: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve BLE alerts: {str(e)}")