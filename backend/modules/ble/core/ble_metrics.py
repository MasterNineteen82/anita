"""
BLE metrics collector module.

This module provides functionality for collecting and retrieving
performance metrics for BLE operations.
"""

import time
import logging
from typing import Dict, List, Any, Optional, Set
from collections import deque
import threading

# Import SystemMonitor for API compatibility
from backend.modules.ble.utils.system_monitor import SystemMonitor, get_system_monitor

logger = logging.getLogger(__name__)

class BleMetricsCollector:
    """
    Collector for BLE operation metrics.
    
    This class tracks various performance metrics:
    - Operation counts
    - Operation timings
    - Error counts
    - Connection statistics
    """
    
    def __init__(self, max_history: int = 1000):
        """
        Initialize the metrics collector.
        
        Args:
            max_history: Maximum number of timing entries to keep
        """
        self.max_history = max_history
        self._lock = threading.RLock()
        
        # Operation counts
        self.operation_counts = {
            "scan": 0,
            "connect": 0,
            "disconnect": 0,
            "read": 0,
            "write": 0,
            "subscribe": 0,
            "unsubscribe": 0,
            "discover_services": 0,
            "discover_characteristics": 0
        }
        
        # Error counts
        self.error_counts = {
            "connection_errors": 0,
            "adapter_errors": 0,
            "service_errors": 0,
            "operation_errors": 0,
            "timeout_errors": 0,
            "other_errors": 0
        }
        
        # Timing history (deques for fixed-size histories)
        self.operation_timings = {
            "scan": deque(maxlen=max_history),
            "connect": deque(maxlen=max_history),
            "disconnect": deque(maxlen=max_history),
            "read": deque(maxlen=max_history),
            "write": deque(maxlen=max_history),
            "subscribe": deque(maxlen=max_history),
            "discover_services": deque(maxlen=max_history),
            "discover_characteristics": deque(maxlen=max_history)
        }
        
        # Connection statistics
        self.connection_stats = {
            "total_connections": 0,
            "successful_connections": 0,
            "failed_connections": 0,
            "avg_connect_time": 0.0,
            "max_connect_time": 0.0,
            "current_connections": 0
        }
        
        # Device statistics
        self.device_stats = {
            "total_devices_discovered": 0,
            "unique_devices_discovered": set(),
            "most_connected_device": None,
            "device_connection_counts": {}
        }
        
        # Start time
        self.start_time = time.time()
    
    @property
    def system_monitor(self):
        """Get the system monitor instance."""
        return get_system_monitor()
    
    def record_operation(self, operation: str, duration: float, success: bool = True) -> None:
        """
        Record an operation with its duration.
        
        Args:
            operation: Operation type (scan, connect, etc.)
            duration: Duration in seconds
            success: Whether the operation succeeded
        """
        with self._lock:
            # Update counts
            if operation in self.operation_counts:
                self.operation_counts[operation] += 1
            
            # Record timing
            if operation in self.operation_timings:
                self.operation_timings[operation].append({
                    "timestamp": time.time(),
                    "duration": duration,
                    "success": success
                })
            
            # Special handling for connections
            if operation == "connect":
                self.connection_stats["total_connections"] += 1
                if success:
                    self.connection_stats["successful_connections"] += 1
                    self.connection_stats["current_connections"] += 1
                    
                    # Update average connect time
                    prev_avg = self.connection_stats["avg_connect_time"]
                    prev_count = self.connection_stats["successful_connections"] - 1
                    
                    if prev_count > 0:
                        self.connection_stats["avg_connect_time"] = (
                            (prev_avg * prev_count) + duration
                        ) / self.connection_stats["successful_connections"]
                    else:
                        self.connection_stats["avg_connect_time"] = duration
                    
                    # Update max connect time
                    if duration > self.connection_stats["max_connect_time"]:
                        self.connection_stats["max_connect_time"] = duration
                else:
                    self.connection_stats["failed_connections"] += 1
            
            # Handle disconnections
            elif operation == "disconnect" and success:
                if self.connection_stats["current_connections"] > 0:
                    self.connection_stats["current_connections"] -= 1
    
    def record_error(self, error_type: str) -> None:
        """
        Record an error occurrence.
        
        Args:
            error_type: Type of error
        """
        with self._lock:
            if error_type in self.error_counts:
                self.error_counts[error_type] += 1
            else:
                self.error_counts["other_errors"] += 1
    
    def record_device_discovered(self, device_address: str) -> None:
        """
        Record a device discovery.
        
        Args:
            device_address: Device address/ID
        """
        with self._lock:
            self.device_stats["total_devices_discovered"] += 1
            self.device_stats["unique_devices_discovered"].add(device_address)
    
    def record_device_connected(self, device_address: str) -> None:
        """
        Record a device connection.
        
        Args:
            device_address: Device address/ID
        """
        with self._lock:
            if device_address in self.device_stats["device_connection_counts"]:
                self.device_stats["device_connection_counts"][device_address] += 1
            else:
                self.device_stats["device_connection_counts"][device_address] = 1
            
            # Update most connected device
            most_connected = self.device_stats["most_connected_device"]
            if most_connected is None or (
                self.device_stats["device_connection_counts"][device_address] > 
                self.device_stats["device_connection_counts"].get(most_connected, 0)
            ):
                self.device_stats["most_connected_device"] = device_address
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get all collected metrics."""
        with self._lock:
            # Calculate uptime
            uptime = time.time() - self.start_time
            
            # Convert deque timings to lists for serialization
            operation_timings_serializable = {}
            for op, timings in self.operation_timings.items():
                operation_timings_serializable[op] = list(timings)
            
            # Convert set to list for serialization
            unique_devices = list(self.device_stats["unique_devices_discovered"])
            
            return {
                "uptime": uptime,
                "operation_counts": self.operation_counts.copy(),
                "error_counts": self.error_counts.copy(),
                "connection_stats": {
                    k: v for k, v in self.connection_stats.items() 
                    if k != "device_connection_counts"
                },
                "device_stats": {
                    "total_devices_discovered": self.device_stats["total_devices_discovered"],
                    "unique_devices_count": len(unique_devices),
                    "most_connected_device": self.device_stats["most_connected_device"],
                    "device_connection_counts": self.device_stats["device_connection_counts"].copy()
                },
                "timing_summary": self._calculate_timing_summary()
            }
    
    # Additional methods for API compatibility
    def get_adapter_metrics(self, adapter_id: Optional[str] = None, limit: int = 100) -> Dict[str, Any]:
        """
        Get metrics related to adapter operations.
        
        Args:
            adapter_id: Optional adapter ID to filter by
            limit: Maximum number of metrics to return
            
        Returns:
            Dict with adapter metrics and summary
        """
        with self._lock:
            return {
                "adapter_id": adapter_id or "all",
                "metrics": [],
                "summary": {
                    "operation_count": 0,
                    "error_count": 0
                }
            }
    
    def get_all_metrics(self, limit: int = 100) -> Dict[str, Any]:
        """
        Get all types of metrics.
        
        Args:
            limit: Maximum number of metrics to return per category
            
        Returns:
            Dict with all metrics categories
        """
        with self._lock:
            return {
                "operations": self._get_operation_metrics_list(limit),
                "devices": self._get_device_metrics_list(limit),
                "adapters": [],
                "system": self._get_system_metrics_list(),
                "summary": {
                    "uptime": time.time() - self.start_time,
                    "operation_count": sum(self.operation_counts.values()),
                    "error_count": sum(self.error_counts.values()),
                    "device_count": len(self.device_stats["unique_devices_discovered"])
                }
            }
    
    def get_operation_metrics(self, limit: int = 100) -> Dict[str, Any]:
        """
        Get operation metrics.
        
        Args:
            limit: Maximum number of metrics to return
            
        Returns:
            Dict with operation metrics and summary
        """
        with self._lock:
            return {
                "operations": self._get_operation_metrics_list(limit),
                "summary": self._calculate_timing_summary()
            }
    
    def get_device_metrics(self, limit: int = 100) -> Dict[str, Any]:
        """
        Get device-related metrics.
        
        Args:
            limit: Maximum number of metrics to return
            
        Returns:
            Dict with device metrics and summary
        """
        with self._lock:
            return {
                "devices": self._get_device_metrics_list(limit),
                "summary": {
                    "total_discovered": self.device_stats["total_devices_discovered"],
                    "unique_discovered": len(self.device_stats["unique_devices_discovered"]),
                    "most_connected": self.device_stats["most_connected_device"]
                }
            }
    
    def clear_all_metrics(self) -> None:
        """Clear all metrics."""
        self.reset_metrics()
    
    def clear_operation_metrics(self) -> None:
        """Clear operation metrics."""
        with self._lock:
            for key in self.operation_counts:
                self.operation_counts[key] = 0
            for key in self.operation_timings:
                self.operation_timings[key].clear()
    
    def clear_device_metrics(self) -> None:
        """Clear device metrics."""
        with self._lock:
            self.device_stats["total_devices_discovered"] = 0
            self.device_stats["unique_devices_discovered"] = set()
            self.device_stats["device_connection_counts"] = {}
    
    def clear_adapter_metrics(self) -> None:
        """Clear adapter metrics."""
        pass  # No adapter-specific metrics yet
    
    def reset_metrics(self) -> None:
        """Reset all metrics."""
        with self._lock:
            # Reset operation counts
            for key in self.operation_counts:
                self.operation_counts[key] = 0
            
            # Reset error counts
            for key in self.error_counts:
                self.error_counts[key] = 0
            
            # Reset timing histories
            for key in self.operation_timings:
                self.operation_timings[key].clear()
            
            # Reset connection stats
            self.connection_stats = {
                "total_connections": 0,
                "successful_connections": 0,
                "failed_connections": 0,
                "avg_connect_time": 0.0,
                "max_connect_time": 0.0,
                "current_connections": 0
            }
            
            # Reset device stats
            self.device_stats = {
                "total_devices_discovered": 0,
                "unique_devices_discovered": set(),
                "most_connected_device": None,
                "device_connection_counts": {}
            }
            
            # Reset start time
            self.start_time = time.time()
    
    def _calculate_timing_summary(self) -> Dict[str, Dict[str, float]]:
        """Calculate timing summary statistics."""
        result = {}
        
        for op, timings in self.operation_timings.items():
            if not timings:
                result[op] = {
                    "min": 0.0,
                    "max": 0.0,
                    "avg": 0.0,
                    "count": 0
                }
                continue
            
            # Extract successful timings
            successful_timings = [t["duration"] for t in timings if t["success"]]
            
            if successful_timings:
                result[op] = {
                    "min": min(successful_timings),
                    "max": max(successful_timings),
                    "avg": sum(successful_timings) / len(successful_timings),
                    "count": len(successful_timings)
                }
            else:
                result[op] = {
                    "min": 0.0,
                    "max": 0.0,
                    "avg": 0.0,
                    "count": 0
                }
        
        return result
    
    def _get_operation_metrics_list(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get a list of operation metrics records."""
        metrics = []
        for op_type, timings in self.operation_timings.items():
            for timing in list(timings)[-limit:]:
                metrics.append({
                    "operation": op_type,
                    "timestamp": timing["timestamp"],
                    "duration": timing["duration"],
                    "success": timing["success"]
                })
        
        # Sort by timestamp (newest first) and limit
        metrics.sort(key=lambda x: x["timestamp"], reverse=True)
        return metrics[:limit]
    
    def _get_device_metrics_list(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get a list of device metrics records."""
        metrics = []
        for device_addr in self.device_stats["unique_devices_discovered"]:
            metrics.append({
                "address": device_addr,
                "connections": self.device_stats["device_connection_counts"].get(device_addr, 0),
                "last_seen": time.time()  # This is a placeholder, would need actual tracking
            })
        
        return metrics[:limit]
    
    def _get_system_metrics_list(self) -> List[Dict[str, Any]]:
        """Get system-level metrics."""
        return [{
            "metric": "uptime",
            "value": time.time() - self.start_time,
            "unit": "seconds"
        }, {
            "metric": "total_operations",
            "value": sum(self.operation_counts.values()),
            "unit": "count"
        }, {
            "metric": "total_errors",
            "value": sum(self.error_counts.values()),
            "unit": "count"
        }]

# Singleton instance
_metrics_collector = None

def get_metrics_collector() -> BleMetricsCollector:
    """
    Get the singleton metrics collector instance.
    
    Returns:
        BleMetricsCollector instance
    """
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = BleMetricsCollector()
    return _metrics_collector

def get_ble_metrics() -> BleMetricsCollector:
    """
    Alias for get_metrics_collector for backward compatibility.
    
    Returns:
        BleMetricsCollector instance
    """
    return get_metrics_collector()