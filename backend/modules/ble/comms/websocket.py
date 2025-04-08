"""BLE WebSocket communication module."""

import asyncio
import json
import logging
import time
from typing import Dict, List, Any, Set, Optional, Callable, Union
from fastapi import WebSocket, WebSocketDisconnect

from backend.modules.ble.core.device_manager import BleDeviceManager
from backend.modules.ble.config import BLE_CONFIG
# Import the Pydantic models
from backend.modules.ble.models.ble_models import (
    MessageType, BaseMessage, ScanRequestMessage, ScanResultMessage,
    ConnectRequestMessage, ConnectResultMessage, ConnectionStatus,
    CharacteristicValue, ReadResult, WriteParams, NotificationMessage,
    PingMessage, PongMessage, ErrorMessage, ScanParams, ConnectionParams
)


logger = logging.getLogger(__name__)

# Track active connections
active_connections: List[WebSocket] = []

async def websocket_endpoint(websocket: WebSocket):
    """Primary WebSocket endpoint for BLE notifications."""
    try:
        await websocket.accept()
        active_connections.append(websocket)
        logger.info(f"WebSocket connection accepted: {websocket.client}")
        
        # Send initial connection message
        await websocket.send_json({
            "type": "connection_established",
            "message": "Connected to BLE notification service"
        })
        
        # Also send connection_status for compatibility with frontend
        await websocket.send_json({
            "type": "connection_status", 
            "status": "connected",
            "message": "WebSocket connected"
        })
        
        # Process messages until disconnection
        while True:
            try:
                # Wait for the next message with a timeout
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                
                # Parse and process the message
                try:
                    message = json.loads(data)
                    await process_message(websocket, message)
                except json.JSONDecodeError:
                    logger.warning(f"Received invalid JSON: {data}")
            except asyncio.TimeoutError:
                # Keep-alive if no message received
                try:
                    # Send a ping to check connection
                    await websocket.send_json({"type": "ping"})
                    logger.debug("Sent ping to client")
                except Exception:
                    # If sending ping fails, connection is probably closed
                    logger.info(f"Connection lost during keep-alive: {websocket.client}")
                    break
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected: {websocket.client}")
                break
        
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
    finally:
        # Clean up on disconnection
        if websocket in active_connections:
            active_connections.remove(websocket)
        logger.info(f"WebSocket connection closed. Active connections: {len(active_connections)}")

async def process_message(websocket: WebSocket, message: Dict[str, Any]):
    """Process incoming WebSocket messages."""
    try:
        message_type = message.get("type", "unknown")
        logger.debug(f"Received WebSocket message: {message_type}")
        
        # Map of message types to handler functions
        handlers = {
            "ping": handle_ping,
            "get_adapters": handle_get_adapters,
            "scan_request": handle_scan_request,
            "connect_request": handle_connect_request,
            "disconnect_request": handle_disconnect_request,
            "get_services": handle_get_services,
            "connection_status": handle_connection_status,  # Add handler for connection_status
        }
        
        # Call the appropriate handler if it exists
        if message_type in handlers:
            await handlers[message_type](websocket, message)
        else:
            logger.debug(f"No handler for message type: {message_type}")
    except Exception as e:
        logger.error(f"Error processing message {message.get('type', 'unknown')}: {e}")
        await websocket.send_json({
            "type": "error",
            "message": f"Failed to process message: {str(e)}"
        })

# Add these functions after process_message but before handle_connection_status

async def handle_ping(websocket: WebSocket, message: Dict[str, Any]):
    """Handle ping message by sending pong response immediately."""
    try:
        # Echo back the same timestamp from request or generate one
        timestamp = message.get("timestamp", int(time.time() * 1000))
        await websocket.send_json({
            "type": "pong",
            "timestamp": timestamp
        })
        logger.debug("Sent pong response to client ping")
    except Exception as e:
        logger.error(f"Error handling ping: {e}")

