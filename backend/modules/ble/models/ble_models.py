"""
Bluetooth Low Energy (BLE) data models.

This module contains Pydantic models for BLE operations, including:
- Device models (scan results, connection info)
- Service and characteristic models
- Adapter information models
- Request/response models for API endpoints
- WebSocket message models
"""

from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field, validator
from enum import Enum, auto
import time


# ============================================================================
# Enum Definitions
# ============================================================================

class ConnectionStatus(str, Enum):
    """Connection status enum."""
    CONNECTED = "connected"
    CONNECTING = "connecting"
    DISCONNECTED = "disconnected"
    FAILED = "failed"
    ERROR = "error"


class AdapterStatus(str, Enum):
    """Adapter status enum."""
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    POWERED_ON = "powered_on"
    POWERED_OFF = "powered_off"
    ERROR = "error"


class MessageType(str, Enum):
    """WebSocket message type enum."""
    SCAN = "scan"
    SCAN_RESULT = "scan_result"
    SCAN_ERROR = "scan_error"
    CONNECT = "connect"
    CONNECT_RESULT = "connect_result"
    CONNECT_ERROR = "connect_error"
    DISCONNECT = "disconnect"
    DISCONNECT_RESULT = "disconnect_result"
    GET_SERVICES = "get_services"
    SERVICES_RESULT = "services_result"
    GET_CHARACTERISTICS = "get_characteristics"
    CHARACTERISTICS_RESULT = "characteristics_result"
    READ_CHARACTERISTIC = "read_characteristic"
    READ_RESULT = "read_result"
    WRITE_CHARACTERISTIC = "write_characteristic"
    WRITE_RESULT = "write_result"
    SUBSCRIBE = "subscribe"
    SUBSCRIBE_RESULT = "subscribe_result"
    UNSUBSCRIBE = "unsubscribe"
    UNSUBSCRIBE_RESULT = "unsubscribe_result"
    NOTIFICATION = "notification"
    ERROR = "error"
    PING = "ping"
    PONG = "pong"
    ADAPTER_INFO = "adapter_info"
    CONNECTION_STATUS = "connection_status"


# ============================================================================
# Device Models
# ============================================================================

class BleDeviceMetadata(BaseModel):
    """BLE device metadata model."""
    manufacturer_data: Dict[str, Any] = Field(default_factory=dict)
    service_data: Dict[str, Any] = Field(default_factory=dict)
    service_uuids: List[str] = Field(default_factory=list)


class BleDevice(BaseModel):
    """BLE device model."""
    address: str
    name: Optional[str] = "Unknown Device"
    rssi: Optional[int] = None
    isMock: bool = False
    metadata: Optional[BleDeviceMetadata] = None


class ScanResult(BaseModel):
    """BLE scan result model."""
    devices: List[BleDevice]
    count: int = 0
    scan_time: Optional[float] = None
    active: Optional[bool] = None
    mock: bool = False


# ============================================================================
# Service and Characteristic Models
# ============================================================================

class BleCharacteristic(BaseModel):
    """BLE characteristic model."""
    uuid: str
    description: Optional[str] = None
    properties: Optional[List[str]] = None
    handle: Optional[int] = None


class BleService(BaseModel):
    """BLE service model."""
    uuid: str
    description: Optional[str] = None
    characteristics: List[BleCharacteristic] = Field(default_factory=list)


class CharacteristicValue(BaseModel):
    """BLE characteristic value model."""
    hex: str = ""
    text: str = ""
    bytes: List[int] = Field(default_factory=list)
    int_value: Optional[int] = None


# ============================================================================
# Adapter Models
# ============================================================================

class BleAdapter(BaseModel):
    """BLE adapter model."""
    id: str
    name: str
    available: bool
    status: Optional[str] = None
    error: Optional[str] = None
    system: Optional[str] = None
    version: Optional[str] = None


# ============================================================================
# Request Models
# ============================================================================

class ScanParams(BaseModel):
    """Parameters for BLE device scanning."""
    scan_time: Optional[float] = 5.0  
    active: bool = True
    service_uuids: Optional[List[str]] = []
    mock: Optional[bool] = None
    real_scan: Optional[bool] = False

    # Add this for backward compatibility
    @property
    def timeout(self) -> float:
        """For backwards compatibility with code using timeout."""
        return self.scan_time if self.scan_time is not None else 5.0

