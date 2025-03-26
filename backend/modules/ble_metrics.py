import time
import logging
import uuid
from typing import Dict, Any, List, Optional
from collections import deque

class BleMetricsCollector:
    """
    Collector for BLE operation metrics and statistics.
    Provides insights into connection reliability, performance, and errors.
    """
    
    def __init__(self, logger=None, max_history: int = 100):
        self.logger = logger or logging.getLogger(__name__)
        self.max_history = max_history
        
        # Connection metrics
        self.connection_attempts = 0
        self.connection_successes = 0
        self.connection_failures = 0
        self.connection_timeouts = 0
        
        # Read/write metrics
        self.read_operations = 0
        self.write_operations = 0
        self.notification_count = 0
        
        # Detailed operation tracking
        self.operations = {}  # Operation ID → details
        self.operation_history = deque(maxlen=max_history)
        
        # Device specific metrics
        self.device_metrics = {}  # Device address → metrics
        
        # Error tracking
        self.error_counts = {}  # Error type → count
        
        # Performance metrics
        self.scan_times = []  # List of scan durations
        self.connection_times = []  # List of connection times
    
    def record_connect_start(self, address: str) -> str:
        """
        Record the start of a connection attempt.
        
        Args:
            address: Device address
            
        Returns:
            str: Operation ID for tracking
        """
        op_id = str(uuid.uuid4())
        
        # Update counters
        self.connection_attempts += 1
        
        # Initialize device metrics if needed
        if address not in self.device_metrics:
            self.device_metrics[address] = {
                "connection_attempts": 0,
                "connection_successes": 0,
                "connection_failures": 0,
                "avg_rssi": None,
                "last_connect_time": None,
                "is_bonded": False,
                "bonded_connections": 0,
                "error_history": []
            }
        
        # Update device metrics
        self.device_metrics[address]["connection_attempts"] += 1
        
        # Record operation details
        op_details = {
            "id": op_id,
            "type": "connect",
            "address": address,
            "start_time": time.time(),
            "end_time": None,
            "duration": None,
            "success": None,
            "error": None
        }
        
        self.operations[op_id] = op_details
        
        return op_id
    
    def record_connect_complete(self, op_id: str, address: str, success: bool, duration: Optional[float] = None):
        """
        Record the completion of a connection attempt.
        
        Args:
            op_id: Operation ID from record_connect_start
            address: Device address
            success: Whether connection was successful
            duration: Connection duration in seconds (if not provided, calculated from start time)
        """
        if op_id not in self.operations:
            self.logger.warning(f"Operation {op_id} not found in metrics")
            return
        
        op = self.operations[op_id]
        op["end_time"] = time.time()
        
        if duration is not None:
            op["duration"] = duration
        else:
            op["duration"] = op["end_time"] - op["start_time"]
        
        op["success"] = success
        
        # Update counters
        if success:
            self.connection_successes += 1
            self.device_metrics[address]["connection_successes"] += 1
            self.device_metrics[address]["last_connect_time"] = time.time()
        else:
            self.connection_failures += 1
            self.device_metrics[address]["connection_failures"] += 1
        
        # Add to history
        self.operation_history.append(op.copy())
        
        # Track connection time for performance metrics
        self.connection_times.append(op["duration"])
        
        # Clean up completed operations periodically
        if len(self.operations) > self.max_history * 2:
            self._clean_old_operations()
    
    def record_connect_error(self, address: str, error_type: str):
        """
        Record a connection error.
        
        Args:
            address: Device address
            error_type: Type of error
        """
        # Update error counts
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
        
        # Add to device error history
        if address in self.device_metrics:
            self.device_metrics[address]["error_history"].append({
                "timestamp": time.time(),
                "error_type": error_type
            })
            
            # Limit error history size
            if len(self.device_metrics[address]["error_history"]) > 10:
                self.device_metrics[address]["error_history"] = self.device_metrics[address]["error_history"][-10:]
    
    def record_bonded_connection(self, address: str):
        """Record a successful connection to a bonded device."""
        if address in self.device_metrics:
            self.device_metrics[address]["is_bonded"] = True
            self.device_metrics[address]["bonded_connections"] += 1
    
    def record_scan(self, duration: float, device_count: int):
        """Record metrics for a scan operation."""
        self.scan_times.append(duration)
        
        # Limit size of scan times list
        if len(self.scan_times) > 100:
            self.scan_times = self.scan_times[-100:]
    
    def record_read(self, characteristic: str, success: bool, duration: float):
        """Record metrics for a characteristic read operation."""
        self.read_operations += 1
    
    def record_write(self, characteristic: str, success: bool, duration: float):
        """Record metrics for a characteristic write operation."""
        self.write_operations += 1
    
    def record_notification(self, characteristic: str):
        """Record metrics for a characteristic notification."""
        self.notification_count += 1
    
    def _clean_old_operations(self):
        """Clean up old operations to prevent memory growth."""
        # Keep only operations with current operation IDs
        current_ops = {op["id"] for op in self.operation_history}
        self.operations = {op_id: op for op_id, op in self.operations.items() if op_id in current_ops}
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get a summary of BLE metrics."""
        connection_success_rate = 0
        if self.connection_attempts > 0:
            connection_success_rate = (self.connection_successes / self.connection_attempts) * 100
        
        avg_connection_time = 0
        if self.connection_times:
            avg_connection_time = sum(self.connection_times) / len(self.connection_times)
        
        return {
            "connection_attempts": self.connection_attempts,
            "connection_successes": self.connection_successes,
            "connection_failures": self.connection_failures,
            "connection_success_rate": connection_success_rate,
            "avg_connection_time": avg_connection_time,
            "read_operations": self.read_operations,
            "write_operations": self.write_operations,
            "notification_count": self.notification_count,
            "device_count": len(self.device_metrics),
            "top_errors": self._get_top_errors(5),
            "timestamp": time.time()
        }
    
    def get_detailed_metrics(self) -> Dict[str, Any]:
        """Get detailed BLE metrics for advanced analysis."""
        return {
            "summary": self.get_metrics_summary(),
            "device_metrics": self.device_metrics,
            "error_counts": self.error_counts,
            "recent_operations": list(self.operation_history),
            "performance": {
                "scan_times": self.scan_times,
                "connection_times": self.connection_times,
            }
        }
    
    def _get_top_errors(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get the most common errors."""
        sorted_errors = sorted(
            self.error_counts.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        return [
            {"type": error_type, "count": count}
            for error_type, count in sorted_errors[:limit]
        ]