async def handle_get_adapters(websocket: WebSocket, message: Dict[str, Any]):
    """Handle request for adapter information."""
    try:
        # Get BLE service
        from backend.modules.ble.core.ble_service import get_ble_service
        ble_service = get_ble_service()
        
        # Fetch adapters
        adapters = await ble_service.get_adapters()
        
        # Send response to client
        await websocket.send_json({
            "type": "adapter_list",
            "adapters": adapters,
            "count": len(adapters),
            "timestamp": int(time.time() * 1000)
        })
    except Exception as e:
        logger.error(f"Error getting adapters: {e}")
        await websocket.send_json({
            "type": "error",
            "context": "get_adapters",
            "message": str(e),
            "timestamp": int(time.time() * 1000)
        })

async def handle_scan_request(websocket: WebSocket, message: Dict[str, Any]):
    """Handle request to scan for BLE devices."""
    try:
        # Get scan parameters using the correct field names
        scan_time = message.get("scan_time", 10.0)  # Changed from timeout to scan_time
        service_uuids = message.get("service_uuids", None)
        continuous = message.get("continuous", False)
        
        # Send acknowledgment
        await websocket.send_json({
            "type": "scan_status",
            "status": "starting",
            "timestamp": int(time.time() * 1000)
        })
        
        # Start scan
        from backend.modules.ble.core.ble_service import get_ble_service
        ble_service = get_ble_service()
        
        # Use scan_for_devices with correct parameter names
        result = await ble_service.scan_for_devices(
            scan_time=scan_time,  # Changed from timeout to scan_time
            active=True,
            service_uuids=service_uuids,
            mock=None,
            real_scan=True
        )
        
        # Send results
        await websocket.send_json({
            "type": "scan_results",
            "devices": result.get("devices", []),
            "count": len(result.get("devices", [])),
            "timestamp": int(time.time() * 1000)
        })
    except Exception as e:
        logger.error(f"Error handling scan request: {e}")
        await websocket.send_json({
            "type": "error",
            "context": "scan_request",
            "message": str(e),
            "timestamp": int(time.time() * 1000)
        })

from backend.modules.ble.core.ble_service_factory import get_ble_service

async def handle_connect_request(websocket: WebSocket, message: Dict[str, Any]):
    """Handle request to connect to a BLE device."""
    try:
        address = message.get("address")
        if not address:
            raise ValueError("Device address is required")

        ble_service = get_ble_service()
        result = await ble_service.connect_device(address)

        await websocket.send_json({
            "type": "connect_result",
            "status": result.get("status", "error"),
            "address": address
        })
    except Exception as e:
        logger.error(f"Error handling connect request: {e}")
        await websocket.send_json({"type": "error", "message": str(e)})

async def handle_disconnect_request(websocket: WebSocket, message: Dict[str, Any]):
    """Handle request to disconnect from a BLE device."""
    try:
        # Get device address
        address = message.get("address")
        
        # Send acknowledgment
        await websocket.send_json({
            "type": "disconnect_status",
            "status": "disconnecting",
            "timestamp": int(time.time() * 1000)
        })
        
        # Disconnect from device
        from backend.modules.ble.core.ble_service import get_ble_service
        ble_service = get_ble_service()
        await ble_service.disconnect_device(address)
        
        # Send result
        await websocket.send_json({
            "type": "disconnect_result",
            "status": "disconnected",
            "timestamp": int(time.time() * 1000)
        })
    except Exception as e:
        logger.error(f"Error handling disconnect request: {e}")
        await websocket.send_json({
            "type": "error",
            "context": "disconnect_request",
            "message": str(e),
            "timestamp": int(time.time() * 1000)
        })

async def handle_get_services(websocket: WebSocket, message: Dict[str, Any]):
    """Handle request to get services for a connected device."""
    try:
        # Delay import to avoid circular dependency
        from backend.modules.ble.core.ble_service_factory import get_ble_service
        ble_service = get_ble_service()
        services = await ble_service.get_services()
        
        # Send results
        await websocket.send_json({
            "type": "services_result",
            "services": services,
            "count": len(services),
            "timestamp": int(time.time() * 1000)
        })
    except Exception as e:
        logger.error(f"Error handling get services request: {e}")
        await websocket.send_json({
            "type": "error",
            "context": "get_services",
            "message": str(e),
            "timestamp": int(time.time() * 1000)
        })

async def handle_connection_status(websocket: WebSocket, message: Dict[str, Any]):
    """Handle connection status updates from clients."""
    try:
        # Log the status
        status = message.get("status", "unknown")
        logger.debug(f"Client connection status: {status}")
        
        # Acknowledge receipt
        await websocket.send_json({
            "type": "connection_ack",
            "status": "received",
            "timestamp": int(time.time() * 1000)
        })
    except Exception as e:
        logger.error(f"Error handling connection status: {e}")