class CharacteristicParams(BaseModel):
    """BLE characteristic parameters model."""
    characteristic_uuid: str
    service_uuid: Optional[str] = None


class WriteParams(BaseModel):
    """BLE characteristic write parameters model."""
    characteristic_uuid: str
    value: Any
    value_type: str = "hex"  # One of: hex, text, bytes, int
    byte_length: int = 4     # For int values only


# ============================================================================
# Response Models
# ============================================================================

class ConnectionResult(BaseModel):
    """BLE connection result model."""
    status: ConnectionStatus
    address: str
    services: List[BleService] = Field(default_factory=list)
    service_count: int = 0
    error: Optional[str] = None


class DisconnectResult(BaseModel):
    """BLE disconnect result model."""
    status: str
    error: Optional[str] = None


class ServicesResult(BaseModel):
    """BLE services result model."""
    services: List[BleService]
    count: int = 0


class CharacteristicsResult(BaseModel):
    """BLE characteristics result model."""
    service_uuid: str
    characteristics: List[BleCharacteristic]
    count: int = 0


class ReadResult(BaseModel):
    """BLE characteristic read result model."""
    characteristic_uuid: str
    value: CharacteristicValue


class WriteResult(BaseModel):
    """BLE characteristic write result model."""
    characteristic_uuid: str
    success: bool
    error: Optional[str] = None


class SubscribeResult(BaseModel):
    """BLE subscribe result model."""
    characteristic_uuid: str
    success: bool
    error: Optional[str] = None


class AdapterResult(BaseModel):
    """BLE adapter result model."""
    adapters: List[BleAdapter]


class ErrorResult(BaseModel):
    """BLE error result model."""
    error: str
    type: Optional[str] = None  # The type of operation that failed


# ============================================================================
# WebSocket Message Models
# ============================================================================

class BaseMessage(BaseModel):
    """Base WebSocket message model."""
    type: MessageType


class ScanRequestMessage(BaseMessage):
    """WebSocket scan request message."""
    type: MessageType = MessageType.SCAN
    data: ScanParams


class ScanResultMessage(BaseMessage):
    """WebSocket scan result message."""
    type: MessageType = MessageType.SCAN_RESULT
    devices: List[BleDevice]
    count: int


class ConnectionParams(BaseModel):
    """BLE connection parameters model."""
    address: Optional[str] = None
    timeout: float = 10.0
    auto_reconnect: bool = True
    remember_device: bool = True
    use_cached_services: bool = True
    retry_count: int = 3
    retry_interval: float = 2.0
    max_reconnect_attempts: int = 5
    use_bluetooth_le_device: bool = True  # Windows-specific

    model_config = {
        'protected_namespaces': ()
    }


class ConnectRequestMessage(BaseMessage):
    """WebSocket connect request message."""
    type: MessageType = MessageType.CONNECT
    data: ConnectionParams


class ConnectResultMessage(BaseMessage):
    """WebSocket connect result message."""
    type: MessageType = MessageType.CONNECT_RESULT
    status: ConnectionStatus
    address: str
    services: List[BleService] = Field(default_factory=list)
    service_count: int = 0
    error: Optional[str] = None


class NotificationMessage(BaseModel):
    """Model for WebSocket notification message."""
    type: str = MessageType.NOTIFICATION
    characteristic_uuid: str
    value: CharacteristicValue


class PingMessage(BaseMessage):
    """WebSocket ping message."""
    type: MessageType = MessageType.PING
    timestamp: int


class PongMessage(BaseMessage):
    """WebSocket pong message."""
    type: MessageType = MessageType.PONG
    timestamp: int


class AdapterInfoMessage(BaseMessage):
    """WebSocket adapter info message."""
    type: MessageType = MessageType.ADAPTER_INFO
    adapters: List[BleAdapter]


class ConnectionStatusMessage(BaseMessage):
    """WebSocket connection status message."""
    type: MessageType = MessageType.CONNECTION_STATUS
    status: ConnectionStatus
    address: Optional[str] = None
    message: Optional[str] = None


class ErrorMessage(BaseMessage):
    """WebSocket error message."""
    type: MessageType = MessageType.ERROR
    error: str


