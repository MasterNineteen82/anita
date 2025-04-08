"""Bluetooth notification-related routes.

This module provides API endpoints for managing BLE characteristic notifications:
- Subscribe/unsubscribe to characteristic notifications
- View active notifications
- Access notification history
- Real-time notifications via WebSocket
"""

import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Body, Path, WebSocket, WebSocketDisconnect, Response
import json

from backend.modules.ble.core.ble_service_factory import get_ble_service
from backend.modules.ble.core.ble_service import BleService
from backend.modules.ble.comms import websocket_manager
from backend.modules.ble.models.ble_models import (
    NotificationRequest, NotificationSubscription, NotificationsResult,
    CharacteristicValue, NotificationHistory, NotificationEvent, MessageType
)

# Create router
notification_router = APIRouter(prefix="/notification", tags=["BLE Notifications"])

# Get logger
logger = logging.getLogger(__name__)

@notification_router.post("/subscribe", response_model=None)
async def subscribe_to_characteristic(
    request: NotificationRequest,
    ble_service: BleService = Depends(get_ble_service)
):
    """
    Subscribe to notifications for a characteristic.
    
    This starts notification delivery for the specified characteristic.
    Notifications can be received either via polling the history endpoint
    or via the WebSocket endpoint.
    
    Parameters:
        - characteristic: UUID of the characteristic to subscribe to
        - enable: Whether to enable (true) or disable (false) notifications
    
    Returns:
        Object with status information
    """
    try:
        if not ble_service.is_connected():
            raise HTTPException(status_code=400, detail="No device connected")
        
        result = await ble_service.subscribe_to_characteristic(
            characteristic_uuid=request.characteristic,
            enable=request.enable
        )
        
        return Response(content=json.dumps({
            "status": "success" if result else "error",
            "characteristic": request.characteristic,
            "subscribed": result
        }, default=str), media_type="application/json")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error subscribing to characteristic: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@notification_router.post("/unsubscribe", response_model=None)
async def unsubscribe_from_characteristic(
    request: NotificationRequest,
    ble_service: BleService = Depends(get_ble_service)
):
    """
    Unsubscribe from notifications for a characteristic.
    
    This stops notification delivery for the specified characteristic.
    
    Parameters:
        - characteristic: UUID of the characteristic to unsubscribe from
    
    Returns:
        Object with status information
    """
    try:
        if not ble_service.is_connected():
            raise HTTPException(status_code=400, detail="No device connected")
        
        # Set enable to false to unsubscribe
        request_data = request.dict()
        request_data["enable"] = False
        unsubscribe_request = NotificationRequest(**request_data)
        
        result = await ble_service.subscribe_to_characteristic(
            characteristic_uuid=unsubscribe_request.characteristic,
            enable=False
        )
        
        return Response(content=json.dumps({
            "status": "success" if result else "error",
            "characteristic": unsubscribe_request.characteristic,
            "unsubscribed": result
        }, default=str), media_type="application/json")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error unsubscribing from characteristic: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@notification_router.get("/active", response_model=None)
async def get_active_notifications(ble_service: BleService = Depends(get_ble_service)):
    """
    Get a list of characteristics with active notifications.
    
    Returns information about all characteristics that currently have 
    active notification subscriptions.
    
    Returns:
        Object with list of characteristic UUIDs and count
    """
    try:
        if not ble_service.is_connected():
            raise HTTPException(status_code=400, detail="No device connected")
        
        notifications = ble_service.get_active_notifications()
        
        # Create a result using our Pydantic model
        result = NotificationsResult(
            characteristics=notifications,
            count=len(notifications)
        )
        
        return Response(content=json.dumps(result.dict(), default=str), media_type="application/json")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting active notifications: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@notification_router.get("/history", response_model=None)
