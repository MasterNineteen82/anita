"""
BLE System Monitor.

This module provides system monitoring capabilities for BLE operations:
- System resource monitoring (CPU, memory, etc.)
- BLE subsystem health monitoring
- Diagnostic information gathering
- Health recommendations
"""

import logging
import time
import platform
import os
import asyncio
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import psutil

try:
    import cpuinfo
    CPU_INFO_AVAILABLE = True
except ImportError:
    CPU_INFO_AVAILABLE = False

# Import the event bus for notifications
from .events import ble_event_bus

logger = logging.getLogger(__name__)

class SystemMonitor:
    """
    Monitors system resources and BLE subsystem health.
    
    This class provides methods to:
    - Track system resource usage
    - Monitor BLE subsystem health
    - Generate diagnostic reports
    - Provide recommendations for improved BLE performance
    """
    
    def __init__(self, log_interval: int = 300):
        """
        Initialize the system monitor.
        
        Args:
            log_interval: How often (in seconds) to log system metrics
        """
        self.log_interval = log_interval
        self.last_log_time = 0
        self.system_info_cache = {}
        self.bluetooth_info_cache = {}
        self.issues_detected = []
        self.is_monitoring = False
        self._monitoring_task = None
        
        # Initialize system info
        self._init_system_info()
        
    def _init_system_info(self):
        """Initialize system information cache."""
        try:
            self.system_info_cache = {
                "platform": platform.system(),
                "platform_release": platform.release(),
                "platform_version": platform.version(),
                "architecture": platform.machine(),
                "processor": platform.processor(),
                "python_version": platform.python_version(),
            }
            
            # Add CPU info if available
            if CPU_INFO_AVAILABLE:
                cpu_info = cpuinfo.get_cpu_info()
                self.system_info_cache["cpu_brand"] = cpu_info.get("brand_raw", "Unknown")
                self.system_info_cache["cpu_cores"] = psutil.cpu_count(logical=False)
                self.system_info_cache["cpu_threads"] = psutil.cpu_count(logical=True)
                
            # Memory info
            memory = psutil.virtual_memory()
            self.system_info_cache["total_memory_gb"] = round(memory.total / (1024**3), 2)
            
            # OS-specific info
            if self.system_info_cache["platform"] == "Windows":
                self._init_windows_bluetooth_info()
            elif self.system_info_cache["platform"] == "Linux":
                self._init_linux_bluetooth_info()
            elif self.system_info_cache["platform"] == "Darwin":
                self._init_macos_bluetooth_info()
                
        except Exception as e:
            logger.error(f"Error initializing system info: {e}", exc_info=True)
            
    def _init_windows_bluetooth_info(self):
        """Initialize Windows-specific Bluetooth information."""
        try:
            import winreg
            
            # Check Bluetooth service status
            import subprocess
            result = subprocess.run(["sc", "query", "bthserv"], capture_output=True, text=True, check=False)
            
            self.bluetooth_info_cache["service_running"] = "RUNNING" in result.stdout
            
            # Try to get adapter info from registry
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Services\BTHPORT\Parameters\Devices") as key:
                    self.bluetooth_info_cache["paired_devices_count"] = winreg.QueryInfoKey(key)[0]
            except Exception:
                self.bluetooth_info_cache["paired_devices_count"] = "Unknown"
                
        except Exception as e:
            logger.error(f"Error getting Windows Bluetooth info: {e}")
            
    def _init_linux_bluetooth_info(self):
        """Initialize Linux-specific Bluetooth information."""
        try:
            # Check if bluetoothctl is available
            import shutil
            if shutil.which("bluetoothctl"):
                import subprocess
                # Check Bluetooth service status
                service_result = subprocess.run(["systemctl", "is-active", "bluetooth"], 
                                               capture_output=True, text=True, check=False)
                
                self.bluetooth_info_cache["service_running"] = service_result.stdout.strip() == "active"
                
                # Try to get adapter info
                adapter_result = subprocess.run(["bluetoothctl", "list"], 
                                              capture_output=True, text=True, check=False)
                
                self.bluetooth_info_cache["adapters_found"] = len(adapter_result.stdout.strip().split("\n")) if adapter_result.stdout else 0
                
        except Exception as e:
            logger.error(f"Error getting Linux Bluetooth info: {e}")
            
    def _init_macos_bluetooth_info(self):
        """Initialize macOS-specific Bluetooth information."""
        try:
            import subprocess
            
            # Check Bluetooth service status using launchctl
            result = subprocess.run(["launchctl", "list", "com.apple.bluetoothd"], 
                                  capture_output=True, text=True, check=False)
            
            self.bluetooth_info_cache["service_running"] = result.returncode == 0
            
            # Try to get Bluetooth version from system_profiler
            try:
                profile_result = subprocess.run(["system_profiler", "SPBluetoothDataType"], 
                                             capture_output=True, text=True, check=False)
                
                if "Bluetooth Version:" in profile_result.stdout:
                    import re
                    match = re.search(r"Bluetooth Version: (\d+\.\d+)", profile_result.stdout)
                    if match:
                        self.bluetooth_info_cache["bluetooth_version"] = match.group(1)
            except Exception:
                pass
                
        except Exception as e:
            logger.error(f"Error getting macOS Bluetooth info: {e}")
    
    async def get_system_metrics(self) -> Dict[str, Any]:
        """
        Get current system resource metrics.
        
        Returns:
            Dict with system metrics (CPU, memory, etc.)
        """
        try:
            # Maybe log metrics periodically
            current_time = time.time()
            should_log = (current_time - self.last_log_time) > self.log_interval
            
            # Get CPU and memory usage
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # Get disk usage for the current directory
            disk = psutil.disk_usage(os.getcwd())
            disk_percent = disk.percent
            
            # Get network stats
            net_io = psutil.net_io_counters()
            network_sent = net_io.bytes_sent
            network_recv = net_io.bytes_recv
            
            # Create metrics object
            metrics = {
                "timestamp": current_time,
                "cpu_percent": cpu_percent,
                "memory_percent": memory_percent,
                "disk_percent": disk_percent,
                "network_sent": network_sent,
                "network_recv": network_recv
            }
            
            # Log if interval has passed
            if should_log:
                logger.info(f"System metrics - CPU: {cpu_percent}%, Memory: {memory_percent}%, Disk: {disk_percent}%")
                self.last_log_time = current_time
                
                # Emit an event with the metrics
                await ble_event_bus.emit("system_metrics", metrics)
                
                # Check for resource issues
                self._check_resource_issues(metrics)
                
            return metrics
            
        except Exception as e:
            logger.error(f"Error getting system metrics: {e}", exc_info=True)
            return {
                "timestamp": time.time(),
                "error": str(e)
            }
    
    def _check_resource_issues(self, metrics: Dict[str, Any]):
        """Check for resource-related issues and record them."""
        # Check CPU usage
        if metrics["cpu_percent"] > 80:
            issue = "High CPU usage detected (>80%). This may impact BLE performance."
            if issue not in self.issues_detected:
                self.issues_detected.append(issue)
                logger.warning(issue)
                
        # Check memory usage
        if metrics["memory_percent"] > 90:
            issue = "High memory usage detected (>90%). This may cause stability issues."
            if issue not in self.issues_detected:
                self.issues_detected.append(issue)
                logger.warning(issue)
                
        # Check disk usage
        if metrics["disk_percent"] > 95:
            issue = "Very low disk space (<5% free). This may affect logging and data storage."
            if issue not in self.issues_detected:
                self.issues_detected.append(issue)
                logger.warning(issue)
    
    async def get_bluetooth_health_report(self) -> Dict[str, Any]:
        """
        Generate a comprehensive health report for the Bluetooth subsystem.
        
        Includes:
        - System resources
        - Adapter status
        - Recent operations
        - Identified issues
        - Recommendations
        
        Returns:
            Dict with health report information
        """
        try:
            # Get system metrics
            system_metrics = await self.get_system_metrics()
            
            # Get adapter status (platform-specific)
            adapter_status = await self._get_adapter_status()
            
            # Gather issues and recommendations
            errors = list(self.issues_detected)
            warnings = []
            recommendations = []
            
            # Check for resource issues
            if system_metrics["cpu_percent"] > 70:
                warnings.append("CPU usage is high")
                recommendations.append("Consider closing other CPU-intensive applications")
                
            if system_metrics["memory_percent"] > 80:
                warnings.append("Memory usage is high")
                recommendations.append("Consider closing memory-intensive applications")
            
            # Check for Bluetooth-specific issues
            if not adapter_status.get("available", False):
                errors.append("No Bluetooth adapter available")
                recommendations.append("Check if Bluetooth is turned on and adapter is working")
                
            elif adapter_status.get("low_power_mode", False):
                warnings.append("Bluetooth adapter may be in low power mode")
                recommendations.append("Check power management settings for your Bluetooth adapter")
            
            # Create the health report
            report = {
                "timestamp": time.time(),
                "system_resources": {
                    "cpu_percent": system_metrics["cpu_percent"],
                    "memory_percent": system_metrics["memory_percent"],
                    "disk_percent": system_metrics["disk_percent"],
                },
                "adapter_status": adapter_status,
                "ble_operations": {},  # Filled by BLE service
                "errors": errors,
                "warnings": warnings,
                "recommendations": recommendations
            }
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating health report: {e}", exc_info=True)
            return {
                "timestamp": time.time(),
                "error": str(e),
                "system_resources": {},
                "adapter_status": {},
                "errors": ["Failed to generate health report: " + str(e)],
                "warnings": [],
                "recommendations": ["Check system logs for more information"]
            }
    
    async def _get_adapter_status(self) -> Dict[str, Any]:
        """Get status of BLE adapter (platform-specific implementation)."""
        platform_name = self.system_info_cache.get("platform", "Unknown")
        
        if platform_name == "Windows":
            return await self._get_windows_adapter_status()
        elif platform_name == "Linux":
            return await self._get_linux_adapter_status()
        elif platform_name == "Darwin":  # macOS
            return await self._get_macos_adapter_status()
        else:
            return {"available": False, "error": "Unsupported platform"}
    
    async def _get_windows_adapter_status(self) -> Dict[str, Any]:
        """Get Windows adapter status."""
        try:
            import subprocess
            
            # Check if Bluetooth service is running
            service_check = subprocess.run(
                ["sc", "query", "bthserv"], 
                capture_output=True, 
                text=True,
                check=False
            )
            
            is_service_running = "RUNNING" in service_check.stdout
            
            if not is_service_running:
                return {
                    "available": False,
                    "service_running": False,
                    "error": "Bluetooth service is not running"
                }
            
            # Use PowerShell to get adapter info
            ps_command = "Get-PnpDevice -Class Bluetooth | ConvertTo-Json"
            ps_process = subprocess.run(
                ["powershell", "-Command", ps_command],
                capture_output=True,
                text=True,
                check=False
            )
            
            if ps_process.returncode != 0:
                return {
                    "available": False,
                    "service_running": True,
                    "error": "Failed to query adapter info"
                }
            
            import json
            try:
                # Output might be a single object or array
                ps_output = ps_process.stdout.strip()
                if not ps_output:
                    return {
                        "available": False,
                        "service_running": True,
                        "error": "No adapter information returned"
                    }
                
                # Try to parse as array first, then as single object
                try:
                    adapter_info = json.loads(ps_output)
                except json.JSONDecodeError:
                    # Clean up output for easier parsing
                    ps_output = ps_output.replace('\r\n', '')
                    adapter_info = json.loads(ps_output)
                
                # Convert to list if single object
                if not isinstance(adapter_info, list):
                    adapter_info = [adapter_info]
                
                # Check for enabled adapters
                enabled_adapters = [
                    adapter for adapter in adapter_info 
                    if adapter.get("Status") == "OK"
                ]
                
                if not enabled_adapters:
                    return {
                        "available": False,
                        "service_running": True,
                        "adapters_found": len(adapter_info),
                        "adapters_enabled": 0,
                        "error": "No enabled Bluetooth adapters found"
                    }
                
                # Return info about available adapters
                return {
                    "available": True,
                    "service_running": True,
                    "adapters_found": len(adapter_info),
                    "adapters_enabled": len(enabled_adapters),
                    "adapter_info": [
                        {
                            "name": adapter.get("FriendlyName", "Unknown"),
                            "status": adapter.get("Status", "Unknown"),
                            "problem_code": adapter.get("ProblemCode", 0)
                        }
                        for adapter in adapter_info
                    ]
                }
                
            except json.JSONDecodeError as e:
                return {
                    "available": False,
                    "service_running": True,
                    "error": f"Failed to parse adapter info: {str(e)}",
                    "raw_output": ps_process.stdout[:100] + "..." if len(ps_process.stdout) > 100 else ps_process.stdout
                }
                
        except Exception as e:
            logger.error(f"Error getting Windows adapter status: {e}", exc_info=True)
            return {
                "available": False,
                "error": str(e)
            }
    
    async def _get_linux_adapter_status(self) -> Dict[str, Any]:
        """Get Linux adapter status."""
        try:
            import subprocess
            import shutil
            
            if not shutil.which("bluetoothctl"):
                return {
                    "available": False,
                    "error": "bluetoothctl not found"
                }
            
            # Check if Bluetooth service is running
            service_check = subprocess.run(
                ["systemctl", "is-active", "bluetooth"],
                capture_output=True,
                text=True,
                check=False
            )
            
            is_service_running = service_check.stdout.strip() == "active"
            
            if not is_service_running:
                return {
                    "available": False,
                    "service_running": False,
                    "error": "Bluetooth service is not running"
                }
            
            # Get list of adapters
            adapter_list = subprocess.run(
                ["bluetoothctl", "list"],
                capture_output=True,
                text=True,
                check=False
            )
            
            if adapter_list.returncode != 0 or not adapter_list.stdout.strip():
                return {
                    "available": False,
                    "service_running": True,
                    "error": "No Bluetooth adapters found"
                }
            
            # Parse adapter list
            adapters = []
            adapter_lines = adapter_list.stdout.strip().split('\n')
            
            for line in adapter_lines:
                if line.strip():
                    # Format is usually: Controller XX:XX:XX:XX:XX:XX DeviceName [default]
                    parts = line.strip().split(' ', 2)
                    if len(parts) >= 2:
                        adapter_addr = parts[1]
                        adapter_name = parts[2] if len(parts) > 2 else "Unknown"
                        
                        # Get adapter info
                        info_result = subprocess.run(
                            ["bluetoothctl", "show", adapter_addr],
                            capture_output=True,
                            text=True,
                            check=False
                        )
                        
                        # Parse info output
                        adapter_info = {
                            "address": adapter_addr,
                            "name": adapter_name,
                            "powered": "Powered: yes" in info_result.stdout,
                            "discoverable": "Discoverable: yes" in info_result.stdout,
                            "pairable": "Pairable: yes" in info_result.stdout
                        }
                        adapters.append(adapter_info)
            
            # Count powered adapters
            powered_adapters = [a for a in adapters if a.get("powered", False)]
            
            return {
                "available": len(powered_adapters) > 0,
                "service_running": True,
                "adapters_found": len(adapters),
                "adapters_powered": len(powered_adapters),
                "adapter_info": adapters
            }
            
        except Exception as e:
            logger.error(f"Error getting Linux adapter status: {e}", exc_info=True)
            return {
                "available": False,
                "error": str(e)
            }
    
    async def _get_macos_adapter_status(self) -> Dict[str, Any]:
        """Get macOS adapter status."""
        try:
            import subprocess
            
            # Check if Bluetooth service is running
            service_check = subprocess.run(
                ["launchctl", "list", "com.apple.bluetoothd"],
                capture_output=True,
                text=True,
                check=False
            )
            
            is_service_running = service_check.returncode == 0
            
            if not is_service_running:
                return {
                    "available": False,
                    "service_running": False,
                    "error": "Bluetooth service is not running"
                }
            
            # Use system_profiler to get adapter info
            profile_result = subprocess.run(
                ["system_profiler", "SPBluetoothDataType"],
                capture_output=True,
                text=True,
                check=False
            )
            
            if "Bluetooth Power: On" in profile_result.stdout:
                # Parse basic adapter info
                import re
                
                # Try to get hardware address
                address_match = re.search(r"Address: ([0-9A-F:]+)", profile_result.stdout)
                address = address_match.group(1) if address_match else "Unknown"
                
                # Try to get manufacturer
                manufacturer_match = re.search(r"Manufacturer: (.+?)$", profile_result.stdout, re.MULTILINE)
                manufacturer = manufacturer_match.group(1) if manufacturer_match else "Apple"
                
                # Try to get Bluetooth version
                version_match = re.search(r"Bluetooth Version: ([\d\.]+)", profile_result.stdout)
                version = version_match.group(1) if version_match else "Unknown"
                
                return {
                    "available": True,
                    "service_running": True,
                    "powered": True,
                    "address": address,
                    "manufacturer": manufacturer,
                    "version": version
                }
            else:
                return {
                    "available": False,
                    "service_running": True,
                    "powered": False,
                    "error": "Bluetooth is turned off"
                }
            
        except Exception as e:
            logger.error(f"Error getting macOS adapter status: {e}", exc_info=True)
            return {
                "available": False,
                "error": str(e)
            }
    
    async def get_system_info(self) -> Dict[str, Any]:
        """
        Get detailed system information.
        
        Returns:
            Dict with system info
        """
        # Get current system metrics
        metrics = await self.get_system_metrics()
        
        # Combine with cached system info
        result = {
            "system": self.system_info_cache,
            "bluetooth": self.bluetooth_info_cache,
            "timestamp": time.time(),
            "cpu_percent": metrics["cpu_percent"],
            "memory_percent": metrics["memory_percent"],
            "disk_percent": metrics["disk_percent"],
            "network_sent": metrics["network_sent"],
            "network_recv": metrics["network_recv"]
        }
        
        return result
    
    async def start_monitoring(self, interval: int = 60):
        """
        Start continuous system monitoring.
        
        Args:
            interval: How often to collect metrics (in seconds)
        """
        if self.is_monitoring:
            return
            
        self.is_monitoring = True
        
        async def monitoring_loop():
            while self.is_monitoring:
                try:
                    await self.get_system_metrics()
                    # No need to store result as it's logged and events emitted
                except Exception as e:
                    logger.error(f"Error in monitoring loop: {e}")
                finally:
                    await asyncio.sleep(interval)
        
        # Start monitoring task
        self._monitoring_task = asyncio.create_task(monitoring_loop())
        logger.info(f"System monitoring started (interval: {interval}s)")
    
    def stop_monitoring(self):
        """Stop continuous system monitoring."""
        self.is_monitoring = False
        
        if self._monitoring_task:
            self._monitoring_task.cancel()
            self._monitoring_task = None
            
        logger.info("System monitoring stopped")
        
    async def run_diagnostics(self, deep_check: bool = False) -> Dict[str, Any]:
        """
        Run diagnostics to identify system and BLE issues.
        
        Args:
            deep_check: Whether to perform deep system checks
            
        Returns:
            Dict with diagnostic results
        """
        try:
            # Start with system info
            system_info = await self.get_system_info()
            
            # Get Bluetooth health
            health_report = await self.get_bluetooth_health_report()
            
            # Run platform-specific diagnostics
            platform_diags = await self._run_platform_diagnostics(deep_check)
            
            # Combine all information
            diagnostics = {
                "timestamp": time.time(),
                "system_info": system_info["system"],
                "bluetooth_info": system_info["bluetooth"],
                "system_resources": {
                    "cpu_percent": system_info["cpu_percent"],
                    "memory_percent": system_info["memory_percent"],
                    "disk_percent": system_info["disk_percent"],
                },
                "bluetooth_health": {
                    "adapter_status": health_report["adapter_status"],
                    "errors": health_report["errors"],
                    "warnings": health_report["warnings"],
                },
                "platform_diagnostics": platform_diags,
                "recommendations": health_report["recommendations"]
            }
            
            return diagnostics
            
        except Exception as e:
            logger.error(f"Error running diagnostics: {e}", exc_info=True)
            return {
                "timestamp": time.time(),
                "error": str(e),
                "recommendations": ["Check system logs for more information"]
            }
    
    async def _run_platform_diagnostics(self, deep_check: bool) -> Dict[str, Any]:
        """Run platform-specific diagnostics."""
        platform_name = self.system_info_cache.get("platform", "Unknown")
        
        if platform_name == "Windows":
            return await self._run_windows_diagnostics(deep_check)
        elif platform_name == "Linux":
            return await self._run_linux_diagnostics(deep_check)
        elif platform_name == "Darwin":
            return await self._run_macos_diagnostics(deep_check)
        else:
            return {"error": "Unsupported platform"}
    
    async def _run_windows_diagnostics(self, deep_check: bool) -> Dict[str, Any]:
        """Run Windows-specific diagnostics."""
        try:
            import subprocess
            results = {}
            
            # Check Windows services
            services_to_check = ["bthserv", "BthHFSrv"]
            services_status = {}
            
            for service in services_to_check:
                try:
                    service_check = subprocess.run(
                        ["sc", "query", service],
                        capture_output=True,
                        text=True,
                        check=False
                    )
                    services_status[service] = "RUNNING" in service_check.stdout
                except Exception as e:
                    services_status[service] = f"Error: {str(e)}"
            
            results["services"] = services_status
            
            # Check Windows Bluetooth troubleshooter if deep check
            if deep_check:
                try:
                    # This runs the Windows troubleshooting PowerShell command
                    # Note: This may open a UI prompt
                    ps_command = "Get-TroubleshootingPack -Path '$env:windir\\diagnostics\\system\\Bluetooth' | Invoke-TroubleshootingPack -AnswerFile $null"
                    ts_process = subprocess.run(
                        ["powershell", "-Command", ps_command],
                        capture_output=True,
                        text=True,
                        check=False,
                        timeout=60  # Prevent hanging
                    )
                    
                    results["troubleshooter"] = {
                        "ran": True,
                        "exit_code": ts_process.returncode,
                        "output": ts_process.stdout[:500] + "..." if len(ts_process.stdout) > 500 else ts_process.stdout
                    }
                except Exception as e:
                    results["troubleshooter"] = {
                        "ran": False,
                        "error": str(e)
                    }
            
            return results
            
        except Exception as e:
            logger.error(f"Error running Windows diagnostics: {e}", exc_info=True)
            return {"error": str(e)}
    
    async def _run_linux_diagnostics(self, deep_check: bool) -> Dict[str, Any]:
        """Run Linux-specific diagnostics."""
        try:
            import subprocess
            import shutil
            results = {}
            
            # Check if required tools are available
            bluetooth_tools = {}
            for tool in ["bluetoothctl", "hcitool", "hciconfig"]:
                bluetooth_tools[tool] = shutil.which(tool) is not None
            
            results["tools_available"] = bluetooth_tools
            
            # Check if BlueZ is installed and version
            if bluetooth_tools["bluetoothctl"]:
                try:
                    bluez_version = subprocess.run(
                        ["bluetoothctl", "--version"],
                        capture_output=True,
                        text=True,
                        check=False
                    )
                    
                    results["bluez_version"] = bluez_version.stdout.strip()
                except Exception:
                    results["bluez_version"] = "Error getting version"
            
            # Check status of Bluetooth service
            try:
                service_status = subprocess.run(
                    ["systemctl", "status", "bluetooth"],
                    capture_output=True,
                    text=True,
                    check=False
                )
                
                results["service_status"] = {
                    "active": "Active: active" in service_status.stdout,
                    "output": service_status.stdout[:500] + "..." if len(service_status.stdout) > 500 else service_status.stdout
                }
            except Exception:
                results["service_status"] = {"active": False, "error": "Failed to check service status"}
            
            # Check adapter details if hciconfig is available
            if bluetooth_tools["hciconfig"] and deep_check:
                try:
                    hci_output = subprocess.run(
                        ["hciconfig", "-a"],
                        capture_output=True,
                        text=True,
                        check=False
                    )
                    
                    results["adapter_details"] = hci_output.stdout
                except Exception:
                    results["adapter_details"] = "Error getting adapter details"
            
            # Check kernel modules if deep check
            if deep_check:
                try:
                    lsmod_output = subprocess.run(
                        ["lsmod | grep -i bluetooth"],
                        shell=True,
                        capture_output=True,
                        text=True,
                        check=False
                    )
                    
                    results["kernel_modules"] = lsmod_output.stdout
                except Exception:
                    results["kernel_modules"] = "Error checking kernel modules"
            
            return results
            
        except Exception as e:
            logger.error(f"Error running Linux diagnostics: {e}", exc_info=True)
            return {"error": str(e)}
    
    async def _run_macos_diagnostics(self, deep_check: bool) -> Dict[str, Any]:
        """Run macOS-specific diagnostics."""
        try:
            import subprocess
            results = {}
            
            # Check Bluetooth service with launchctl
            try:
                service_check = subprocess.run(
                    ["launchctl", "list", "com.apple.bluetoothd"],
                    capture_output=True,
                    text=True,
                    check=False
                )
                
                results["service_running"] = service_check.returncode == 0
            except Exception:
                results["service_running"] = False
            
            # Get detailed Bluetooth info
            try:
                profile_result = subprocess.run(
                    ["system_profiler", "SPBluetoothDataType"],
                    capture_output=True,
                    text=True,
                    check=False
                )
                
                results["bluetooth_profile"] = profile_result.stdout[:1000] + "..." if len(profile_result.stdout) > 1000 else profile_result.stdout
            except Exception:
                results["bluetooth_profile"] = "Error retrieving Bluetooth profile"
            
            # Deep checks
            if deep_check:
                # Check IORegistry for Bluetooth controllers
                try:
                    ioreg_result = subprocess.run(
                        ["ioreg", "-p", "IOService", "-l", "-w", "0", "-r", "-c", "IOBluetoothHCIController"],
                        capture_output=True,
                        text=True,
                        check=False
                    )
                    
                    results["ioreg_controllers"] = ioreg_result.stdout[:1000] + "..." if len(ioreg_result.stdout) > 1000 else ioreg_result.stdout
                except Exception:
                    results["ioreg_controllers"] = "Error retrieving controller information"
                
                # Check if Bluetooth processes are running
                try:
                    ps_result = subprocess.run(
                        ["ps", "-ax", "|", "grep", "-i", "blue"],
                        shell=True,
                        capture_output=True,
                        text=True,
                        check=False
                    )
                    
                    results["bluetooth_processes"] = ps_result.stdout
                except Exception:
                    results["bluetooth_processes"] = "Error checking Bluetooth processes"
            
            return results
            
        except Exception as e:
            logger.error(f"Error running macOS diagnostics: {e}", exc_info=True)
            return {"error": str(e)}

# Create a singleton instance (can be overridden by unit tests)
_system_monitor = None

def get_system_monitor() -> SystemMonitor:
    """Get the SystemMonitor singleton instance."""
    global _system_monitor
    if _system_monitor is None:
        _system_monitor = SystemMonitor()
    return _system_monitor