# ============================================================================
# Factory Functions
# ============================================================================

def create_device_from_dict(device_dict: Dict[str, Any]) -> BleDevice:
    """Create a BleDevice model from a dictionary."""
    # Create metadata if it exists
    metadata = None
    if "metadata" in device_dict and device_dict["metadata"]:
        metadata = BleDeviceMetadata(**device_dict["metadata"])
    
    # Create and return the device
    return BleDevice(
        address=device_dict["address"],
        name=device_dict.get("name", "Unknown Device"),
        rssi=device_dict.get("rssi"),
        isMock=device_dict.get("isMock", False),
        metadata=metadata
    )


def create_service_from_dict(service_dict: Dict[str, Any]) -> BleService:
    """Create a BleService model from a dictionary."""
    # Create characteristics
    characteristics = []
    for char_dict in service_dict.get("characteristics", []):
        characteristics.append(BleCharacteristic(**char_dict))
    
    # Create and return the service
    return BleService(
        uuid=service_dict["uuid"],
        description=service_dict.get("description"),
        characteristics=characteristics
    )
    
# Additional models to add to ble_models.py

# ============================================================================
# Device Information Models
# ============================================================================

class BLEDeviceInfo(BaseModel):
    """Comprehensive BLE device information model.
    
    This aligns with the BLEDeviceInfo dataclass in ble_service.py
    """
    address: str
    name: Optional[str] = None
    rssi: Optional[int] = None
    timestamp: float = Field(default_factory=time.time)
    last_seen: float = Field(default_factory=time.time)
    manufacturer_data: Dict[str, Any] = Field(default_factory=dict)
    service_data: Dict[str, Any] = Field(default_factory=dict)
    service_uuids: List[str] = Field(default_factory=list)
    appearance: Optional[int] = None
    tx_power: Optional[int] = None
    is_connectable: Optional[bool] = None
    address_type: Optional[str] = None
    local_name: Optional[str] = None
    isMock: bool = False


# ============================================================================
# Notification Models
# ============================================================================

class NotificationRequest(BaseModel):
    """Notification request model.
    
    Used in notification_routes.py
    """
    characteristic: str
    enable: bool = True
    
class NotificationSubscription(BaseModel):
    """Notification subscription model."""
    characteristic_uuid: str
    client_id: str
    timestamp: float = Field(default_factory=time.time)


# ============================================================================
# Device Cache Models
# ============================================================================

class DeviceCacheEntry(BaseModel):
    """Device cache entry model."""
    device: BLEDeviceInfo
    last_updated: float = Field(default_factory=time.time)


class DeviceCacheStats(BaseModel):
    """Device cache statistics model."""
    total_devices: int = 0
    active_devices: int = 0
    expired_devices: int = 0
    mock_devices: int = 0
    real_devices: int = 0
    last_cleanup: Optional[float] = None


# ============================================================================
# Metrics Models
# ============================================================================

class AdapterMetric(BaseModel):
    """Adapter metric model for BleMetricsCollector."""
    adapter_id: str
    operation: str
    success: bool
    timestamp: float = Field(default_factory=time.time)
    duration: Optional[float] = None
    details: Dict[str, Any] = Field(default_factory=dict)


class DeviceMetric(BaseModel):
    """Device metric model for BleMetricsCollector."""
    device_address: str
    operation: str
    success: bool
    timestamp: float = Field(default_factory=time.time)
    duration: Optional[float] = None
    details: Dict[str, Any] = Field(default_factory=dict)


class SystemMetric(BaseModel):
    """System metric model for SystemMonitor."""
    timestamp: float = Field(default_factory=time.time)
    cpu_percent: Optional[float] = None
    memory_percent: Optional[float] = None
    disk_percent: Optional[float] = None
    network_sent: Optional[int] = None
    network_recv: Optional[int] = None


# ============================================================================
# Service Specific Models
# ============================================================================

class BatteryServiceData(BaseModel):
    """Battery service data model."""
    level: int
    last_updated: float = Field(default_factory=time.time)


class DeviceInfoServiceData(BaseModel):
    """Device Information service data model."""
    manufacturer_name: Optional[str] = None
    model_number: Optional[str] = None
    serial_number: Optional[str] = None
    hardware_revision: Optional[str] = None
    firmware_revision: Optional[str] = None
    software_revision: Optional[str] = None
    system_id: Optional[str] = None
    last_updated: float = Field(default_factory=time.time)

    model_config = {
        'protected_namespaces': ()
    }


