from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field
from backend.ws.manager import manager

class EventCategory(str, Enum):
    """Categories for WebSocket events."""
    SYSTEM = "system"
    DEVICE = "device"
    UWB = "uwb"
    BIOMETRIC = "biometric"
    CARD = "card"
    BLE = "ble"
    MQTT = "mqtt"
    ERROR = "error"
    AUTH = "auth"

# --- Common base models ---

class BaseMessage(BaseModel):
    """Base structure for all WebSocket messages."""
    type: str
    payload: Dict[str, Any]

class BaseEvent(BaseModel):
    """Base class for all event payloads."""
    timestamp: datetime = Field(default_factory=datetime.now)

class ErrorEvent(BaseEvent):
    """Standard error event payload."""
    message: str
    code: Optional[int] = None
    details: Optional[Dict[str, Any]] = None

class StatusEvent(BaseEvent):
    """Standard status update event."""
    status: str
    message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

# --- System events ---

class ConnectionEvent(BaseEvent):
    """Connection status events."""
    client_id: str
    status: str  # connected, disconnected, authenticated
    user_id: Optional[str] = None

class HeartbeatEvent(BaseEvent):
    """Periodic heartbeat to keep connection alive."""
    server_time: datetime = Field(default_factory=datetime.now)
    uptime_seconds: Optional[float] = None
    
class AuthRequiredEvent(BaseEvent):
    """Authentication required notification."""
    auth_methods: List[str] = ["token"]
    message: str = "Authentication required to continue"

# --- Device Management Events ---

class DeviceStatus(str, Enum):
    """Status values for devices."""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    STANDBY = "standby"
    ERROR = "error"
    BUSY = "busy"
    READY = "ready"

class DeviceEvent(BaseEvent):
    """Base event for device-related events."""
    device_id: str
    status: DeviceStatus

class DeviceListEvent(BaseEvent):
    """List of available devices."""
    devices: List[Dict[str, Any]]
    total_count: int

class DeviceCapabilitiesEvent(BaseEvent):
    """Capabilities of a specific device."""
    device_id: str
    capabilities: Dict[str, Any]

# --- UWB Events ---

class Location3D(BaseModel):
    """3D location representation."""
    x: float
    y: float
    z: float

class UWBDeviceRegisteredEvent(BaseEvent):
    """Event for UWB device registration."""
    device_id: str
    initial_location: Optional[Location3D] = None

class UWBDeviceListEvent(BaseEvent):
    """List of active UWB devices."""
    devices: List[Dict[str, Any]]

class UWBLocationEvent(BaseEvent):
    """Location update for a single UWB device."""
    device_id: str
    location: Location3D
    accuracy: Optional[float] = None
    
class UWBPositionUpdateEvent(BaseEvent):
    """Update with positions of multiple UWB devices."""
    positions: Dict[str, Location3D]
    
class UWBProximityEvent(BaseEvent):
    """Proximity alert between two UWB devices."""
    device1: str
    device2: str
    distance: float
    
class UWBLocationHistoryEvent(BaseEvent):
    """History of locations for a UWB device."""
    device_id: str
    history: List[Dict[str, Any]]
    start_time: datetime
    end_time: datetime

# --- Biometric Events ---

class BiometricStatus(str, Enum):
    """Status values for biometric operations."""
    INITIALIZING = "initializing"
    READY = "ready"
    CAPTURING = "capturing"
    PROCESSING = "processing"
    MATCHING = "matching"
    COMPLETE = "complete"
    ERROR = "error"

class BiometricStatusEvent(BaseEvent):
    """Status update during biometric operation."""
    status: BiometricStatus
    message: Optional[str] = None
    progress: Optional[float] = None  # 0.0 to 1.0

class BiometricResultEvent(BaseEvent):
    """Result of a biometric operation."""
    success: bool
    score: Optional[float] = None  # Confidence score if applicable
    match_id: Optional[str] = None  # ID of the matched record if found
    error_message: Optional[str] = None
    
