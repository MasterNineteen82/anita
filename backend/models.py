from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

# API Models
class SuccessResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None

class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    details: Optional[Dict[str, Any]] = None

class StatusResponse(BaseModel):
    status: str
    message: str

class ReaderResponse(BaseModel):
    reader_name: str = Field(..., json_schema_extra={'example': "My Reader"})
    reader_type: str = Field(..., json_schema_extra={'example': "Serial"})

class ReadersResponse(BaseModel):
    readers: List[ReaderResponse]

# Hardware Models
class DeviceStatus(BaseModel):
    status: str = Field(..., json_schema_extra={'example': "online"})
    details: Optional[str] = Field(None, json_schema_extra={'example': "Device is functioning normally"})

class InterfaceType(BaseModel):
    interface_type: str = Field(..., json_schema_extra={'example': "USB"})
    description: Optional[str] = Field(None, json_schema_extra={'example': "Standard USB interface"})

class HardwareDevice(BaseModel):
    device_id: str = Field(..., json_schema_extra={'example': "device_123"})
    device_name: str = Field(..., json_schema_extra={'example': "My Device"})
    status: DeviceStatus
    interface: InterfaceType

class DeviceCapability(BaseModel):
    capability_name: str = Field(..., json_schema_extra={'example': "Read Mifare"})
    description: Optional[str] = Field(None, json_schema_extra={'example': "Able to read Mifare Classic cards"})

class ReaderDevice(BaseModel):
    reader_id: str = Field(..., json_schema_extra={'example': "reader_456"})
    reader_name: str = Field(..., json_schema_extra={'example': "My Reader"})
    device: HardwareDevice
    capabilities: List[DeviceCapability] = []

# System Models
class LogRequest(BaseModel):
    level: str
    message: str
    context: Optional[Dict[str, Any]] = None

class Settings(BaseModel):
    theme: str = "dark"
    logging_enabled: bool = True
    auto_refresh: bool = True
    refresh_interval: int = 5000
    simulation_mode: bool = False
    api_base_url: str = "http://localhost:8000/api"
    websocket_url: str = "ws://localhost:8000/ws/events"
    mifare_default_key: str = "FFFFFFFFFFFF"
    mifare_key_type: str = "A"
    plugin_directory: str = "plugins"
    enabled_plugins: list = []
    autodetect_reader: bool = True
    reader_check_interval: int = 5000

class LogResponse(BaseModel):
    status: str = Field(..., json_schema_extra={'example': "success"})

class SystemStatus(BaseModel):
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    network_status: str
    timestamp: float

class LogEntry(BaseModel):
    timestamp: float
    level: str
    message: str
    context: Optional[Dict[str, Any]] = None

# Mifare Models
class MifareKey(BaseModel):
    key_value: str

class MifareClassicSector(BaseModel):
    """MIFARE Classic sector data"""
    sector_number: int
    key_a: Optional[str] = None
    key_b: Optional[str] = None
    access_bits: Optional[str] = None
    data_blocks: Optional[List[str]] = None

class MifareDESFireApplication(BaseModel):
    """MIFARE DESFire application data"""
    aid: str
    file_ids: List[int]
    keys: Optional[Dict[str, str]] = None

# Config Models
class ConfigurationSetting(BaseModel):
    key: str = Field(..., json_schema_extra={'example': "api_base_url"})
    value: str = Field(..., json_schema_extra={'example': "http://localhost:8000/api"})
    description: Optional[str] = Field(None, json_schema_extra={'example': "Base URL for the API"})

class ConfigurationResponse(BaseModel):
    settings: List[ConfigurationSetting]

# Cache Models
class CacheItem(BaseModel):
    key: str
    value: Any
    expiration_time: Optional[float] = None

class CacheStats(BaseModel):
    hits: int
    misses: int
    size: int

class CachePolicy(BaseModel):
    max_size: int
    eviction_policy: str

# Card Models
class CardReadRequest(BaseModel):
    reader_name: str
    card_number: str

class CardWriteRequest(BaseModel):
    reader_name: str
    card_number: str
    data: str

class CardData(BaseModel):
    card_number: str
    data: str

# NFC Models
class NFCRecord(BaseModel):
    pass

class NFCMessage(BaseModel):
    pass

class NFCWifiCredentials(BaseModel):
    pass

class NFCTextRecord(BaseModel):
    pass

class NFCURLRecord(BaseModel):
    pass

# RFID Models
class RFIDTagResponse(BaseModel):
    pass

class RFIDTagInfo(BaseModel):
    pass

class RFIDReaderInfo(BaseModel):
    pass

# UWB Models
class UWBMode(BaseModel):
    pass

class UWBAnchor(BaseModel):
    pass

class UWBTag(BaseModel):
    pass

class UWBPosition(BaseModel):
    pass

class UWBRangingResult(BaseModel):
    pass

class RFIDTagDataRequest(BaseModel):
    pass

class RFIDConfigRequest(BaseModel):
    pass

# BLE Models
class BLEDeviceInfo(BaseModel):
    name: str
    address: str
    rssi: Optional[int] = None

class BLEService(BaseModel):
    uuid: str
    description: Optional[str] = None

class BLECharacteristic(BaseModel):
    uuid: str
    service_uuid: str
    properties: List[str]
    description: Optional[str] = None

class BLEConnectionStatus(BaseModel):
    connected: bool
    device_address: Optional[str] = None
    device_name: Optional[str] = None

class BLEServicesResponse(BaseModel):
    services: List[BLEService]

class BLECharacteristicsResponse(BaseModel):
    characteristics: List[BLECharacteristic]

class BLEValueResponse(BaseModel):
    value: str  # Hex-encoded value
    raw_value: Optional[str] = None  # For human-readable representation if available
    
class SmartcardReaderResponse(BaseModel):  
    status: str
    card_present: bool
    atr: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    
class SmartcardCommand(BaseModel):  
    command: str
    data: Optional[List[int]] = None

class SmartcardResponse(BaseModel):
    status: str
    message: str