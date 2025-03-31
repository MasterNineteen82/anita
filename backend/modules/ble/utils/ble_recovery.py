"""
BLE Error Recovery Module.

This module provides recovery mechanisms for common BLE errors:
- Automatic reconnection strategies
- Adapter reset procedures
- Stack recovery methods
- Platform-specific fixes
"""

import logging
import time
import asyncio
from typing import Dict, Any, Callable, List, Coroutine, Optional, Union

# Import the SystemMonitor from our new location
from backend.modules.ble.utils.system_monitor import SystemMonitor, get_system_monitor
from backend.modules.ble.utils.events import ble_event_bus

logger = logging.getLogger(__name__)

class BleErrorRecovery:
    """
    BLE error recovery and management system.
    Provides methods to recover from common BLE errors and track error statistics.
    """
    
    def __init__(self, logger=None):
        """
        Initialize the BLE error recovery system.
        
        Args:
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        self._system_monitor = None
        self.recovery_attempts = {}
        self.max_recovery_attempts = 3
        self.recovery_backoff = [1, 5, 15]  # Seconds between attempts
        
        # Track errors by type
        self.error_counts = {}
        self.last_errors = {}
        
        # Recovery strategies by error type
        self.recovery_strategies = {
            "connection_timeout": self._recover_connection_timeout,
            "adapter_error": self._recover_adapter_error,
            "gatt_error": self._recover_gatt_error,
            "device_disconnected": self._recover_device_disconnected,
            "characteristic_not_found": self._recover_characteristic_not_found,
            "permission_denied": self._recover_permission_denied,
            "pairing_failed": self._recover_pairing_failed
        }
    
    def _get_system_monitor(self) -> 'SystemMonitor':
        """Get the system monitor instance."""
        if self._system_monitor is None:
            self._system_monitor = get_system_monitor()
        return self._system_monitor

    async def diagnose_connection_issues(self, device_address: Optional[str] = None) -> Dict[str, Any]:
        """
        Diagnose connection issues with a device.
        
        Args:
            device_address: Optional address of the device to diagnose
            
        Returns:
            Dict with diagnostic information
        """
        try:
            # Get system monitor
            monitor = self._get_system_monitor()
            
            # Run system diagnostics
            system_diag = await monitor.run_diagnostics(deep_check=True)
            
            # Get adapter status
            adapter_status = await monitor._get_adapter_status()
            
            # Analyze device-specific issues if address provided
            device_issues = []
            if device_address:
                # Check recent errors for this device
                device_errors = [
                    {"type": error_type, "time": error_data["time"], "message": error_data["message"]}
                    for error_type, error_data in self.last_errors.items()
                    if error_data.get("device_address") == device_address
                ]
                
                # Check recovery attempts
                recovery_history = self.recovery_attempts.get(device_address, [])
                
                device_diag = {
                    "address": device_address,
                    "recent_errors": device_errors,
                    "recovery_attempts": len(recovery_history),
                    "recent_recoveries": recovery_history[-5:] if recovery_history else []
                }
            else:
                device_diag = None
            
            # Compile diagnostic results
            diagnostics = {
                "timestamp": time.time(),
                "adapter_status": adapter_status,
                "system_health": {
                    "cpu_usage": system_diag.get("system_resources", {}).get("cpu_percent"),
                    "memory_usage": system_diag.get("system_resources", {}).get("memory_percent"),
                    "bluetooth_service": adapter_status.get("service_running", False)
                },
                "platform_diagnostics": system_diag.get("platform_diagnostics", {}),
                "device_diagnostics": device_diag,
                "error_counts": self.error_counts,
                "recommendations": self._generate_recommendations(adapter_status, system_diag, device_diag)
            }
            
            return diagnostics
        
        except Exception as e:
            self.logger.error(f"Error diagnosing connection issues: {e}", exc_info=True)
            return {
                "timestamp": time.time(),
                "error": str(e),
                "recommendations": ["Check system logs for more information"]
            }
    
    def _generate_recommendations(
        self, 
        adapter_status: Dict[str, Any], 
        system_diag: Dict[str, Any],
        device_diag: Optional[Dict[str, Any]]
    ) -> List[str]:
        """Generate recommendations based on diagnostics."""
        recommendations = []
        
        # Adapter recommendations
        if not adapter_status.get("available", False):
            recommendations.append("Bluetooth adapter is not available - check if it's enabled")
            
            if adapter_status.get("service_running", False) == False:
                recommendations.append("Bluetooth service is not running - try restarting the service")
                
        elif not adapter_status.get("powered", True):
            recommendations.append("Bluetooth adapter is not powered on - turn it on in system settings")
        
        # System recommendations
        system_resources = system_diag.get("system_resources", {})
        if system_resources.get("cpu_percent", 0) > 80:
            recommendations.append("High CPU usage detected - close other applications to improve performance")
            
        if system_resources.get("memory_percent", 0) > 90:
            recommendations.append("High memory usage detected - close other applications to improve stability")
        
        # Device recommendations
        if device_diag:
            if len(device_diag.get("recent_errors", [])) > 0:
                recommendations.append("Device has recent errors - try turning it off and on again")
                
            if device_diag.get("recovery_attempts", 0) >= self.max_recovery_attempts:
                recommendations.append(
                    "Multiple recovery attempts have failed - consider removing the device "
                    "from your Bluetooth settings and pairing it again"
                )
        
        # General recommendations if no specific issues found
        if not recommendations:
            recommendations.append("No specific issues detected - ensure the device is in range and powered on")
            recommendations.append("Check that the device is not connected to another system")
        
        return recommendations
    
    async def recover_from_error(
        self, 
        error_type: str, 
        device_address: Optional[str] = None,
        error_details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Attempt to recover from a BLE error.
        
        Args:
            error_type: Type of error to recover from
            device_address: Optional device address related to the error
            error_details: Optional additional error details
            
        Returns:
            Dict with recovery result information
        """
        try:
            # Track the error
            self._track_error(error_type, device_address, error_details)
            
            # Check if we have a recovery strategy for this error
            if error_type not in self.recovery_strategies:
                return {
                    "success": False,
                    "message": f"No recovery strategy for error type: {error_type}",
                    "error_type": error_type,
                    "device_address": device_address
                }
            
            # Get recovery attempts for this device
            device_key = device_address or "global"
            if device_key not in self.recovery_attempts:
                self.recovery_attempts[device_key] = []
            
            attempts = len(self.recovery_attempts[device_key])
            
            # Check if we've exceeded max attempts
            if attempts >= self.max_recovery_attempts:
                return {
                    "success": False,
                    "message": "Maximum recovery attempts exceeded",
                    "error_type": error_type,
                    "device_address": device_address,
                    "attempts": attempts
                }
            
            # Calculate backoff time
            backoff_index = min(attempts, len(self.recovery_backoff) - 1)
            backoff_time = self.recovery_backoff[backoff_index]
            
            # Log the recovery attempt
            self.logger.info(
                f"Attempting recovery for {error_type} error" +
                (f" on device {device_address}" if device_address else "") +
                f" (attempt {attempts + 1}/{self.max_recovery_attempts}, backoff: {backoff_time}s)"
            )
            
            # Wait for backoff time
            await asyncio.sleep(backoff_time)
            
            # Execute the recovery strategy
            recovery_strategy = self.recovery_strategies[error_type]
            result = await recovery_strategy(device_address, error_details)
            
            # Record the attempt
            timestamp = time.time()
            attempt_record = {
                "timestamp": timestamp,
                "error_type": error_type,
                "success": result.get("success", False),
                "message": result.get("message", ""),
                "device_address": device_address
            }
            self.recovery_attempts[device_key].append(attempt_record)
            
            # Limit the history size
            if len(self.recovery_attempts[device_key]) > 20:
                self.recovery_attempts[device_key] = self.recovery_attempts[device_key][-20:]
            
            # Emit event for recovery attempt
            ble_event_bus.emit("recovery_attempt", attempt_record)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error during recovery attempt: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"Recovery failed with error: {str(e)}",
                "error_type": error_type,
                "device_address": device_address,
                "exception": str(e)
            }
    
    def _track_error(
        self, 
        error_type: str, 
        device_address: Optional[str] = None,
        error_details: Optional[Dict[str, Any]] = None
    ):
        """Track an error for statistics."""
        # Increment error count
        if error_type not in self.error_counts:
            self.error_counts[error_type] = 0
        
        self.error_counts[error_type] += 1
        
        # Record the error details
        self.last_errors[error_type] = {
            "time": time.time(),
            "device_address": device_address,
            "message": error_details.get("message", "") if error_details else "",
            "count": self.error_counts[error_type]
        }
        
        # Emit error event
        ble_event_bus.emit("ble_error", {
            "type": error_type,
            "device_address": device_address,
            "details": error_details,
            "time": time.time()
        })
    
    async def clear_error_history(self, device_address: Optional[str] = None):
        """
        Clear error and recovery history.
        
        Args:
            device_address: If provided, clear only for this device
        """
        if device_address:
            # Clear just for this device
            device_key = device_address
            if device_key in self.recovery_attempts:
                del self.recovery_attempts[device_key]
            
            # Clear device from last_errors
            for error_type in list(self.last_errors.keys()):
                if self.last_errors[error_type].get("device_address") == device_address:
                    del self.last_errors[error_type]
        else:
            # Clear all history
            self.recovery_attempts = {}
            self.last_errors = {}
            self.error_counts = {}
    
    # ==========================================================================
    # Recovery strategies
    # ==========================================================================
    
    async def _recover_connection_timeout(
        self, 
        device_address: Optional[str],
        error_details: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Recover from a connection timeout."""
        try:
            # First check system Bluetooth status
            system_monitor = self._get_system_monitor()
            adapter_status = await system_monitor._get_adapter_status()
            
            if not adapter_status.get("available", False):
                return {
                    "success": False,
                    "message": "Cannot recover: Bluetooth adapter is not available",
                    "recommend_adapter_reset": True
                }
            
            # Emit event for potential listeners (like the BLE service)
            ble_event_bus.emit("recovery_action", {
                "action": "retry_connection",
                "device_address": device_address,
                "error_type": "connection_timeout"
            })
            
            # Note: The actual reconnection will be handled by listeners
            # We just return success to indicate the recovery procedure initiated
            
            return {
                "success": True,
                "message": "Recovery procedure initiated: retry connection",
                "device_address": device_address
            }
        except Exception as e:
            self.logger.error(f"Error recovering from connection timeout: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"Recovery failed: {str(e)}",
                "device_address": device_address
            }
    
    async def _recover_adapter_error(
        self, 
        device_address: Optional[str],
        error_details: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Recover from an adapter error."""
        try:
            # Emit event to reset the adapter
            ble_event_bus.emit("recovery_action", {
                "action": "reset_adapter",
                "device_address": device_address,
                "error_type": "adapter_error"
            })
            
            # Wait for reset to potentially take effect
            await asyncio.sleep(2)
            
            return {
                "success": True,
                "message": "Recovery procedure initiated: adapter reset",
                "device_address": device_address
            }
        except Exception as e:
            self.logger.error(f"Error recovering from adapter error: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"Recovery failed: {str(e)}",
                "device_address": device_address
            }
    
    async def _recover_gatt_error(
        self, 
        device_address: Optional[str],
        error_details: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Recover from a GATT operation error."""
        try:
            # Most GATT errors require reconnection
            ble_event_bus.emit("recovery_action", {
                "action": "reconnect",
                "device_address": device_address,
                "error_type": "gatt_error",
                "clear_cache": True
            })
            
            # Wait for reconnection to potentially take effect
            await asyncio.sleep(2)
            
            return {
                "success": True,
                "message": "Recovery procedure initiated: reconnect with cache clear",
                "device_address": device_address
            }
        except Exception as e:
            self.logger.error(f"Error recovering from GATT error: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"Recovery failed: {str(e)}",
                "device_address": device_address
            }
    
    async def _recover_device_disconnected(
        self, 
        device_address: Optional[str],
        error_details: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Recover from an unexpected device disconnection."""
        try:
            # Check how many times this has happened
            device_key = device_address or "global"
            disconnection_count = 0
            
            for attempt in self.recovery_attempts.get(device_key, []):
                if attempt.get("error_type") == "device_disconnected":
                    disconnection_count += 1
            
            # If too many disconnections, suggest adapter reset
            if disconnection_count >= 2:
                ble_event_bus.emit("recovery_action", {
                    "action": "reset_adapter",
                    "device_address": device_address,
                    "error_type": "device_disconnected",
                    "disconnect_count": disconnection_count
                })
                
                await asyncio.sleep(3)  # Give more time for adapter reset
                
                return {
                    "success": True,
                    "message": "Recovery procedure initiated: adapter reset due to multiple disconnections",
                    "device_address": device_address
                }
            else:
                # Just try to reconnect
                ble_event_bus.emit("recovery_action", {
                    "action": "reconnect",
                    "device_address": device_address,
                    "error_type": "device_disconnected"
                })
                
                await asyncio.sleep(2)
                
                return {
                    "success": True,
                    "message": "Recovery procedure initiated: reconnect",
                    "device_address": device_address
                }
        except Exception as e:
            self.logger.error(f"Error recovering from device disconnection: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"Recovery failed: {str(e)}",
                "device_address": device_address
            }
    
    async def _recover_characteristic_not_found(
        self, 
        device_address: Optional[str],
        error_details: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Recover from characteristic not found error."""
        try:
            # Need to rediscover services
            ble_event_bus.emit("recovery_action", {
                "action": "rediscover_services",
                "device_address": device_address,
                "error_type": "characteristic_not_found",
                "characteristic_uuid": error_details.get("characteristic_uuid") if error_details else None
            })
            
            await asyncio.sleep(3)  # Give more time for service discovery
            
            return {
                "success": True,
                "message": "Recovery procedure initiated: rediscover services",
                "device_address": device_address
            }
        except Exception as e:
            self.logger.error(f"Error recovering from characteristic not found: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"Recovery failed: {str(e)}",
                "device_address": device_address
            }
    
    async def _recover_permission_denied(
        self, 
        device_address: Optional[str],
        error_details: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Recover from permission denied errors."""
        try:
            # Permission issues often require pairing/authentication
            ble_event_bus.emit("recovery_action", {
                "action": "pair_device",
                "device_address": device_address,
                "error_type": "permission_denied"
            })
            
            await asyncio.sleep(5)  # Give more time for pairing
            
            return {
                "success": True,
                "message": "Recovery procedure initiated: attempt pairing",
                "device_address": device_address
            }
        except Exception as e:
            self.logger.error(f"Error recovering from permission denied: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"Recovery failed: {str(e)}",
                "device_address": device_address
            }
    
    async def _recover_pairing_failed(
        self, 
        device_address: Optional[str],
        error_details: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Recover from pairing failures."""
        try:
            # For pairing failures, we need to clear bonding data and try again
            ble_event_bus.emit("recovery_action", {
                "action": "remove_bond",
                "device_address": device_address,
                "error_type": "pairing_failed",
                "retry_pair": True
            })
            
            await asyncio.sleep(3)
            
            return {
                "success": True,
                "message": "Recovery procedure initiated: remove bond and retry pairing",
                "device_address": device_address
            }
        except Exception as e:
            self.logger.error(f"Error recovering from pairing failure: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"Recovery failed: {str(e)}",
                "device_address": device_address
            }

# Create a singleton instance
_error_recovery = None

def get_error_recovery() -> BleErrorRecovery:
    """Get the BleErrorRecovery singleton instance."""
    global _error_recovery
    if _error_recovery is None:
        _error_recovery = BleErrorRecovery()
    return _error_recovery