async def broadcast_message(message: Dict[str, Any]):
    """Broadcast a message to all connected clients."""
    if not active_connections:
        return
        
    disconnected_clients = []
    for connection in active_connections:
        try:
            await connection.send_json(message)
        except Exception:
            disconnected_clients.append(connection)
    
    # Clean up any failed connections
    for connection in disconnected_clients:
        if connection in active_connections:
            active_connections.remove(connection)

class BleWebSocketManager:
    """
    Manages WebSocket connections for BLE communications.
    
    Handles:
    - Client connections
    - Message dispatching
    - Event broadcasting
    """
    
    def __init__(self):
        """Initialize the WebSocket manager."""
        self.active_connections: Set[WebSocket] = set()
        self.device_manager = None  # Will be initialized lazily
        self._message_handlers = {
            MessageType.SCAN: self._handle_scan_request,  # Fixed method name
            MessageType.CONNECT: self._handle_connect,
            MessageType.DISCONNECT: self._handle_disconnect,
            MessageType.GET_SERVICES: self._handle_get_services,
            MessageType.GET_CHARACTERISTICS: self._handle_get_characteristics,
            MessageType.READ_CHARACTERISTIC: self._handle_read_characteristic,
            MessageType.WRITE_CHARACTERISTIC: self._handle_write_characteristic,
            MessageType.SUBSCRIBE: self._handle_subscribe,
            MessageType.UNSUBSCRIBE: self._handle_unsubscribe,
            MessageType.PING: self._handle_ping,
            "get_adapter_info": self._handle_get_adapter_info,  # Legacy support
        }
        
        # Track notification subscriptions by client
        self._client_subscriptions: Dict[WebSocket, List[str]] = {}
        
        # Track device notifications
        self._active_notifications: Dict[str, List[WebSocket]] = {}
        
        logger.info("BLE WebSocket manager initialized")
        
    def _get_device_manager(self) -> BleDeviceManager:
        """Get or create the device manager instance."""
        if self.device_manager is None:
            try:
                # Lazy initialization
                from backend.modules.ble.core.device_manager import BleDeviceManager
                self.device_manager = BleDeviceManager(logger=logger)
            except Exception as e:
                logger.error(f"Error creating device manager: {e}")
                # Create a simple stub instead of a complex fallback
                from types import SimpleNamespace
                self.device_manager = SimpleNamespace()
                self.device_manager.info = logger
                self.device_manager.get_available_adapters = lambda: [{
                    "id": "error", "name": "Error Adapter", 
                    "available": False, "status": "error"
                }]
                
        return self.device_manager
        
    async def connect(self, websocket: WebSocket):
        """Handle a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.add(websocket)
        self._client_subscriptions[websocket] = []
        
        # Send initial status message
        await self.send_message(websocket, {
            "type": MessageType.CONNECTION_STATUS,
            "status": ConnectionStatus.CONNECTED,
            "message": "WebSocket connected"
        })
        
        # Send adapter status
        try:
            adapters = await self._get_device_manager().get_available_adapters()
            await self.send_message(websocket, {
                "type": MessageType.ADAPTER_INFO,
                "adapters": adapters
            })
        except Exception as e:
            logger.error(f"Error getting adapter status: {e}")
            
        logger.info(f"WebSocket client connected, total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """Handle WebSocket disconnection."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            
        # Clean up subscriptions for this client
        if websocket in self._client_subscriptions:
            # Get all characteristics this client was subscribed to
            char_uuids = self._client_subscriptions[websocket]
            
            # Remove client from each characteristic's subscribers
            for char_uuid in char_uuids:
                if char_uuid in self._active_notifications:
                    if websocket in self._active_notifications[char_uuid]:
                        self._active_notifications[char_uuid].remove(websocket)
                    
                    # If no more subscribers, stop notifications on device
                    if not self._active_notifications[char_uuid]:
                        asyncio.create_task(self._stop_device_notification(char_uuid))
            
            # Remove client's subscription record
            del self._client_subscriptions[websocket]
            
        logger.info(f"WebSocket client disconnected, remaining connections: {len(self.active_connections)}")
    
    async def broadcast(self, message: Union[Dict[str, Any], BaseMessage]):
        """Send a message to all connected clients."""
        if not self.active_connections:
            return
        
        # Convert Pydantic models to dict if needed
        if hasattr(message, "dict"):
            message = message.dict()
            
        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to broadcast to client: {e}")
                disconnected.add(connection)
                
        # Clean up any disconnected clients
        for connection in disconnected:
            self.disconnect(connection)
    
    async def send_message(self, websocket: WebSocket, message: Union[Dict[str, Any], BaseMessage]):
        """Send a message to a specific client."""
        try:
            # Convert Pydantic models to dict if needed
            if hasattr(message, "dict"):
                message = message.dict()
                
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            self.disconnect(websocket)
    
    async def process_message(self, websocket: WebSocket, message: Dict[str, Any]):
        """Process an incoming WebSocket message."""
        try:
            # Extract message type and data
            message_type = message.get("type", "")
            message_data = message.get("data", {})
            
            # Log the message (but not for pings or other high-frequency messages)
            if message_type not in [MessageType.PING]:
                logger.debug(f"Received WebSocket message: {message_type}")
                
            # Find and execute the appropriate handler using enum if possible
            try:
                msg_type_enum = MessageType(message_type)
                handler = self._message_handlers.get(msg_type_enum)
            except ValueError:
                # Fall back to string-based lookup for backward compatibility
                handler = self._message_handlers.get(message_type)
                
            if handler:
                response = await handler(websocket, message_data)
                
                # If the handler returned a response, send it
                if response:
                    await self.send_message(websocket, response)
            else:
                # Unknown message type
                error_msg = ErrorMessage(
                    type=MessageType.ERROR,
                    error=f"Unknown message type: {message_type}"
                )
                await self.send_message(websocket, error_msg)
                
        except Exception as e:
            logger.exception(f"Error processing WebSocket message: {e}")
            # Send error response
            error_msg = ErrorMessage(
                type=MessageType.ERROR,
                error=str(e)
            )
            await self.send_message(websocket, error_msg)
    
    # Fix from line 363-367 (error in logger reference)
    async def _handle_scan_request(self, websocket: WebSocket, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle request to scan for BLE devices."""
        try:
            # Get scan parameters - note we use scan_time not timeout
            scan_time = data.get("scan_time", 10.0)
            service_uuids = data.get("service_uuids", [])
            continuous = data.get("continuous", False)
            active = data.get("active", True)
            
            # Send acknowledgment
            await self.send_message(websocket, {
                "type": "scan_status",
                "status": "starting",
                "timestamp": int(time.time() * 1000),
                "command_id": data.get("command_id")  # Return command_id if present
            })
            
            # Log the scan request
            logger.info(f"Scan request: time={scan_time}s, active={active}, services={service_uuids}")
            
            try:
                # Get BLE service and call scan method
                from backend.modules.ble.core.ble_service import get_ble_service
                ble_service = get_ble_service()
                
                # Check if device_manager exists
                if not hasattr(ble_service, 'device_manager'):
                    raise AttributeError("BleService is missing the device_manager attribute. Please check the service implementation.")
                
                # Call the scan_devices method with proper parameters
                devices = await ble_service.scan_devices(
                    scan_time=scan_time,
                    service_uuids=service_uuids,
                    active=active,
                    continuous=continuous
                )
                
                # Convert devices to serializable format
                serialized_devices = []
                for device in devices:
                    try:
                        if isinstance(device, dict):
                            serialized_devices.append(device)
                        else:
                            # Convert BLEDeviceInfo or similar object to dict
                            serialized_devices.append(device.dict())
                    except Exception as e:
                        logger.error(f"Error serializing device: {e}")
                        # Try a basic conversion
                        serialized_devices.append({
                            "address": getattr(device, "address", "unknown"),
                            "name": getattr(device, "name", "Unknown Device"),
                            "rssi": getattr(device, "rssi", None)
                        })
                
                # Log result summary
                logger.info(f"Scan completed: found {len(serialized_devices)} devices")
                
                # Send results
                return {
                    "type": "scan_results",
                    "devices": serialized_devices,
                    "count": len(serialized_devices),
                    "timestamp": int(time.time() * 1000),
                    "command_id": data.get("command_id")  # Return command_id if present
                }
            except AttributeError as attr_error:
                logger.error(f"Attribute error during scan: {attr_error}", exc_info=True)
                return {
                    "type": "scan_status",
                    "status": "error",
                    "message": f"Backend service configuration error: {str(attr_error)}",
                    "timestamp": int(time.time() * 1000),
                    "command_id": data.get("command_id")  # Return command_id if present
                }
            except Exception as scan_error:
                logger.error(f"Error during scan operation: {scan_error}", exc_info=True)
                # Send error response specific to the scan failure
                return {
                    "type": "scan_status",
                    "status": "error",
                    "message": f"Scan failed: {str(scan_error)}",
                    "timestamp": int(time.time() * 1000),
                    "command_id": data.get("command_id")  # Return command_id if present
                }
        except Exception as e:
            logger.error(f"Error handling scan request: {e}", exc_info=True)
            return {
                "type": "error",
                "context": "scan_request",
                "message": str(e),
                "timestamp": int(time.time() * 1000),
                "command_id": data.get("command_id")  # Return command_id if present
            }
    
    async def _handle_connect(self, websocket: WebSocket, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle BLE device connection request."""
        try:
            # Convert to Pydantic model for validation
            connect_params = ConnectionParams(
                address=data.get("address", ""),
                timeout=data.get("timeout")
            )
            
            if not connect_params.address:
                return {
                    "type": MessageType.CONNECT_ERROR,
                    "error": "No device address provided"
                }
                
            # Send connection status
            await self.send_message(websocket, {
                "type": MessageType.CONNECTION_STATUS,
                "status": ConnectionStatus.CONNECTING,
                "address": connect_params.address
            })
            
            # Connect to the device
            result = await self._get_device_manager().connect_to_device(
                address=connect_params.address,
                timeout=connect_params.timeout
            )
            
            # Return the connection result using Pydantic model
            connect_result = ConnectResultMessage(
                type=MessageType.CONNECT_RESULT,
                status=ConnectionStatus(result.get("status", "error")),
                address=connect_params.address,
                services=result.get("services", []),
                service_count=result.get("service_count", 0),
                error=result.get("error")
            )
            
            return connect_result.dict()
        except Exception as e:
            logger.error(f"Error connecting to device: {e}")
            return {
                "type": MessageType.CONNECT_ERROR,
                "error": str(e),
                "address": data.get("address", "")
            }
    
    async def _handle_disconnect(self, websocket: WebSocket, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle BLE device disconnection request."""
        try:
            # Try to disconnect from the device
            if self._get_device_manager().client and self._get_device_manager().client.is_connected:
                await self._get_device_manager().client.disconnect()
                self._get_device_manager().client = None
                self._get_device_manager().device_address = None
                
                return {
                    "type": MessageType.DISCONNECT_RESULT,
                    "status": "disconnected"
                }
            else:
                return {
                    "type": MessageType.DISCONNECT_RESULT,
                    "status": "already_disconnected"
                }
        except Exception as e:
            logger.error(f"Error disconnecting from device: {e}")
            return {
                "type": MessageType.ERROR,
                "error": str(e)
            }
    
    async def _handle_get_services(self, websocket: WebSocket, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle request to get device services."""
        try:
            if not self._get_device_manager().client or not self._get_device_manager().client.is_connected:
                return {
                    "type": MessageType.ERROR,
                    "error": "Not connected to device"
                }
                
            services = []
            for service in self._get_device_manager().client.services:
                service_info = {
                    "uuid": service.uuid,
                    "description": service.description or "Unknown Service",
                    "handle": getattr(service, "handle", None),
                    "characteristics": []
                }
                
                # Add characteristics if available
                if hasattr(service, "characteristics"):
                    for char in service.characteristics:
                        char_info = {
                            "uuid": char.uuid,
                            "description": char.description or "Unknown Characteristic",
                            "properties": char.properties,
                            "handle": char.handle
                        }
                        service_info["characteristics"].append(char_info)
                
                services.append(service_info)
                
            return {
                "type": MessageType.SERVICES_RESULT,
                "services": services,
                "count": len(services)
            }
        except Exception as e:
            logger.error(f"Error getting services: {e}")
            return {
                "type": MessageType.ERROR,
                "error": str(e)
            }
    
    async def _handle_get_characteristics(self, websocket: WebSocket, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle request to get characteristics for a service."""
        try:
            service_uuid = data.get("service_uuid")
            
            if not service_uuid:
                return {
                    "type": MessageType.ERROR,
                    "error": "No service UUID provided"
                }
                
            if not self._get_device_manager().client or not self._get_device_manager().client.is_connected:
                return {
                    "type": MessageType.ERROR,
                    "error": "Not connected to device"
                }
                
            # Find the service
            service = None
            for svc in self._get_device_manager().client.services:
                if svc.uuid.lower() == service_uuid.lower():
                    service = svc
                    break
                    
            if not service:
                return {
                    "type": MessageType.ERROR,
                    "error": f"Service {service_uuid} not found"
                }
                
            # Get characteristics
            characteristics = []
            for char in service.characteristics:
                char_info = {
                    "uuid": char.uuid,
                    "description": char.description or "Unknown Characteristic",
                    "properties": char.properties,
                    "handle": char.handle
                }
                characteristics.append(char_info)
                
            return {
                "type": MessageType.CHARACTERISTICS_RESULT,
                "service_uuid": service_uuid,
                "characteristics": characteristics,
                "count": len(characteristics)
            }
        except Exception as e:
            logger.error(f"Error getting characteristics: {e}")
            return {
                "type": MessageType.ERROR,
                "error": str(e)
            }
    
    async def _handle_read_characteristic(self, websocket: WebSocket, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle request to read a characteristic value."""
        try:
            char_uuid = data.get("characteristic_uuid")
            
            if not char_uuid:
                return {
                    "type": MessageType.READ_ERROR,
                    "error": "No characteristic UUID provided"
                }
                
            if not self._get_device_manager().client or not self._get_device_manager().client.is_connected:
                return {
                    "type": MessageType.READ_ERROR,
                    "error": "Not connected to device"
                }
                
            # Read the characteristic
            value = await self._get_device_manager().client.read_gatt_char(char_uuid)
            
            # Use the CharacteristicValue model for conversion
            char_value = CharacteristicValue(
                hex=value.hex() if value else "",
                text=self._try_decode_bytes(value),
                bytes=[b for b in value] if value else [],
                int=self._try_convert_to_int(value)
            )
            
            # Create result using Pydantic model
            result = ReadResult(
                characteristic_uuid=char_uuid,
                value=char_value
            )
            
            return {
                "type": MessageType.READ_RESULT,
                "characteristic_uuid": char_uuid,
                "value": char_value.dict()
            }
        except Exception as e:
            logger.error(f"Error reading characteristic: {e}")
            return {
                "type": MessageType.READ_ERROR,
                "error": str(e),
                "characteristic_uuid": data.get("characteristic_uuid")
            }
    
    def _try_decode_bytes(self, value: bytes) -> str:
        """Try to decode bytes to UTF-8 string."""
        if not value:
            return ""
        try:
            return value.decode('utf-8')
        except UnicodeDecodeError:
            return "(binary data)"
    
    def _try_convert_to_int(self, value: bytes) -> Optional[int]:
        """Try to convert bytes to integer value."""
        if not value or len(value) not in [1, 2, 4, 8]:
            return None
            
        try:
            return int.from_bytes(value, byteorder='little', signed=False)
        except Exception:
            return None
    
    async def _handle_write_characteristic(self, websocket: WebSocket, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle request to write a characteristic value."""
        try:
            # Validate with Pydantic model
            write_params = WriteParams(
                characteristic_uuid=data.get("characteristic_uuid", ""),
                value=data.get("value"),
                value_type=data.get("value_type", "hex"),
                byte_length=data.get("byte_length", 4)
            )
            
            if not write_params.characteristic_uuid:
                return {
                    "type": MessageType.WRITE_ERROR,
                    "error": "No characteristic UUID provided"
                }
                
            if write_params.value is None:
                return {
                    "type": MessageType.WRITE_ERROR,
                    "error": "No value provided"
                }
                
            if not self._get_device_manager().client or not self._get_device_manager().client.is_connected:
                return {
                    "type": MessageType.WRITE_ERROR,
                    "error": "Not connected to device"
                }
                
            # Convert value based on type
            bytes_value = self._convert_value_to_bytes(
                write_params.value, 
                write_params.value_type,
                write_params.byte_length
            )
                
            if bytes_value is None:
                return {
                    "type": MessageType.WRITE_ERROR,
                    "error": f"Invalid value or value type: {write_params.value_type}"
                }
                
            # Write the value
            await self._get_device_manager().client.write_gatt_char(
                write_params.characteristic_uuid, 
                bytes_value
            )
            
            return {
                "type": MessageType.WRITE_RESULT,
                "characteristic_uuid": write_params.characteristic_uuid,
                "success": True
            }
        except Exception as e:
            logger.error(f"Error writing characteristic: {e}")
            return {
                "type": MessageType.WRITE_ERROR,
                "error": str(e),
                "characteristic_uuid": data.get("characteristic_uuid")
            }
    
    def _convert_value_to_bytes(self, value: Any, value_type: str, byte_length: int = 4) -> Optional[bytes]:
        """Convert a value to bytes based on the specified type."""
        try:
            if value_type == "hex":
                # Convert hex string to bytes
                return bytes.fromhex(value)
            elif value_type == "text":
                # Convert text to bytes
                return value.encode('utf-8')
            elif value_type == "bytes":
                # Convert byte array to bytes
                return bytes(value)
            elif value_type == "int":
                # Convert integer to bytes
                return int(value).to_bytes(byte_length, byteorder='little')
            else:
                logger.warning(f"Unknown value type: {value_type}")
                return None
        except Exception as e:
            logger.error(f"Error converting value: {e}")
            return None
    
    async def _handle_subscribe(self, websocket: WebSocket, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle request to subscribe to characteristic notifications."""
        try:
            char_uuid = data.get("characteristic_uuid")
            
            if not char_uuid:
                return {
                    "type": MessageType.ERROR,
                    "error": "No characteristic UUID provided"
                }
                
            if not self._get_device_manager().client or not self._get_device_manager().client.is_connected:
                return {
                    "type": MessageType.ERROR,
                    "error": "Not connected to device"
                }
                
            # Check if this is the first subscription for this characteristic
            start_notifications = False
            if (char_uuid not in self._active_notifications or
                not self._active_notifications[char_uuid]):
                self._active_notifications[char_uuid] = []
                start_notifications = True
                
            # Add this websocket to the subscribers if not already there
            if websocket not in self._active_notifications[char_uuid]:
                self._active_notifications[char_uuid].append(websocket)
                
            # Add this characteristic to the client's subscriptions if not already there
            if websocket not in self._client_subscriptions:
                self._client_subscriptions[websocket] = []
                
            if char_uuid not in self._client_subscriptions[websocket]:
                self._client_subscriptions[websocket].append(char_uuid)
                
            # Start notifications if this is the first subscriber
            if start_notifications:
                await self._start_device_notification(char_uuid)
                
            return {
                "type": MessageType.SUBSCRIBE_RESULT,
                "characteristic_uuid": char_uuid,
                "success": True
            }
        except Exception as e:
            logger.error(f"Error subscribing to notifications: {e}")
            return {
                "type": MessageType.ERROR,
                "error": str(e),
                "characteristic_uuid": data.get("characteristic_uuid")
            }
    
    async def _start_device_notification(self, char_uuid: str):
        """Start device notifications for a characteristic."""
        try:
            # Define the notification callback
            def notification_handler(sender, data):
                # Use the CharacteristicValue model
                char_value = CharacteristicValue(
                    hex=data.hex() if data else "",
                    text=self._try_decode_bytes(data),
                    bytes=[b for b in data] if data else [],
                    int=self._try_convert_to_int(data)
                )
                
                # Create notification message using Pydantic model
                notification = NotificationMessage(
                    type=MessageType.NOTIFICATION,
                    characteristic_uuid=char_uuid,
                    value=char_value
                )
                
                # Send to all subscribers
                if char_uuid in self._active_notifications:
                    disconnected = []
                    for connection in self._active_notifications[char_uuid]:
                        try:
                            # Create a task for each sending operation
                            asyncio.create_task(
                                self.send_message(connection, notification)
                            )
                        except Exception as e:
                            logger.error(f"Error sending notification: {e}")
                            disconnected.append(connection)
                    
                    # Schedule cleanup of disconnected clients
                    if disconnected:
                        asyncio.create_task(self._cleanup_disconnected(disconnected))
            
            # Start the notifications
            await self._get_device_manager().client.start_notify(char_uuid, notification_handler)
            logger.info(f"Started notifications for {char_uuid}")
            
        except Exception as e:
            logger.error(f"Error starting notifications: {e}")
            raise
    
    async def _cleanup_disconnected(self, disconnected_clients):
        """Clean up disconnected clients."""
        for client in disconnected_clients:
            self.disconnect(client)
    
    async def _handle_unsubscribe(self, websocket: WebSocket, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle request to unsubscribe from characteristic notifications."""
        try:
            char_uuid = data.get("characteristic_uuid")
            
            if not char_uuid:
                return {
                    "type": MessageType.ERROR,
                    "error": "No characteristic UUID provided"
                }
                
            # Remove this client from the characteristic's subscribers
            if char_uuid in self._active_notifications:
                if websocket in self._active_notifications[char_uuid]:
                    self._active_notifications[char_uuid].remove(websocket)
                    
                # If no more subscribers, stop notifications
                if not self._active_notifications[char_uuid]:
                    await self._stop_device_notification(char_uuid)
                    
            # Remove this characteristic from the client's subscriptions
            if websocket in self._client_subscriptions:
                if char_uuid in self._client_subscriptions[websocket]:
                    self._client_subscriptions[websocket].remove(char_uuid)
                    
            return {
                "type": MessageType.UNSUBSCRIBE_RESULT,
                "characteristic_uuid": char_uuid,
                "success": True
            }
        except Exception as e:
            logger.error(f"Error unsubscribing from notifications: {e}")
            return {
                "type": MessageType.ERROR,
                "error": str(e),
                "characteristic_uuid": data.get("characteristic_uuid")
            }
    
    async def _stop_device_notification(self, char_uuid: str):
        """Stop device notifications for a characteristic."""
        try:
            if self._get_device_manager().client and self._get_device_manager().client.is_connected:
                await self._get_device_manager().client.stop_notify(char_uuid)
                logger.info(f"Stopped notifications for {char_uuid}")
                
            # Clean up our tracking structures
            if char_uuid in self._active_notifications:
                del self._active_notifications[char_uuid]
                
        except Exception as e:
            logger.error(f"Error stopping notifications: {e}")
    
    async def _handle_get_adapter_info(self, websocket: WebSocket, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle request to get adapter information."""
        try:
            adapters = await self._get_device_manager().get_available_adapters()
            
            return {
                "type": MessageType.ADAPTER_INFO,
                "adapters": adapters
            }
        except Exception as e:
            logger.error(f"Error getting adapter info: {e}")
            return {
                "type": MessageType.ERROR,
                "error": str(e)
            }
    
    async def _handle_ping(self, websocket: WebSocket, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle ping request."""
        # Create a pong response using Pydantic model
        pong = PongMessage(
            type=MessageType.PONG,
            timestamp=data.get("timestamp", int(time.time() * 1000))
        )
        return pong.dict()

    async def send_adapter_status(websocket, ble_service):
        """Send current adapter status to the client."""
        try:
            # Don't use await - get_adapter_status is not async
            status = ble_service.get_adapter_status()
            
            await websocket.send_json({
                "type": "adapter_status",
                "status": status
            })
        except Exception as e:
            logger.error(f"Error getting adapter status: {e}", exc_info=True)
            await websocket.send_json({
                "type": "error",
                "message": f"Failed to get adapter status: {str(e)}"
            })

    async def websocket_endpoint(websocket: WebSocket):
        """
        Primary WebSocket endpoint for BLE communications.
        
        This function should be used in FastAPI app websocket routes.
        """
        try:
            # Accept the connection
            await websocket_manager.connect(websocket)
            
            # Handle messages
            while True:
                message = await websocket.receive_json()
                await websocket_manager.process_message(websocket, message)
                
        except WebSocketDisconnect:
            websocket_manager.disconnect(websocket)
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            websocket_manager.disconnect(websocket)

# Create a singleton instance
websocket_manager = BleWebSocketManager()