# ============================================================================
# Error and Recovery Models
# ============================================================================

class BleError(BaseModel):
    """BLE error model for BleErrorRecovery."""
    error_type: str
    message: str
    timestamp: float = Field(default_factory=time.time)
    component: str
    device_address: Optional[str] = None
    recoverable: bool = True
    recovery_attempted: bool = False
    recovery_successful: Optional[bool] = None
    details: Dict[str, Any] = Field(default_factory=dict)


class RecoveryAction(BaseModel):
    """Recovery action model for BleErrorRecovery."""
    action_type: str
    timestamp: float = Field(default_factory=time.time)
    successful: Optional[bool] = None
    duration: Optional[float] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    
# ============================================================================
# Device Information Models
# ============================================================================

class BLEDeviceInfo(BaseModel):
    """Comprehensive BLE device information model."""
    address: str
    name: Optional[str] = None
    rssi: Optional[int] = None
    timestamp: float = Field(default_factory=time.time)
    last_seen: float = Field(default_factory=time.time)
    manufacturer_data: Dict[str, Any] = Field(default_factory=dict)
    service_data: Dict[str, Any] = Field(default_factory=dict)
    service_uuids: List[str] = Field(default_factory=list)
    appearance: Optional[int] = None
    tx_power: Optional[int] = None
    is_connectable: Optional[bool] = None
    address_type: Optional[str] = None
    local_name: Optional[str] = None
    isMock: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the Pydantic model to a dictionary."""
        result = self.model_dump()
        
        # Clean up None values for cleaner output
        return {k: v for k, v in result.items() if v is not None}
    
    @classmethod
    def from_bleak_device(cls, device, advertisement_data=None, is_mock=False):
        """Create a BLEDeviceInfo from a Bleak device and advertisement data."""
        # Handle the case when advertisement_data is not provided
        if advertisement_data is None:
            return cls(
                address=device.address,
                name=device.name or "Unknown Device",
                rssi=getattr(device, "rssi", -100),
                isMock=is_mock
            )
        
        # Create with advertisement data
        return cls(
            address=device.address,
            name=device.name or "Unknown Device",
            rssi=advertisement_data.rssi,
            manufacturer_data=getattr(advertisement_data, "manufacturer_data", {}),
            service_data=getattr(advertisement_data, "service_data", {}),
            service_uuids=getattr(advertisement_data, "service_uuids", []),
            appearance=getattr(advertisement_data, "appearance", None),
            tx_power=getattr(advertisement_data, "tx_power", None),
            is_connectable=getattr(advertisement_data, "is_connectable", None),
            isMock=is_mock
        )
        
# Add these models to your existing ble_models.py file

# Request Models
class WriteRequest(BaseModel):
    """Request model for writing to a characteristic."""
    characteristic: str
    value: str
    value_type: Optional[str] = "auto"
    response: Optional[bool] = True

class ServiceFilterRequest(BaseModel):
    """Request model for filtering services."""
    services: List[str] = Field(default_factory=list, description="List of service UUIDs to filter by")

class DevicePairRequest(BaseModel):
    """Request model for pairing with a device."""
    address: str
    timeout: Optional[float] = 10.0

class DeviceBondRequest(BaseModel):
    """Request model for bonding with a device."""
    address: str
    name: Optional[str] = None
    device_type: Optional[str] = None
    is_trusted: bool = True

# Update the existing ScanParams model to include camelCase parameters
class ScanParams(BaseModel):
    """Parameters for BLE device scanning."""
    scan_time: float = Field(5.0, description="Duration to scan in seconds")
    scanTime: Optional[float] = Field(None, description="Duration to scan in seconds (camelCase version)") # Alias for compatibility
    active: bool = Field(True, description="Whether to use active scanning")
    name_prefix: Optional[str] = Field(None, description="Filter devices by name prefix") # Added field
    service_uuids: Optional[List[str]] = None
    mock: Optional[bool] = Field(None, description="If False, attempt real scanning")
    real_scan: Optional[bool] = Field(False, description="Force real device scanning")
    realScan: Optional[bool] = Field(None, description="Force real device scanning (camelCase version)")
    
    # Handle compatibility between snake_case and camelCase
    def __init__(self, **data):
        # If only camelCase version is provided, use it for snake_case
        if "scanTime" in data and "scan_time" not in data:
            data["scan_time"] = data["scanTime"]
        if "realScan" in data and "real_scan" not in data:
            data["real_scan"] = data["realScan"]
        super().__init__(**data)
    
    # Make sure values are consistent when accessed
    @property
    def effective_scan_time(self) -> float:
        """Get the effective scan time, considering both naming conventions."""
        return self.scan_time
    
    @property
    def effective_real_scan(self) -> bool:
        """Get the effective real_scan value, considering both naming conventions."""
        return self.real_scan or (self.realScan or False)
    
    
# -----------------------------------------------------------------------------

# Response Models
    
class DeviceStatusResponse(BaseModel):
    """Response model for device connection status."""
    connected: bool
    device: Optional[str] = None
    uptime: Optional[float] = None

class DeviceExistsResponse(BaseModel):
    """Response model for device existence check."""
    exists: bool
    connected: bool
    
# ============================================================================
# BLE Descriptor Models
# ============================================================================

class BleDescriptor(BaseModel):
    """BLE descriptor model."""
    uuid: str
    handle: Optional[int] = None
    description: Optional[str] = None
    value: Optional[Dict[str, Any]] = None


# ============================================================================
# Service Results Models
# ============================================================================

class DescriptorsResult(BaseModel):
    """Result model for descriptor listing."""
    service_uuid: str
    characteristic_uuid: str
    descriptors: List[BleDescriptor] = Field(default_factory=list)
    count: int = 0


class NotificationsResult(BaseModel):
    """Result model for active notifications."""
    characteristics: List[str] = Field(default_factory=list)
    count: int = 0


class BatteryServiceInfo(BaseModel):
    """Battery service information model."""
    available: bool = False
    level: Optional[int] = None
    last_updated: Optional[float] = None
    error: Optional[str] = None


class DeviceInformationServiceInfo(BaseModel):
    """Device Information service data model."""
    available: bool = False
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    serial: Optional[str] = None
    firmware: Optional[str] = None
    hardware: Optional[str] = None
    software: Optional[str] = None
    error: Optional[str] = None
    
# Add these models to your existing ble_models.py file

# ============================================================================
# Adapter Request Models
# ============================================================================

class AdapterSelectionRequest(BaseModel):
    """Request model for selecting an adapter."""
    id: str
    name: Optional[str] = None

class AdapterResetRequest(BaseModel):
    """Request model for resetting an adapter."""
    adapter_id: Optional[str] = None
    force: bool = False

class AdapterSelectRequest(BaseModel):
    """Request model for selecting a specific Bluetooth adapter."""
    id: Union[str, Dict[str, str]] = Field(..., description="The ID or address of the adapter to select")
    
    @validator('id')
    def validate_id(cls, v):
        if isinstance(v, dict) and 'id' not in v:
            raise ValueError("Invalid adapter ID format")
        return v
    
    @property
    def adapter_id(self) -> str:
        """Get the adapter ID regardless of input format."""
        if isinstance(self.id, dict) and 'id' in self.id:
            # If sent as {"id": "adapter-id"} from the frontend
            return str(self.id['id'])
        else:
            # If sent as a simple string
            return str(self.id)

class AdapterSelectResponse(BaseModel):
    """Response model for adapter selection results."""
    status: str = Field(..., description="Result status of the operation")
    adapter: Dict[str, Any] = Field(..., description="The selected adapter information")
    message: str = Field(None, description="Additional information about the result")

# ============================================================================
# System Health Models
# ============================================================================

class BluetoothHealthReport(BaseModel):
    """Bluetooth health report model."""
    timestamp: float = Field(default_factory=time.time)
    adapter_status: Dict[str, Any] = Field(default_factory=dict)
    system_resources: Dict[str, Any] = Field(default_factory=dict)
    ble_operations: Dict[str, Any] = Field(default_factory=dict)
    connection_status: Dict[str, Any] = Field(default_factory=dict)
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    
# Add these notification models to your existing ble_models.py file

# ============================================================================
# Notification Models
# ============================================================================

class NotificationEvent(BaseModel):
    """Model for a notification event."""
    characteristic_uuid: str
    timestamp: float = Field(default_factory=time.time)
    value: Optional[CharacteristicValue] = None

class NotificationHistory(BaseModel):
    """Model for notification history results."""
    events: List[NotificationEvent] = Field(default_factory=list)
    count: int = 0
    characteristic_uuid: Optional[str] = None

    
# Add these health and diagnostics models to your existing ble_models.py file

# ============================================================================
# BLE Stack and System Models
# ============================================================================

class StackInfo(BaseModel):
    """Bluetooth stack information model."""
    platform: Dict[str, Any] = Field(default_factory=dict)
    bleak_version: Optional[str] = None
    backend: Optional[str] = None
    driver_info: Dict[str, Any] = Field(default_factory=dict)
    system_libraries: Dict[str, Any] = Field(default_factory=dict)
    capabilities: List[str] = Field(default_factory=list)

class ResetResponse(BaseModel):
    """Response from Bluetooth reset operation."""
    success: bool = False
    message: str = ""
    adapter_status: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    actions_taken: List[str] = Field(default_factory=list)

class MetricsResponse(BaseModel):
    """Response for metrics retrieval."""
    metric_type: str
    operation_metrics: List[Dict[str, Any]] = Field(default_factory=list)
    device_metrics: List[Dict[str, Any]] = Field(default_factory=list)
    adapter_metrics: List[Dict[str, Any]] = Field(default_factory=list)
    system_metrics: List[Dict[str, Any]] = Field(default_factory=list)
    counts: Dict[str, int] = Field(default_factory=dict)
    summary: Dict[str, Any] = Field(default_factory=dict)

class DiagnosticRequest(BaseModel):
    """Request model for running diagnostics."""
    check_adapter: bool = True
    test_scan: bool = True
    scan_duration: float = 3.0
    deep_hardware_check: bool = False
    check_system: bool = True

class DiagnosticResult(BaseModel):
    """Result of diagnostic tests."""
    timestamp: float = Field(default_factory=time.time)
    success: bool = False
    tests: List[Dict[str, Any]] = Field(default_factory=list)
    issues: List[str] = Field(default_factory=list)
    hardware_status: Dict[str, Any] = Field(default_factory=dict)
    stack_status: Dict[str, Any] = Field(default_factory=dict)
    recommendations: List[str] = Field(default_factory=list)
    
# Add this class to your existing ble_models.py file

class ConnectionParams(BaseModel):
    """
    Parameters for BLE device connection.
    
    Attributes:
        address: Device MAC address to connect to
        timeout: Connection timeout in seconds
        auto_reconnect: Whether to automatically reconnect on unexpected disconnection
        remember_device: Whether to remember the device for future connections
        use_cached_services: Whether to use cached services when available
        use_bluetooth_le_device: Windows-specific option for connection method
    """
    address: Optional[str] = None
    timeout: float = 10.0
    auto_reconnect: bool = True
    remember_device: bool = True
    use_cached_services: bool = True
    retry_count: int = 3
    retry_interval: float = 2.0
    max_reconnect_attempts: int = 5
    
    # Platform-specific options
    use_bluetooth_le_device: bool = True  # Windows-specific
    
    model_config = {
        'protected_namespaces': ()  # Fix for the warning about model_number
    }

# Ensure this is in the models file to clarify the naming
# Use ConnectionParams as the standard name since this appears to be used more widely
class ConnectionParams(BaseModel):
    """BLE connection parameters model."""
    address: Optional[str] = None
    timeout: float = 10.0
    auto_reconnect: bool = True
    remember_device: bool = True
    use_cached_services: bool = True
    retry_count: int = 3
    retry_interval: float = 2.0
    max_reconnect_attempts: int = 5
    use_bluetooth_le_device: bool = True  # Windows-specific
    
    model_config = {
        'protected_namespaces': ()
    }


class DeviceResponse (BaseModel):
    """Response model for device operations."""
    status: str
    address: Optional[str] = None
    services: List[BleService] = Field(default_factory=list)
    service_count: int = 0
    error: Optional[str] = None

# Add ConnectParams as an alias for backward compatibility
ConnectParams = ConnectionParams