class BiometricListEvent(BaseEvent):
    """List of biometric records."""
    records: List[Dict[str, Any]]
    count: int

# --- Card/NFC/RFID Events ---

class CardType(str, Enum):
    """Types of cards/tags."""
    MIFARE = "mifare"
    DESFIRE = "desfire"
    ISO14443 = "iso14443"
    ISO15693 = "iso15693"
    NTAG = "ntag"
    FELICA = "felica"
    OTHER = "other"

class CardDetectedEvent(BaseEvent):
    """Event when a card is detected."""
    reader_id: str
    card_type: Optional[CardType] = None
    card_id: str
    card_info: Optional[Dict[str, Any]] = None

class ReaderStatusEvent(BaseEvent):
    """Status update for a card reader."""
    reader_id: str
    status: str  # connected, disconnected, ready, busy, error
    message: Optional[str] = None

class CardDataEvent(BaseEvent):
    """Card data read event."""
    reader_id: str
    card_id: str
    data: Dict[str, Any]

class CardOperationResultEvent(BaseEvent):
    """Result of a card operation (read/write)."""
    reader_id: str
    card_id: str
    operation: str  # read, write, auth
    success: bool
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None

# --- BLE Events ---

class BLEDeviceEvent(BaseEvent):
    """Event for BLE device detection."""
    address: str
    name: Optional[str] = None
    rssi: Optional[int] = None
    manufacturer_data: Optional[Dict[str, Any]] = None
    services: Optional[List[str]] = None

class BLEScanStatusEvent(BaseEvent):
    """Status of a BLE scan operation."""
    status: str  # started, stopped, complete
    duration: Optional[float] = None
    devices_found: Optional[int] = None

class BLEConnectionEvent(BaseEvent):
    """BLE connection status event."""
    address: str
    status: str  # connected, disconnected, failed
    error: Optional[str] = None

class BLECharacteristicEvent(BaseEvent):
    """BLE characteristic value event."""
    address: str
    service: str
    characteristic: str
    value: Any
    value_hex: Optional[str] = None

# --- MQTT Events ---

class MQTTMessageEvent(BaseEvent):
    """MQTT message received event."""
    topic: str
    payload: Any
    qos: int
    retain: bool

class MQTTSubscriptionEvent(BaseEvent):
    """MQTT subscription status event."""
    topic: str
    status: str  # subscribed, unsubscribed, error
    error: Optional[str] = None

class MQTTPublishResultEvent(BaseEvent):
    """Result of an MQTT publish operation."""
    topic: str
    success: bool
    message_id: Optional[int] = None
    error: Optional[str] = None

# --- Event type registry ---

