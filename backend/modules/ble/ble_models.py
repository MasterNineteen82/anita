from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Set, Any

class ScanOptions(BaseModel):
    """Options for BLE device scanning."""
    duration: int = Field(default=5, ge=1, le=30, description="Scan duration in seconds")
    activeMode: bool = Field(default=False, description="Whether to use active scanning")
    filterDuplicates: bool = Field(default=True, description="Whether to filter duplicate devices")

class ConnectionOptions(BaseModel):
    """Options for BLE device connection."""
    autoReconnect: bool = Field(default=True, description="Whether to automatically reconnect")
    timeout: Optional[int] = Field(default=10, ge=1, le=30, description="Connection timeout in seconds")

class WriteOptions(BaseModel):
    """Options for writing to a characteristic."""
    value: str = Field(..., description="Hex value to write")
    withResponse: bool = Field(default=True, description="Whether to require a response")

class BatteryInfo(BaseModel):
    """Information about device battery."""
    level: int = Field(..., ge=0, le=100, description="Battery level percentage")
    deviceId: str = Field(..., description="Device address")

class StatusResponse(BaseModel):
    """Generic status response."""
    status: str = Field(..., description="Operation status")
    message: str = Field(..., description="Status message")

class ErrorResponse(BaseModel):
    """Error response."""
    detail: str = Field(..., description="Error details")

class BLEDeviceInfo(BaseModel):
    """BLE device information."""
    name: str = Field(..., description="Device name")
    address: str = Field(..., description="Device address")
    rssi: Optional[int] = Field(None, description="Signal strength in dBm")
    bonded: Optional[bool] = Field(None, description="Whether the device is bonded")
    manufacturer_data: Optional[Dict[str, Any]] = Field(None, description="Manufacturer data")
    service_data: Optional[Dict[str, Any]] = Field(None, description="Service data")
    service_uuids: Optional[List[str]] = Field(None, description="Service UUIDs")

class ServiceInfo(BaseModel):
    """BLE service information."""
    uuid: str = Field(..., description="Service UUID")
    description: str = Field(..., description="Service description")

class CharacteristicInfo(BaseModel):
    """BLE characteristic information."""
    uuid: str = Field(..., description="Characteristic UUID")
    description: str = Field(..., description="Characteristic description")
    properties: List[str] = Field(..., description="Characteristic properties")
    service_uuid: str = Field(..., description="Parent service UUID")

class CharacteristicValue(BaseModel):
    """Characteristic value with decoded representation."""
    uuid: str = Field(..., description="Characteristic UUID")
    value: str = Field(..., description="Raw value as hex string")
    decoded: Any = Field(None, description="Decoded value if known format")

class ConnectionResponse(BaseModel):
    status: str
    address: str
    connection_time: float

class ConnectionParams(BaseModel):
    timeout: int = Field(default=10, description="Connection timeout in seconds")
    autoReconnect: bool = Field(default=True, description="Whether to auto-reconnect")
    retryCount: int = Field(default=2, description="Number of connection retries")
    
class BLEDeviceState(BaseModel):
    """Current state of a BLE device."""
    address: str = Field(..., description="Device address")
    name: Optional[str] = Field(None, description="Device name")
    connected: bool = Field(..., description="Whether the device is currently connected")
    rssi: Optional[int] = Field(None, description="Current signal strength in dBm")
    bonded: Optional[bool] = Field(None, description="Whether the device is bonded")
    services: List[ServiceInfo] = Field(default_factory=list, description="Available services")
    characteristics: List[CharacteristicInfo] = Field(default_factory=list, description="Available characteristics")
    last_updated: Optional[str] = Field(None, description="Timestamp of last state update")
    
class BLEDeviceConnection(BaseModel):
    """Model representing a BLE device connection response."""
    address: str
    status: str = "connected"  # "connected", "already_connected", "connected_after_recovery"
    services: Dict[str, Any] = {}
    mtu: int = 23
    message: str = ""

class BLEDeviceStorage(BaseModel):
    """BLE device storage."""
    devices: Dict[str, BLEDeviceState] = Field(default_factory=dict, description="Stored device states")
