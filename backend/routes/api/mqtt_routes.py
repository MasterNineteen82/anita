from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, Optional
from pydantic import BaseModel
import logging
from backend.modules.mqtt_manager import MQTTManager
# from backend.modules.system.models import StatusResponse, ErrorResponse, LogRequest, Settings  # Commented out
from ..utils import handle_errors, validate_json

logger = logging.getLogger(__name__)

# Create a router without prefix (prefix is added in main.py)
router = APIRouter(tags=["mqtt"])

class MQTTConnectRequest(BaseModel):
    broker: str
    port: int = 1883
    client_id: str
    username: Optional[str] = None
    password: Optional[str] = None

class MQTTPublishRequest(BaseModel):
    topic: str
    payload: str

class MQTTSubscribeRequest(BaseModel):
    topic: str

# Dictionary to store MQTT client instances
mqtt_clients = {}

@router.post("/mqtt/connect", summary="Connect to an MQTT broker")
async def connect_mqtt_broker(request: MQTTConnectRequest):
    """
    Connect to an MQTT broker.
    
    Args:
        request: The connection details for the MQTT broker.
        
    Returns:
        Dictionary indicating success or failure.
    """
    try:
        # Create an MQTT manager instance
        mqtt_client = MQTTManager(
            broker=request.broker,
            port=request.port,
            client_id=request.client_id,
            username=request.username,
            password=request.password
        )
        
        # Connect to the broker
        mqtt_client.connect()
        
        # Store the client for future use
        mqtt_clients[request.client_id] = mqtt_client
        
        return {
            "status": "success", 
            "message": f"Connected to MQTT broker {request.broker}:{request.port}"
        }
    except Exception as e:
        logger.error(f"Error connecting to MQTT broker: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error connecting to MQTT broker: {str(e)}")

@router.post("/mqtt/disconnect/{client_id}", summary="Disconnect from an MQTT broker")
async def disconnect_mqtt_broker(client_id: str):
    """
    Disconnect from an MQTT broker.
    
    Args:
        client_id: The client ID of the connection to disconnect.
        
    Returns:
        Dictionary indicating success or failure.
    """
    try:
        if client_id not in mqtt_clients:
            raise HTTPException(status_code=404, detail=f"Client ID {client_id} not found")
            
        mqtt_client = mqtt_clients[client_id]
        mqtt_client.disconnect()
        
        # Remove the client from the dictionary
        del mqtt_clients[client_id]
        
        return {
            "status": "success", 
            "message": f"Disconnected client {client_id} from MQTT broker"
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error disconnecting from MQTT broker: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error disconnecting from MQTT broker: {str(e)}")

@router.post("/mqtt/publish/{client_id}", summary="Publish a message to an MQTT topic")
async def publish_mqtt_message(client_id: str, request: MQTTPublishRequest):
    """
    Publish a message to an MQTT topic.
    
    Args:
        client_id: The client ID of the connection to use.
        request: The topic and payload details.
        
    Returns:
        Dictionary indicating success or failure.
    """
    try:
        if client_id not in mqtt_clients:
            raise HTTPException(status_code=404, detail=f"Client ID {client_id} not found")
            
        mqtt_client = mqtt_clients[client_id]
        mqtt_client.publish(request.topic, request.payload)
        
        return {
            "status": "success", 
            "message": f"Published message to {request.topic}"
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error publishing MQTT message: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error publishing MQTT message: {str(e)}")

@router.post("/mqtt/subscribe/{client_id}", summary="Subscribe to an MQTT topic")
async def subscribe_mqtt_topic(client_id: str, request: MQTTSubscribeRequest):
    """
    Subscribe to an MQTT topic.
    
    Args:
        client_id: The client ID of the connection to use.
        request: The topic details.
        
    Returns:
        Dictionary indicating success or failure.
    """
    try:
        if client_id not in mqtt_clients:
            raise HTTPException(status_code=404, detail=f"Client ID {client_id} not found")
            
        mqtt_client = mqtt_clients[client_id]
        mqtt_client.subscribe(request.topic)
        
        return {
            "status": "success", 
            "message": f"Subscribed to topic {request.topic}"
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error subscribing to MQTT topic: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error subscribing to MQTT topic: {str(e)}")

@router.get("/mqtt/status", summary="Get MQTT connection status")
@handle_errors
async def get_mqtt_status():
    """
    Get the status of MQTT connections.
    
    Returns:
        Dictionary containing MQTT connection status
    """
    return {
        "status": "success",
        "data": {
            "connected": False,
            "broker": None
        }
    }