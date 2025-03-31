"""
BLE Models Package.

This package contains all Pydantic models used in the BLE module:
- Device and connection models
- Service and characteristic models
- Message and communication models
- Notification models
- Health and diagnostic models

Usage:
    from backend.modules.ble.models import BLEDeviceInfo, ConnectionParams, MessageType
    
    # Create a device info model
    device = BLEDeviceInfo(
        address="00:11:22:33:44:55",
        name="My BLE Device",
        rssi=-65
    )
    
    # Access enum values
    message_type = MessageType.SCAN_RESULT
"""

import time
from enum import Enum, auto
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field

# Re-export all models from ble_models.py
from .ble_models import (
    # Device Models
    BLEDeviceInfo,
    ConnectionParams,  # Add this import
    ConnectionResult,
    ConnectionStatus,
    
    # Service Models
    BleService,
    BleCharacteristic,
    BleDescriptor,
    ServicesResult,
    CharacteristicsResult,
    DescriptorsResult,
    
    # Value Models
    CharacteristicValue,
    ReadResult,
    WriteRequest,
    WriteParams,
    
    # Notification Models
    NotificationRequest,
    NotificationSubscription,
    NotificationsResult,
    NotificationEvent,
    NotificationHistory,
    NotificationMessage,
    
    # Adapter Models
    BleAdapter,
    AdapterResult,
    AdapterStatus,
    AdapterSelectionRequest,
    AdapterResetRequest,
    
    # Health Models
    SystemMetric,
    AdapterMetric,
    BluetoothHealthReport,
    StackInfo,
    ResetResponse,
    MetricsResponse,
    DiagnosticRequest,
    DiagnosticResult,
    
    # Message Models
    MessageType,
    BaseMessage,
    ScanRequestMessage,
    ScanResultMessage,
    ConnectRequestMessage,
    ConnectResultMessage,
    PingMessage,
    PongMessage,
    ErrorMessage,
    
    # Scan Models
    ScanParams,
    ServiceFilterRequest,
    
    # Pairing/Bonding Models
    DevicePairRequest,
    DeviceBondRequest,
    
    # Any other models from ble_models.py
)

# Package metadata
__version__ = "1.0.0"

# Define what should be importable directly from the package
__all__ = [
    # Device Models
    "BLEDeviceInfo",
    "ConnectionParams",  # Add this export
    "ConnectionResult",
    "ConnectionStatus",
    
    # Service Models
    "BleService",
    "BleCharacteristic",
    "BleDescriptor",
    "ServicesResult",
    "CharacteristicsResult",
    "DescriptorsResult",
    
    # Value Models
    "CharacteristicValue",
    "ReadResult",
    "WriteRequest",
    "WriteParams",
    
    # Notification Models
    "NotificationRequest",
    "NotificationSubscription",
    "NotificationsResult",
    "NotificationEvent",
    "NotificationHistory",
    "NotificationMessage",
    
    # Adapter Models
    "BleAdapter",
    "AdapterResult",
    "AdapterStatus",
    "AdapterSelectionRequest",
    "AdapterResetRequest",
    
    # Health Models
    "SystemMetric",
    "AdapterMetric",
    "BluetoothHealthReport",
    "StackInfo",
    "ResetResponse",
    "MetricsResponse",
    "DiagnosticRequest",
    "DiagnosticResult",
    
    # Message Models
    "MessageType",
    "BaseMessage",
    "ScanRequestMessage",
    "ScanResultMessage",
    "ConnectRequestMessage",
    "ConnectResultMessage",
    "PingMessage",
    "PongMessage",
    "ErrorMessage",
    
    # Scan Models
    "ScanParams",
    "ServiceFilterRequest",
    
    # Pairing/Bonding Models
    "DevicePairRequest",
    "DeviceBondRequest",
]

# Convenience functions
def create_error_model(error_message: str) -> ErrorMessage:
    """
    Create an error message model with the given error message.
    
    Args:
        error_message: The error message text
        
    Returns:
        An ErrorMessage model instance
    """
    return ErrorMessage(
        type=MessageType.ERROR,
        error=error_message
    )

def create_scan_result(devices: List[Dict[str, Any]]) -> ScanResultMessage:
    """
    Create a scan result message with the given devices.
    
    Args:
        devices: List of device information dictionaries
        
    Returns:
        A ScanResultMessage model instance
    """
    return ScanResultMessage(
        type=MessageType.SCAN_RESULT,
        devices=devices,
        count=len(devices)
    )

model_config = {
    'protected_namespaces': ()  # Disables the model_ namespace protection
}