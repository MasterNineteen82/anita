"""BLE WebSocket communication handler.

This module provides WebSocket functionality for BLE operations:
- Real-time device notifications
- Command execution
- Scan result broadcasting
"""

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
            MessageType.SCAN: self._handle_scan,
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
            # Lazy initialization to avoid circular imports
            self.device_manager = BleDeviceManager(logger=logger)
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
    
    async def _handle_scan(self, websocket: WebSocket, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle BLE scan request."""
        try:
            # Convert to Pydantic model for validation
            scan_params = ScanParams(
                scan_time=data.get("scan_time", 5.0),
                active=data.get("active", True),
                service_uuids=data.get("service_uuids"),
                mock=data.get("mock"),
                real_scan=data.get("real_scan", False)
            )
            
            # Send scan start notification
            await self.send_message(websocket, {
                "type": "scan_status",
                "status": "started"
            })
            
            # Perform the scan
            devices = await self._get_device_manager().scan_devices(
                scan_time=scan_params.effective_scan_time,
                active=scan_params.active,
                service_uuids=scan_params.service_uuids,
                mock=scan_params.mock,
                real_scan=scan_params.effective_real_scan
            )
            
            # Build and return the response using Pydantic model
            result = ScanResultMessage(
                type=MessageType.SCAN_RESULT,
                devices=devices,
                count=len(devices)
            )
            
            return result.dict()
        except Exception as e:
            logger.error(f"Error during scan: {e}")
            return {
                "type": MessageType.SCAN_ERROR,
                "error": str(e)
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
            if char_uuid not in self._active_notifications:
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

# Create a singleton instance
websocket_manager = BleWebSocketManager()

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