class EventRegistry:
    """Registry of standard event types and their schemas."""
    
    def __init__(self):
        self.events = {}
        self._register_standard_events()
        
    def _register_standard_events(self):
        """Register all standard event types."""
        # System events
        self.register_event("system.error", "Error notification", ErrorEvent, EventCategory.ERROR)
        self.register_event("system.connection", "Connection status update", ConnectionEvent, EventCategory.SYSTEM)
        self.register_event("system.heartbeat", "Server heartbeat", HeartbeatEvent, EventCategory.SYSTEM)
        self.register_event("system.auth_required", "Authentication required", AuthRequiredEvent, EventCategory.AUTH)
        
        # Device events
        self.register_event("device.status", "Device status update", DeviceEvent, EventCategory.DEVICE)
        self.register_event("device.list", "List of available devices", DeviceListEvent, EventCategory.DEVICE)
        self.register_event("device.capabilities", "Device capabilities", DeviceCapabilitiesEvent, EventCategory.DEVICE)
        
        # UWB events
        self.register_event("uwb.device_registered", "UWB device registered", UWBDeviceRegisteredEvent, EventCategory.UWB)
        self.register_event("uwb.device_list", "UWB device list", UWBDeviceListEvent, EventCategory.UWB)
        self.register_event("uwb.location", "UWB device location", UWBLocationEvent, EventCategory.UWB)
        self.register_event("uwb.position_update", "UWB position update", UWBPositionUpdateEvent, EventCategory.UWB)
        self.register_event("uwb.proximity", "UWB proximity alert", UWBProximityEvent, EventCategory.UWB)
        self.register_event("uwb.location_history", "UWB location history", UWBLocationHistoryEvent, EventCategory.UWB)
        
        # Biometric events
        self.register_event("biometric.status", "Biometric operation status", BiometricStatusEvent, EventCategory.BIOMETRIC)
        self.register_event("biometric.result", "Biometric operation result", BiometricResultEvent, EventCategory.BIOMETRIC)
        self.register_event("biometric.list", "Biometric records list", BiometricListEvent, EventCategory.BIOMETRIC)
        
        # Card events
        self.register_event("card.detected", "Card detected", CardDetectedEvent, EventCategory.CARD)
        self.register_event("card.reader_status", "Card reader status", ReaderStatusEvent, EventCategory.CARD)
        self.register_event("card.data", "Card data read", CardDataEvent, EventCategory.CARD)
        self.register_event("card.operation_result", "Card operation result", CardOperationResultEvent, EventCategory.CARD)
        
        # BLE events
        self.register_event("ble.device", "BLE device found", BLEDeviceEvent, EventCategory.BLE)
        self.register_event("ble.scan_status", "BLE scan status", BLEScanStatusEvent, EventCategory.BLE)
        self.register_event("ble.connection", "BLE connection status", BLEConnectionEvent, EventCategory.BLE)
        self.register_event("ble.characteristic", "BLE characteristic value", BLECharacteristicEvent, EventCategory.BLE)
        
        # MQTT events
        self.register_event("mqtt.message", "MQTT message received", MQTTMessageEvent, EventCategory.MQTT)
        self.register_event("mqtt.subscription", "MQTT subscription status", MQTTSubscriptionEvent, EventCategory.MQTT)
        self.register_event("mqtt.publish_result", "MQTT publish result", MQTTPublishResultEvent, EventCategory.MQTT)
    
    def register_event(self, event_type: str, description: str, schema: type, category: EventCategory):
        """Register a new event type with its schema."""
        self.events[event_type] = {
            "type": event_type,
            "description": description,
            "schema": schema,
            "category": category,
            "example": self._generate_example(schema)
        }
    
    def _generate_example(self, schema: type) -> dict:
        """Generate an example payload for the schema."""
        try:
            # Create an instance with default values
            instance = schema()
            return instance.dict()
        except Exception:
            return {"example": "Unavailable"}
    
    def get_event_schema(self, event_type: str) -> Optional[type]:
        """Get the schema for an event type."""
        if event_type in self.events:
            return self.events[event_type]["schema"]
        return None
    
    def get_event_info(self, event_type: str) -> Optional[dict]:
        """Get information about an event type."""
        return self.events.get(event_type)
    
    def list_events(self, category: Optional[EventCategory] = None) -> List[dict]:
        """List all registered events, optionally filtered by category."""
        if category:
            return [
                {"type": k, "description": v["description"], "category": v["category"].value}
                for k, v in self.events.items() 
                if v["category"] == category
            ]
        return [
            {"type": k, "description": v["description"], "category": v["category"].value}
            for k, v in self.events.items()
        ]
    
    def event_categories(self) -> List[str]:
        """Get all event categories."""
        return [category.value for category in EventCategory]

# Create a global instance
event_registry = EventRegistry()

# Convenience functions for creating events
def create_event(event_type: str, **kwargs) -> dict:
    """Create an event message with the specified type and payload data."""
    schema = event_registry.get_event_schema(event_type)
    if schema:
        # Validate against schema if available
        payload = schema(**kwargs).dict()
    else:
        # Use raw kwargs if no schema
        payload = kwargs
    
    return {
        "type": event_type,
        "payload": payload
    }