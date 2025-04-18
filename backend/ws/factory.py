import logging
import inspect
from typing import Callable, Dict, List, Optional, Type, Any

from fastapi import WebSocket, WebSocketDisconnect, APIRouter
from pydantic import BaseModel, create_model, ValidationError

from backend.ws.manager import manager, WebSocketHandler

logger = logging.getLogger(__name__)

class WebSocketRoute:
    """Represents a WebSocket route with handlers and metadata."""
    def __init__(
        self, 
        path: str, 
        name: str,
        description: str = "",
        requires_auth: bool = False,
        auto_join_room: Optional[str] = None,
        handlers: Dict[str, WebSocketHandler] = None
    ):
        self.path = path
        self.name = name
        self.description = description
        self.requires_auth = requires_auth
        self.auto_join_room = auto_join_room
        self.handlers = handlers or {}
        
    def add_handler(self, msg_type: str, handler: WebSocketHandler) -> None:
        """Add a message handler for this route."""
        self.handlers[msg_type] = handler

class WebSocketEndpointFactory:
    """Factory for creating standardized WebSocket endpoints."""
    
    def __init__(self, router: APIRouter):
        self.router = router
        self.routes: Dict[str, WebSocketRoute] = {}
        self.handlers: Dict[str, WebSocketHandler] = {}
        
    def create_endpoint(
        self,
        path: str,
        name: str,
        description: str = "",
        requires_auth: bool = False,
        auto_join_room: Optional[str] = None
    ) -> WebSocketRoute:
        """
        Create a new WebSocket endpoint and add it to the router.
        
        Args:
            path: The WebSocket route path
            name: A unique name for this endpoint
            description: Human-readable description of what this endpoint does
            requires_auth: Whether authentication is required
            auto_join_room: Room to automatically join when connecting
            
        Returns:
            WebSocketRoute object for adding handlers
        """
        # Ensure path starts with /ws
        if not path.startswith("/ws"):
            path = f"/ws{path}"
            
        # Create route object
        route = WebSocketRoute(
            path=path,
            name=name,
            description=description,
            requires_auth=requires_auth,
            auto_join_room=auto_join_room
        )
        
        # Register the WebSocket endpoint
        @self.router.websocket(path)
        async def websocket_endpoint(websocket: WebSocket):
            client_id = await manager.connect(websocket)
            
            # Handle auto room join if specified
            if auto_join_room:
                await manager.join_room(websocket, auto_join_room)
                
            try:
                # Handle authentication if required
                if requires_auth and not await manager.require_authentication(websocket):
                    # If authentication is required but not provided, disconnect
                    await manager.disconnect(websocket)
                    return
                
                # Handle incoming messages
                async for raw_message in websocket.iter_json():
                    try:
                        # Process message
                        success = await self.process_message(websocket, name, raw_message)
                        if not success:
                            # If message handling failed, log but continue
                            logger.warning(f"Failed to handle message: {raw_message}")
                    except ValidationError as e:
                        # Handle validation errors for incoming messages
                        await manager.send_error(websocket, f"Invalid message format: {str(e)}")
                    except Exception as e:
                        # Handle other exceptions
                        logger.exception(f"Error processing message: {str(e)}")
                        await manager.send_error(websocket, f"Error processing message: {str(e)}")
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected from {path}")
            except Exception as e:
                logger.exception(f"Error in WebSocket endpoint {path}: {str(e)}")
            finally:
                # Always ensure client is disconnected properly
                await manager.disconnect(websocket)
                
        # Store route for later handler registration
        self.routes[name] = route
        logger.info(f"Created WebSocket endpoint: {path} ({name})")
        
        return route
        
    async def process_message(self, websocket: WebSocket, endpoint_name: str, message: dict) -> bool:
        """
        Process an incoming WebSocket message.
        
        Args:
            websocket: The client WebSocket
            endpoint_name: The endpoint that received the message
            message: The parsed JSON message
            
        Returns:
            True if the message was processed successfully, False otherwise
        """
        # Extract message type and payload
        msg_type = message.get("type")
        payload = message.get("data", {})
        
        if not msg_type:
            await manager.send_error(websocket, "Message type is required")
            return False
            
        # Create a handler key from endpoint + message type
        handler_key = f"{endpoint_name}.{msg_type}"
        
        # First try specific endpoint handler (e.g., "ble_socket.start_scan")
        handler = self.handlers.get(handler_key)
        
        # If not found, try global handler (e.g., "ping")
        if not handler:
            handler = self.handlers.get(msg_type)
            
        if not handler:
            await manager.send_error(websocket, f"No handler found for message type: {msg_type}")
            return False
            
        try:
            # Call handler with websocket and payload
            await handler(websocket, payload)
            return True
        except Exception as e:
            logger.exception(f"Error in handler for message type {msg_type}: {str(e)}")
            await manager.send_error(websocket, f"Error in handler: {str(e)}")
            return False
    
    def document_endpoint(self, name: str) -> dict:
        """Generate documentation for a WebSocket endpoint."""
        if name not in self.routes:
            return {"error": f"Endpoint {name} not found"}
            
        route = self.routes[name]
        handlers_info = {}
        
        for msg_type, handler in route.handlers.items():
            # Extract handler parameter info using introspection
            sig = inspect.signature(handler)
            
            # Skip websocket parameter
            params = list(sig.parameters.items())[1:]  # Skip the websocket param
            if params:
                param_name, param = params[0]  # Get payload parameter
                handlers_info[msg_type] = {
                    "description": handler.__doc__ or "No description",
                    "payload_schema": str(param.annotation) if param.annotation != inspect.Parameter.empty else "dict"
                }
            else:
                handlers_info[msg_type] = {
                    "description": handler.__doc__ or "No description",
                    "payload_schema": "None"
                }
        
        return {
            "path": route.path,
            "name": route.name,
            "description": route.description,
            "requires_auth": route.requires_auth,
            "auto_join_room": route.auto_join_room,
            "message_handlers": handlers_info
        }
    
    def register_handler(self, endpoint_name: str, msg_type: str, handler: WebSocketHandler) -> bool:
        """Register a handler for an existing endpoint."""
        if endpoint_name not in self.routes:
            logger.error(f"Cannot register handler: endpoint {endpoint_name} not found")
            return False
            
        handler_key = f"{endpoint_name}.{msg_type}"
        self.handlers[handler_key] = handler
        return True
    
    def get_all_endpoints(self) -> List[dict]:
        """Get documentation for all WebSocket endpoints."""
        return [self.document_endpoint(name) for name in self.routes]

# Create a factory with a default router
websocket_factory = WebSocketEndpointFactory(APIRouter())