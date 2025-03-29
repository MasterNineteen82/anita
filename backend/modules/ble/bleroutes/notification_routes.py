"""Bluetooth notification-related routes."""

import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Path, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from backend.dependencies import get_ble_service
from backend.modules.ble.ble_service import BleService

# Create router
notification_router = APIRouter(prefix="/notification", tags=["BLE Notifications"])

# Get logger
logger = logging.getLogger(__name__)

class NotificationRequest(BaseModel):
    characteristic: str
    enable: bool = True

@notification_router.post("/subscribe")
async def subscribe_to_notifications(
    request: NotificationRequest,
    ble_service: BleService = Depends(get_ble_service)
):
    """Subscribe to notifications from a characteristic."""
    try:
        if not ble_service.is_connected():
            raise HTTPException(status_code=400, detail="No device connected")
        
        if request.enable:
            # Start notifications
            success = await ble_service.start_notify(request.characteristic)
            if success:
                return {
                    "status": "subscribed",
                    "characteristic": request.characteristic
                }
            else:
                raise HTTPException(status_code=400, detail="Failed to subscribe to notifications")
        else:
            # Stop notifications
            success = await ble_service.stop_notify(request.characteristic)
            if success:
                return {
                    "status": "unsubscribed",
                    "characteristic": request.characteristic
                }
            else:
                raise HTTPException(status_code=400, detail="Failed to unsubscribe from notifications")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error with notification subscription: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@notification_router.get("/active")
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

@notification_router.get("/history")
async def get_notification_history(
    characteristic: Optional[str] = None,
    ble_service: BleService = Depends(get_ble_service)
):
    """Get notification history."""
    try:
        if not ble_service.is_connected():
            raise HTTPException(status_code=400, detail="No device connected")
        
        history = ble_service.get_notification_history(characteristic)
        return history
    except Exception as e:
        logger.error(f"Error getting notification history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@notification_router.delete("/history")
async def clear_notification_history(
    characteristic: Optional[str] = None,
    ble_service: BleService = Depends(get_ble_service)
):
    """Clear notification history."""
    try:
        if not ble_service.is_connected():
            raise HTTPException(status_code=400, detail="No device connected")
        
        ble_service.clear_notification_history(characteristic)
        return {"status": "success", "message": "Notification history cleared"}
    except Exception as e:
        logger.error(f"Error clearing notification history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@notification_router.websocket("/ws")
async def notification_websocket(websocket: WebSocket, ble_service: BleService = Depends(get_ble_service)):
    """WebSocket endpoint for receiving notifications in real-time."""
    await websocket.accept()
    
    try:
        # Register WebSocket
        ble_service.register_notification_websocket(websocket)
        
        # Keep connection open and handle client messages
        while True:
            # Wait for client messages (subscription requests)
            data = await websocket.receive_json()
            
            if "subscribe" in data:
                char_uuid = data["subscribe"]
                if isinstance(char_uuid, str):
                    # Client wants to subscribe to notifications
                    success = await ble_service.start_notify(char_uuid)
                    await websocket.send_json({
                        "type": "subscription",
                        "status": "subscribed" if success else "failed",
                        "characteristic": char_uuid
                    })
            
            elif "unsubscribe" in data:
                char_uuid = data["unsubscribe"]
                if isinstance(char_uuid, str):
                    # Client wants to unsubscribe from notifications
                    success = await ble_service.stop_notify(char_uuid)
                    await websocket.send_json({
                        "type": "subscription",
                        "status": "unsubscribed" if success else "failed",
                        "characteristic": char_uuid
                    })
    
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e)
            })
        except:
            pass
    finally:
        # Unregister WebSocket
        ble_service.unregister_notification_websocket(websocket)