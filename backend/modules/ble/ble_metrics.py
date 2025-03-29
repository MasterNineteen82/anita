import time
import logging
import uuid
from typing import Dict, Any, List, Optional
from collections import deque
import psutil
import platform
from datetime import datetime
import cpuinfo  # Make sure py-cpuinfo is imported

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
    
    # Add new method to track adapter-specific metrics
    def record_adapter_metrics(self, adapter_id: str, operation: str, success: bool, details: Dict[str, Any] = None):
        """
        Record metrics for a specific adapter.
        
        Args:
            adapter_id: Identifier for the adapter
            operation: Operation performed (scan, connect, etc.)
            success: Whether the operation was successful
            details: Additional operation details
        """
        if not hasattr(self, "adapter_metrics"):
            self.adapter_metrics = {}
        
        if adapter_id not in self.adapter_metrics:
            self.adapter_metrics[adapter_id] = {
                "operations": {},
                "success_count": 0,
                "failure_count": 0,
                "last_operation_time": None,
                "last_operation": None,
                "history": deque(maxlen=self.max_history)
            }
        
        # Update counters
        if success:
            self.adapter_metrics[adapter_id]["success_count"] += 1
        else:
            self.adapter_metrics[adapter_id]["failure_count"] += 1
        
        # Update operation counts
        if operation not in self.adapter_metrics[adapter_id]["operations"]:
            self.adapter_metrics[adapter_id]["operations"][operation] = {
                "count": 0,
                "success_count": 0,
                "failure_count": 0
            }
        
        self.adapter_metrics[adapter_id]["operations"][operation]["count"] += 1
        if success:
            self.adapter_metrics[adapter_id]["operations"][operation]["success_count"] += 1
        else:
            self.adapter_metrics[adapter_id]["operations"][operation]["failure_count"] += 1
        
        # Update timestamps
        self.adapter_metrics[adapter_id]["last_operation_time"] = time.time()
        self.adapter_metrics[adapter_id]["last_operation"] = operation
        
        # Add to history
        history_entry = {
            "timestamp": time.time(),
            "operation": operation,
            "success": success,
            "details": details or {}
        }
        self.adapter_metrics[adapter_id]["history"].append(history_entry)
    
    def get_adapter_metrics(self, adapter_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get metrics for a specific adapter or all adapters.
        
        Args:
            adapter_id: Optional identifier for a specific adapter
            
        Returns:
            Dict: Adapter metrics
        """
        if not hasattr(self, "adapter_metrics"):
            return {"adapters": {}, "count": 0}
        
        if adapter_id and adapter_id in self.adapter_metrics:
            return {
                "adapter": adapter_id,
                "metrics": self.adapter_metrics[adapter_id]
            }
        
        return {
            "adapters": self.adapter_metrics,
            "count": len(self.adapter_metrics)
        }

    def record_scan_start(self):
        """Record the start of a scan operation.
        
        Returns:
            str: Operation ID for tracking
        """
        import uuid
        import time
        
        op_id = str(uuid.uuid4())
        
        # Initialize operations dict if not exists
        if not hasattr(self, "operations"):
            self.operations = {}
            
        # Initialize scan_count if not exists
        if not hasattr(self, "scan_count"):
            self.scan_count = 0
            
        # Record operation
        self.operations[op_id] = {
            "type": "scan",
            "start_time": time.time(),
            "status": "in_progress"
        }
        
        self.scan_count += 1
        return op_id
        
    def record_scan_complete(self, op_id, success=True, device_count=0, error=None):
        """Record the completion of a scan operation.
        
        Args:
            op_id: Operation ID from record_scan_start
            success: Whether the scan succeeded
            device_count: Number of devices found
            error: Error message if scan failed
        """
        import time
        
        # Initialize operations dict if not exists
        if not hasattr(self, "operations"):
            self.operations = {}
            
        # Initialize scan_failures and devices_found if not exists
        if not hasattr(self, "scan_failures"):
            self.scan_failures = 0
            
        if not hasattr(self, "devices_found"):
            self.devices_found = 0
        
        # Skip if operation not found
        if op_id not in self.operations:
            return
            
        # Skip if operation is not a scan
        operation = self.operations[op_id]
        if operation.get("type") != "scan":
            return
            
        # Record completion
        operation["end_time"] = time.time()
        operation["duration"] = operation["end_time"] - operation["start_time"]
        operation["success"] = success
        operation["device_count"] = device_count
        
        if success:
            self.devices_found += device_count
        else:
            self.scan_failures += 1
            operation["error"] = error

class SystemMonitor:
    """Monitor system resources and provide diagnostics for BLE operations"""
    
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        self.baseline = self.capture_baseline()
    
    def capture_baseline(self) -> Dict[str, Any]:
        """Capture baseline system metrics for comparison"""
        return {
            "timestamp": datetime.now().isoformat(),
            "cpu": {
                "percent": psutil.cpu_percent(interval=0.1),
                "count": psutil.cpu_count()
            },
            "memory": {
                "total": psutil.virtual_memory().total,
                "available": psutil.virtual_memory().available,
                "percent": psutil.virtual_memory().percent
            },
            "cpu_info": cpuinfo.get_cpu_info()
        }
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get static system information"""
        try:
            cpu_info = cpuinfo.get_cpu_info()
        except Exception:
            cpu_info = {"brand_raw": "Unknown", "hz_advertised_friendly": "Unknown"}
        
        return {
            "platform": platform.system(),
            "platform_version": platform.version(),
            "platform_release": platform.release(),
            "processor": cpu_info.get("brand_raw", "Unknown"),
            "processor_freq": cpu_info.get("hz_advertised_friendly", "Unknown"),
            "python_version": platform.python_version(),
            "memory": {
                "total": psutil.virtual_memory().total
            }
        }
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get current system metrics"""
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "cpu": {
                "percent": psutil.cpu_percent(interval=0.1),
                "count": psutil.cpu_count(),
                "frequency": None
            },
            "memory": {
                "total": psutil.virtual_memory().total,
                "available": psutil.virtual_memory().available,
                "percent": psutil.virtual_memory().percent
            },
            "network": {},
            "process": {
                "cpu_percent": psutil.Process().cpu_percent(interval=0.1),
                "memory_percent": psutil.Process().memory_percent(),
                "memory_rss": psutil.Process().memory_info().rss,
                "threads": len(psutil.Process().threads())
            },
            "battery": None
        }
        
        # Try to get CPU frequency
        try:
            cpu_freq = psutil.cpu_freq()
            if cpu_freq:
                metrics["cpu"]["frequency"] = {
                    "current": cpu_freq.current,
                    "min": cpu_freq.min,
                    "max": cpu_freq.max
                }
        except Exception:
            pass
        
        # Try to get battery info
        try:
            battery = psutil.sensors_battery()
            if battery:
                metrics["battery"] = {
                    "percent": battery.percent,
                    "power_plugged": battery.power_plugged,
                    "secsleft": battery.secsleft
                }
        except Exception:
            pass
        
        # Try to get network I/O stats
        try:
            net_io = psutil.net_io_counters()
            metrics["network"] = {
                "bytes_sent": net_io.bytes_sent,
                "bytes_recv": net_io.bytes_recv,
                "packets_sent": net_io.packets_sent,
                "packets_recv": net_io.packets_recv,
                "errin": net_io.errin,
                "errout": net_io.errout,
                "dropin": net_io.dropin,
                "dropout": net_io.dropout
            }
        except Exception:
            pass
        
        return metrics
    
    def get_bluetooth_health_report(self) -> Dict[str, Any]:
        """
        Generate a comprehensive health report for Bluetooth functionality.
        
        Returns:
            Dict: Health report with diagnostic information
        """
        system_info = self.get_system_info()
        current_metrics = self.get_system_metrics()
        
        # Check for common issues that could affect Bluetooth
        issues = []
        recommendations = []
        status = "healthy"
        
        # Check CPU load
        if current_metrics["cpu"]["percent"] > 80:
            issues.append("High CPU usage may affect Bluetooth performance")
            recommendations.append("Close unnecessary applications to reduce CPU load")
            status = "warning"
        
        # Check memory
        if current_metrics["memory"]["percent"] > 90:
            issues.append("Low system memory could cause Bluetooth stability issues")
            recommendations.append("Free up memory by closing applications or restarting the system")
            status = "warning"
        
        # Check Bluetooth services (Windows)
        if platform.system() == "Windows":
            bt_service_running = False
            
            try:
                import wmi
                w = wmi.WMI()
                
                for service in w.Win32_Service(Name="bthserv"):
                    if service.State == "Running":
                        bt_service_running = True
                    else:
                        issues.append("Bluetooth Support Service is not running")
                        recommendations.append("Start the Bluetooth Support Service (bthserv)")
                        status = "error"
            except Exception:
                # Fallback using psutil
                for service in psutil.win_service_iter():
                    if service.name().lower() == "bthserv":
                        info = service.as_dict()
                        if info["status"] == "running":
                            bt_service_running = True
                        else:
                            issues.append("Bluetooth Support Service is not running")
                            recommendations.append("Start the Bluetooth Support Service (bthserv)")
                            status = "error"
            
            # Check for device manager errors
            try:
                for device in w.Win32_PnPEntity():
                    if (hasattr(device, 'PNPDeviceID') and device.PNPDeviceID and 
                        "bluetooth" in device.PNPDeviceID.lower() and
                        device.ConfigManagerErrorCode != 0):
                        issues.append(f"Bluetooth adapter has an error: {device.Caption}")
                        recommendations.append("Check Device Manager for issues with the Bluetooth adapter")
                        status = "error"
            except Exception:
                pass
        
        # For Linux
        elif platform.system() == "Linux":
            try:
                import subprocess
                result = subprocess.run(["systemctl", "is-active", "bluetooth"], 
                                       capture_output=True, text=True)
                if result.stdout.strip() != "active":
                    issues.append("Bluetooth service is not running")
                    recommendations.append("Start the Bluetooth service with: sudo systemctl start bluetooth")
                    status = "error"
            except Exception:
                pass
        
        # Assemble the health report
        report = {
            "timestamp": datetime.now().isoformat(),
            "status": status,
            "issues": issues,
            "recommendations": recommendations,
            "system": {
                "platform": system_info.get("platform", "Unknown"),
                "processor": system_info.get("processor", "Unknown"),
                "memory_total_gb": round(system_info.get("memory", {}).get("total", 0) / (1024**3), 1),
                "memory_available_gb": round(current_metrics.get("memory", {}).get("available", 0) / (1024**3), 1),
                "memory_percent": current_metrics.get("memory", {}).get("percent", 0),
                "cpu_percent": current_metrics.get("cpu", {}).get("percent", 0)
            },
            "bluetooth": {
                "services_running": True,  # Default to true, updated above if needed
            }
        }
        
        # On Windows, add registry and driver details
        if platform.system() == "Windows":
            try:
                import winreg
                registry_info = {}
                
                # Check common Bluetooth registry keys
                registry_paths = [
                    r"SYSTEM\CurrentControlSet\Services\BTHPORT\Parameters",
                    r"SYSTEM\CurrentControlSet\Services\Bluetooth\Parameters"
                ]
                
                for path in registry_paths:
                    try:
                        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path) as key:
                            registry_info[path] = "Accessible"
                    except WindowsError:
                        registry_info[path] = "Not accessible or doesn't exist"
                
                report["windows_specific"] = {
                    "registry": registry_info
                }
            except Exception:
                pass
        
        return report