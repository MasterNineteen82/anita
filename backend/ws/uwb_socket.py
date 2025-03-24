import logging
from typing import Dict, List, Set, Optional, Any

from fastapi import WebSocket, APIRouter, Depends

from ws.manager import manager
from ws.factory import websocket_factory
from ws.events import create_event, Location3D
from backend.modules.monitoring import UWBPositionMonitor, monitoring_manager

from repositories.uwb_repository import UWBRepository
from services.uwb_system import UWBSystem

logger = logging.getLogger(__name__)

# Create UWB dependencies
uwb_repository = UWBRepository()
uwb_system = UWBSystem()

# Create UWB position monitor
uwb_monitor = UWBPositionMonitor(uwb_system, uwb_repository)
monitoring_manager.register_monitor(uwb_monitor)

# Create router
router = APIRouter()

# Create UWB WebSocket endpoint
uwb_endpoint = websocket_factory.create_endpoint(
    path="/ws/uwb",
    name="uwb_socket",
    description="UWB device tracking and management",
    auto_join_room="uwb"
)

# Register handlers

async def register_uwb_device(websocket: WebSocket, payload: dict):
    """Register a new UWB device."""
    device_id = payload.get("device_id")
    initial_location = payload.get("initial_location", {"x": 0, "y": 0, "z": 0})
    
    if not device_id:
        await manager.send_error(websocket, "Device ID is required")
        return
    
    try:
        # Register device in repository
        success = await uwb_repository.register_device(device_id, initial_location)
        
        if success:
            # Send success response
            await manager.send_message(websocket, create_event(
                "uwb.device_registered",
                device_id=device_id,
                initial_location=initial_location
            ))
            
            # Broadcast to room (except sender)
            await manager.broadcast_to_room("uwb", create_event(
                "device.status",
                device_id=device_id,
                status="connected",
                device_type="uwb"
            ), exclude=websocket)
        else:
            await manager.send_error(websocket, f"Failed to register device {device_id}")
    except Exception as e:
        logger.error(f"Error registering UWB device: {str(e)}")
        await manager.send_error(websocket, f"Error registering device: {str(e)}")

async def get_active_uwb_devices(websocket: WebSocket, payload: dict):
    """Get list of active UWB devices."""
    try:
        devices = await uwb_repository.get_all_devices()
        
        # Format for frontend
        device_list = [{
            "id": device.id,
            "last_seen": device.last_seen.isoformat() if hasattr(device, "last_seen") else None,
            "location": {
                "x": getattr(getattr(device, "location", None), "x", 0),
                "y": getattr(getattr(device, "location", None), "y", 0),
                "z": getattr(getattr(device, "location", None), "z", 0)
            }
        } for device in devices]
        
        await manager.send_message(websocket, create_event(
            "uwb.device_list",
            devices=device_list
        ))
    except Exception as e:
        logger.error(f"Error fetching UWB devices: {str(e)}")
        await manager.send_error(websocket, f"Error fetching devices: {str(e)}")

async def get_uwb_device_location(websocket: WebSocket, payload: dict):
    """Get current location for a UWB device."""
    device_id = payload.get("device_id")
    
    if not device_id:
        await manager.send_error(websocket, "Device ID is required")
        return
    
    try:
        device = await uwb_repository.get_device(device_id)
        
        if not device:
            await manager.send_error(websocket, f"Device {device_id} not found")
            return
            
        # Get current location from UWB system
        location = await uwb_system.get_device_position(device_id)
        
        if not location:
            # Fall back to repository location
            location = {
                "x": getattr(getattr(device, "location", None), "x", 0),
                "y": getattr(getattr(device, "location", None), "y", 0),
                "z": getattr(getattr(device, "location", None), "z", 0)
            }
            
        await manager.send_message(websocket, create_event(
            "uwb.location",
            device_id=device_id,
            location=location
        ))
    except Exception as e:
        logger.error(f"Error getting UWB device location: {str(e)}")
        await manager.send_error(websocket, f"Error getting device location: {str(e)}")

async def start_uwb_position_tracking(websocket: WebSocket, payload: dict):
    """Start real-time position tracking for devices."""
    device_ids = payload.get("device_ids", [])
    update_frequency = payload.get("update_frequency", 0.5)  # Default to 2Hz
    
    if not device_ids:
        await manager.send_error(websocket, "At least one device ID is required")
        return
    
    try:
        # Set monitor properties
        uwb_monitor.track_devices(device_ids)
        uwb_monitor.interval = update_frequency
        
        # Start monitor if not already running
        if not uwb_monitor.running:
            await monitoring_manager.start_monitor("uwb_position_monitor", "uwb")
            
        await manager.send_message(websocket, create_event(
            "uwb.tracking_started",
            device_ids=device_ids,
            update_frequency=update_frequency
        ))
    except Exception as e:
        logger.error(f"Error starting UWB tracking: {str(e)}")
        await manager.send_error(websocket, f"Error starting tracking: {str(e)}")

async def stop_uwb_position_tracking(websocket: WebSocket, payload: dict):
    """Stop position tracking."""
    try:
        await monitoring_manager.stop_monitor("uwb_position_monitor")
        
        await manager.send_message(websocket, create_event(
            "uwb.tracking_stopped"
        ))
    except Exception as e:
        logger.error(f"Error stopping UWB tracking: {str(e)}")
        await manager.send_error(websocket, f"Error stopping tracking: {str(e)}")

async def get_uwb_location_history(websocket: WebSocket, payload: dict):
    """Get location history for a device."""
    device_id = payload.get("device_id")
    start_time = payload.get("start_time")
    end_time = payload.get("end_time")
    limit = payload.get("limit", 100)
    
    if not device_id:
        await manager.send_error(websocket, "Device ID is required")
        return
    
    try:
        history = await uwb_repository.get_location_history(
            device_id,
            start_time,
            end_time,
            limit
        )
        
        await manager.send_message(websocket, create_event(
            "uwb.location_history",
            device_id=device_id,
            history=history,
            start_time=start_time,
            end_time=end_time
        ))
    except Exception as e:
        logger.error(f"Error getting UWB location history: {str(e)}")
        await manager.send_error(websocket, f"Error getting location history: {str(e)}")

# Register handlers
websocket_factory.register_handler("uwb_socket", "register_device", register_uwb_device)
websocket_factory.register_handler("uwb_socket", "get_active_devices", get_active_uwb_devices)
websocket_factory.register_handler("uwb_socket", "get_device_location", get_uwb_device_location)
websocket_factory.register_handler("uwb_socket", "start_position_tracking", start_uwb_position_tracking)
websocket_factory.register_handler("uwb_socket", "stop_position_tracking", stop_uwb_position_tracking)
websocket_factory.register_handler("uwb_socket", "get_location_history", get_uwb_location_history)