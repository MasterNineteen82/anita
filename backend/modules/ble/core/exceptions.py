"""
BLE exception types.

This module defines the exception hierarchy used throughout the BLE module.
Specific exception types help with identifying and handling different
error conditions in a structured way.
"""

import traceback
from typing import Dict, Any, Optional

class BleError(Exception):
    """Base exception for all BLE-related errors."""
    
    def __init__(
        self, 
        message: str, 
        device_address: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize a BLE error.
        
        Args:
            message: Error message
            device_address: Optional device address related to the error
            context: Optional additional context information
        """
        self.message = message
        self.device_address = device_address
        self.context = context or {}
        self.traceback = traceback.format_exc()
        
        # Format the error message
        full_message = message
        if device_address:
            full_message = f"[Device: {device_address}] {full_message}"
            
        super().__init__(full_message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the exception to a dictionary for serialization."""
        return {
            "type": self.__class__.__name__,
            "message": self.message,
            "device_address": self.device_address,
            "context": self.context,
            "traceback": self.traceback
        }

class BleConnectionError(BleError):
    """
    Raised when there's an error establishing or maintaining a connection.
    
    Examples:
    - Device not found
    - Connection timeout
    - Device disconnected unexpectedly
    - Authentication failed
    """
    pass

class BleServiceError(BleError):
    """
    Raised when there's an error with GATT services or characteristics.
    
    Examples:
    - Service not found
    - Characteristic not found
    - Read/write operations failed
    - Notification errors
    """
    pass

class BleAdapterError(BleError):
    """
    Raised when there's an error with the Bluetooth adapter.
    
    Examples:
    - Adapter not found
    - Adapter not powered on
    - Adapter permission issues
    - Hardware failure
    """
    pass

class BleNotSupportedError(BleError):
    """
    Raised when an operation is not supported by the device or platform.
    
    Examples:
    - Feature not supported by device
    - Platform limitation
    - Incompatible device
    """
    pass

class BleOperationError(BleError):
    """
    Raised for general BLE operation errors.
    
    Examples:
    - Scan errors
    - Operation timeout
    - Invalid parameters
    - Resource constraints
    """
    pass

class BleSecurityError(BleError):
    """
    Raised for security-related errors.
    
    Examples:
    - Encryption failed
    - Authentication rejected
    - Insufficient permissions
    - Pairing failed
    """
    pass

class BleCommunicationError(BleError):
    """
    Raised for communication protocol errors.
    
    Examples:
    - Invalid response format
    - Command rejected by device
    - Communication timeout
    - Protocol violation
    """
    pass

class BleResourceError(BleError):
    """
    Raised when system resources are unavailable.
    
    Examples:
    - Too many connections
    - Out of memory
    - Resource busy
    - System constraints
    """
    
    def __init__(
        self, 
        message: str, 
        device_address: Optional[str] = None,
        resource_type: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize a resource error.
        
        Args:
            message: Error message
            device_address: Optional device address related to the error
            resource_type: Optional resource type that is unavailable
            context: Optional additional context information
        """
        context = context or {}
        if resource_type:
            context["resource_type"] = resource_type
            
        super().__init__(message, device_address, context)

# Helper functions for creating exceptions with context
def create_connection_error(
    message: str, 
    device_address: Optional[str] = None,
    operation: Optional[str] = None,
    **kwargs
) -> BleConnectionError:
    """
    Create a connection error with context.
    
    Args:
        message: Error message
        device_address: Device address
        operation: Operation that failed
        **kwargs: Additional context data
        
    Returns:
        BleConnectionError instance
    """
    context = {"operation": operation, **kwargs} if operation else kwargs
    return BleConnectionError(message, device_address, context)

def create_service_error(
    message: str, 
    device_address: Optional[str] = None,
    service_uuid: Optional[str] = None,
    characteristic_uuid: Optional[str] = None,
    operation: Optional[str] = None,
    **kwargs
) -> BleServiceError:
    """
    Create a service error with context.
    
    Args:
        message: Error message
        device_address: Device address
        service_uuid: Service UUID
        characteristic_uuid: Characteristic UUID
        operation: Operation that failed
        **kwargs: Additional context data
        
    Returns:
        BleServiceError instance
    """
    context = kwargs.copy()
    if service_uuid:
        context["service_uuid"] = service_uuid
    if characteristic_uuid:
        context["characteristic_uuid"] = characteristic_uuid
    if operation:
        context["operation"] = operation
        
    return BleServiceError(message, device_address, context)

def create_adapter_error(
    message: str, 
    adapter_address: Optional[str] = None,
    operation: Optional[str] = None,
    **kwargs
) -> BleAdapterError:
    """
    Create an adapter error with context.
    
    Args:
        message: Error message
        adapter_address: Adapter address
        operation: Operation that failed
        **kwargs: Additional context data
        
    Returns:
        BleAdapterError instance
    """
    context = {"operation": operation, **kwargs} if operation else kwargs
    return BleAdapterError(message, adapter_address, context)

def is_connection_error(exception: Exception) -> bool:
    """
    Check if an exception is a connection error.
    
    This includes BleConnectionError and some BleakError types
    that indicate connection problems.
    
    Args:
        exception: Exception to check
        
    Returns:
        True if it's a connection error
    """
    from bleak import BleakError
    
    if isinstance(exception, BleConnectionError):
        return True
        
    if isinstance(exception, BleakError):
        error_str = str(exception).lower()
        connection_indicators = [
            "disconnected", "connection", "timeout", 
            "not connected", "not found", "device not found"
        ]
        return any(indicator in error_str for indicator in connection_indicators)
        
    return False

def extract_error_context(exception: Exception) -> Dict[str, Any]:
    """
    Extract context information from an exception.
    
    Args:
        exception: Exception to extract context from
        
    Returns:
        Dictionary with error context
    """
    if isinstance(exception, BleError):
        return exception.to_dict()
        
    return {
        "type": exception.__class__.__name__,
        "message": str(exception),
        "traceback": traceback.format_exc()
    }