async def get_notification_history(
    characteristic: Optional[str] = Query(None, description="Filter history by characteristic UUID"),
    limit: int = Query(100, description="Maximum number of events to return"),
    ble_service: BleService = Depends(get_ble_service)
):
    """
    Get notification history.
    
    Retrieves historical notification events that have been received.
    Can be filtered by characteristic UUID.
    
    Parameters:
        - characteristic: Optional UUID to filter by
        - limit: Maximum number of events to return (default 100)
    
    Returns:
        Object with history events and count
    """
    try:
        if not ble_service.is_connected():
            raise HTTPException(status_code=400, detail="No device connected")
        
        history_raw = ble_service.get_notification_history(characteristic, limit)
        
        # Convert to Pydantic models for consistent formatting
        events = []
        for event in history_raw.get("events", []):
            # Convert the value to our CharacteristicValue model
            if "value" in event:
                value = event["value"]
                char_value = CharacteristicValue(
                    hex=value.get("hex", ""),
                    text=value.get("text", ""),
                    bytes=value.get("bytes", []),
                    int=value.get("int")
                )
            else:
                char_value = None
                
            # Create NotificationEvent
            notification_event = NotificationEvent(
                characteristic_uuid=event.get("characteristic_uuid"),
                timestamp=event.get("timestamp"),
                value=char_value
            )
            events.append(notification_event)
            
        # Create the history object
        history = NotificationHistory(
            events=events,
            count=len(events),
            characteristic_uuid=characteristic
        )
        
        return Response(content=json.dumps(history.dict(), default=str), media_type="application/json")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting notification history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@notification_router.delete("/history", response_model=None)
async def clear_notification_history(
    characteristic: Optional[str] = Query(None, description="Clear history for specific characteristic only"),
    ble_service: BleService = Depends(get_ble_service)
):
    """
    Clear notification history.
    
    Removes stored notification events from history. Can be filtered to clear
    events only for a specific characteristic.
    
    Parameters:
        - characteristic: Optional UUID to filter by
    
    Returns:
        Status message
    """
    try:
        if not ble_service.is_connected():
            raise HTTPException(status_code=400, detail="No device connected")
        
        ble_service.clear_notification_history(characteristic)
        
        return Response(content=json.dumps({
            "status": "success", 
            "message": f"Notification history cleared{f' for {characteristic}' if characteristic else ''}"
        }, default=str), media_type="application/json")
    except Exception as e:
        logger.error(f"Error clearing notification history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@notification_router.websocket("/ws")
async def notification_websocket(websocket: WebSocket, ble_service: BleService = Depends(get_ble_service)):
    """
    WebSocket endpoint for receiving notifications in real-time.
    
    Provides a WebSocket connection that delivers real-time notifications
    from BLE characteristics. Clients can subscribe and unsubscribe to
    specific characteristics through the WebSocket connection.
    
    Protocol:
    - To subscribe: Send {"subscribe": "characteristic_uuid"}
    - To unsubscribe: Send {"unsubscribe": "characteristic_uuid"}
    - Notifications are delivered as:
        {
            "type": "notification",
            "characteristic": "uuid",
            "value": {"hex": "...", "text": "...", "bytes": [...]}
        }
    """
    await websocket.accept()
    
    try:
        # Register the connection with the WebSocket manager for centralized handling
        # This avoids duplication with our comms/websocket.py implementation
        from backend.modules.ble.comms import websocket_manager
        
        # Add this connection to the WebSocket manager
        # The manager will handle the same functionality, but we'll register 
        # this with the BLE service as well for backward compatibility
        websocket_manager.active_connections.add(websocket)
        
        # Also register with BLE service for backward compatibility
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
                    
                    # Also register with WebSocket manager if using centralized approach
                    if websocket in websocket_manager.active_connections:
                        if success and hasattr(websocket_manager, "_client_subscriptions"):
                            if websocket not in websocket_manager._client_subscriptions:
                                websocket_manager._client_subscriptions[websocket] = []
                            if char_uuid not in websocket_manager._client_subscriptions[websocket]:
                                websocket_manager._client_subscriptions[websocket].append(char_uuid)
                    
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
                    
                    # Also unregister with WebSocket manager if using centralized approach
                    if websocket in websocket_manager.active_connections:
                        if hasattr(websocket_manager, "_client_subscriptions"):
                            if websocket in websocket_manager._client_subscriptions:
                                if char_uuid in websocket_manager._client_subscriptions[websocket]:
                                    websocket_manager._client_subscriptions[websocket].remove(char_uuid)
                    
                    await websocket.send_json({
                        "type": "subscription",
                        "status": "unsubscribed" if success else "failed",
                        "characteristic": char_uuid
                    })
            
            elif "ping" in data:
                # Client is checking connection health
                await websocket.send_json({
                    "type": "pong",
                    "timestamp": data.get("timestamp", 0)
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
        # Unregister from both systems
        ble_service.unregister_notification_websocket(websocket)
        
        # Also remove from WebSocket manager
        if websocket in websocket_manager.active_connections:
            websocket_manager.disconnect(websocket)