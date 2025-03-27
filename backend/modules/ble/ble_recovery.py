import asyncio
import logging
import platform
import time
import subprocess
from typing import Dict, Any, Callable, List, Coroutine, Optional
import uuid

class BleErrorRecovery:
    """
    BLE error recovery and management system.
    Provides methods to recover from common BLE errors and track error statistics.
    """
    
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        self.platform = platform.system().lower()
        self.recovery_attempts = 0
        self.successful_recoveries = 0
        self.adapter_resets = 0
        self.error_counts = {}  # Tracks counts of different error types
        self.recovery_history = []  # Stores history of recent recovery operations
        self.max_history = 50  # Maximum number of history entries to keep
    
    def _detect_platform(self) -> str:
        """Detect the current platform for platform-specific recovery methods."""
        system = platform.system().lower()
        
        if system == "windows":
            return "windows"
        elif system == "linux":
            return "linux"
        elif system == "darwin":
            return "macos"
        else:
            self.logger.warning(f"Unknown platform: {system}, defaulting to generic implementation")
            return "generic"
    
    def record_error(self, error_type: str, details: str = None):
        """
        Record an error occurrence for statistics.
        
        Args:
            error_type: Type of error (e.g., 'ConnectionError', 'TimeoutError')
            details: Additional error details
        """
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
        
        # Add to history
        entry = {
            "timestamp": time.time(),
            "error_type": error_type,
            "details": details
        }
        
        self.recovery_history.append(entry)
        
        # Trim history if needed
        if len(self.recovery_history) > self.max_history:
            self.recovery_history = self.recovery_history[-self.max_history:]
    
    async def recover_connection(self, 
                               device_address: str, 
                               connection_func: Callable[[], Coroutine],
                               max_attempts: int = 3,
                               backoff_factor: float = 1.5) -> bool:
        """
        Attempt to recover a failed connection using exponential backoff.
        
        Args:
            device_address: Address of the device to connect to
            connection_func: Async function that attempts to establish connection
            max_attempts: Maximum number of recovery attempts
            backoff_factor: Multiplier for increasing delay between attempts
            
        Returns:
            bool: Whether recovery was successful
        """
        self.recovery_attempts += 1
        attempt = 0
        delay = 1.0  # Start with 1 second delay
        
        while attempt < max_attempts:
            attempt += 1
            self.logger.info(f"Recovery attempt {attempt}/{max_attempts} for {device_address}")
            
            try:
                # Try the connection function
                result = await connection_func()
                if result:
                    self.logger.info(f"Recovery successful on attempt {attempt}")
                    self.successful_recoveries += 1
                    return True
            except Exception as e:
                self.logger.warning(f"Recovery attempt {attempt} failed: {e}")
                self.record_error(f"RecoveryAttempt{attempt}", str(e))
            
            # Only sleep if this isn't the last attempt
            if attempt < max_attempts:
                # Exponential backoff
                await asyncio.sleep(delay)
                delay *= backoff_factor
        
        self.logger.warning(f"All recovery attempts failed for {device_address}")
        return False
    
    async def reset_adapter(self):
        """
        Reset the Bluetooth adapter with better error handling
        Returns:
            bool: Success status
        """
        self.logger.info("Attempting to reset Bluetooth adapter...")
        self.adapter_resets += 1
        
        try:
            # Determine which platform-specific reset method to call
            platform_type = self._detect_platform()
            
            if platform_type == "windows":
                result = await self._reset_windows_adapter()
            elif platform_type == "linux":
                result = await self._reset_linux_adapter()
            elif platform_type == "macos":
                result = await self._reset_mac_adapter()
            else:
                self.logger.error(f"Unsupported platform for adapter reset: {platform_type}")
                return False
            
            success = result.get("status") == "success"
            if success:
                self.logger.info("Adapter reset successful")
            else:
                self.logger.error(f"Adapter reset failed: {result.get('message', 'Unknown error')}")
            
            return success
        
        except Exception as error:
            self.logger.error(f"Error resetting adapter: {error}")
            return False
    
    async def _reset_windows_adapter(self):
        """Windows-specific adapter reset."""
        self.logger.info("Attempting to reset Windows Bluetooth adapter")
        
        try:
            # Method 1: Use PowerShell to disable and re-enable the Bluetooth radio
            import subprocess
            
            # Find the Bluetooth adapter
            self.logger.info("Finding Bluetooth adapter...")
            find_cmd = "Get-PnpDevice | Where-Object {$_.Class -eq 'Bluetooth'} | Select-Object Status,DeviceID,FriendlyName | ConvertTo-Json"
            ps_process = subprocess.run(["powershell", "-Command", find_cmd], capture_output=True, text=True)
            
            if ps_process.returncode != 0:
                raise Exception(f"Failed to find Bluetooth devices: {ps_process.stderr}")
            
            # Parse output
            if not ps_process.stdout.strip():
                return {"status": "error", "message": "No Bluetooth adapters found"}
            
            # Simple case - try toggling all Bluetooth devices
            self.logger.info("Disabling Bluetooth adapter")
            disable_cmd = "Get-PnpDevice | Where-Object {$_.Class -eq 'Bluetooth'} | Disable-PnpDevice -Confirm:$false"
            disable_process = subprocess.run(["powershell", "-Command", disable_cmd], capture_output=True, text=True)
            
            # Wait a moment
            await asyncio.sleep(2)
            
            self.logger.info("Enabling Bluetooth adapter")
            enable_cmd = "Get-PnpDevice | Where-Object {$_.Class -eq 'Bluetooth'} | Enable-PnpDevice -Confirm:$false"
            enable_process = subprocess.run(["powershell", "-Command", enable_cmd], capture_output=True, text=True)
            
            if disable_process.returncode != 0 or enable_process.returncode != 0:
                self.logger.warning("Powershell method failed, trying sc service restart")
                
                # Fallback method: Restart Bluetooth service
                service_cmd = "Restart-Service bthserv -Force"
                service_process = subprocess.run(["powershell", "-Command", service_cmd], capture_output=True, text=True)
                
                if service_process.returncode != 0:
                    raise Exception(f"Failed to restart Bluetooth service: {service_process.stderr}")
            
            # Allow some time for the adapter to initialize
            await asyncio.sleep(3)
            return {"status": "success", "message": "Bluetooth adapter reset complete"}
            
        except Exception as e:
            self.logger.error(f"Error during Windows Bluetooth reset: {e}")
            return {"status": "error", "message": str(e)}

    async def _reset_linux_adapter(self):
        """Linux-specific adapter reset."""
        try:
            import subprocess
            
            # Get the interface name
            result = subprocess.run(["hciconfig"], capture_output=True, text=True)
            if result.returncode != 0:
                raise Exception(f"Failed to get Bluetooth interfaces: {result.stderr}")
            
            # Parse hciconfig output to get interface names
            interfaces = []
            for line in result.stdout.splitlines():
                if ":" in line and "hci" in line:
                    interfaces.append(line.split(":")[0].strip())
            
            if not interfaces:
                return {"status": "error", "message": "No Bluetooth interfaces found"}
            
            # Reset each interface
            for interface in interfaces:
                self.logger.info(f"Resetting interface {interface}")
                
                # Down the interface
                down_result = subprocess.run(["sudo", "hciconfig", interface, "down"], capture_output=True, text=True)
                if down_result.returncode != 0:
                    self.logger.warning(f"Failed to bring down {interface}: {down_result.stderr}")
                
                # Wait a moment
                await asyncio.sleep(1)
                
                # Reset the interface
                reset_result = subprocess.run(["sudo", "hciconfig", interface, "reset"], capture_output=True, text=True)
                if reset_result.returncode != 0:
                    self.logger.warning(f"Failed to reset {interface}: {reset_result.stderr}")
                
                # Wait a moment
                await asyncio.sleep(1)
                
                # Up the interface
                up_result = subprocess.run(["sudo", "hciconfig", interface, "up"], capture_output=True, text=True)
                if up_result.returncode != 0:
                    self.logger.warning(f"Failed to bring up {interface}: {up_result.stderr}")
            
            # Allow some time for the interfaces to initialize
            await asyncio.sleep(2)
            return {"status": "success", "message": f"Reset {len(interfaces)} Bluetooth interfaces"}
            
        except Exception as e:
            self.logger.error(f"Error during Linux Bluetooth reset: {e}")
            return {"status": "error", "message": str(e)}

    async def _reset_mac_adapter(self):
        """macOS-specific adapter reset."""
        try:
            import subprocess
            
            # On macOS, we can toggle Bluetooth using the blueutil command
            # Check if blueutil is installed
            check_result = subprocess.run(["which", "blueutil"], capture_output=True, text=True)
            if check_result.returncode != 0:
                return {"status": "error", "message": "blueutil not installed. Install with: brew install blueutil"}
            
            # Turn Bluetooth off
            self.logger.info("Turning Bluetooth off")
            off_result = subprocess.run(["blueutil", "--power", "0"], capture_output=True, text=True)
            if off_result.returncode != 0:
                raise Exception(f"Failed to turn off Bluetooth: {off_result.stderr}")
            
            # Wait a moment
            await asyncio.sleep(2)
            
            # Turn Bluetooth on
            self.logger.info("Turning Bluetooth on")
            on_result = subprocess.run(["blueutil", "--power", "1"], capture_output=True, text=True)
            if on_result.returncode != 0:
                raise Exception(f"Failed to turn on Bluetooth: {on_result.stderr}")
            
            # Allow some time for Bluetooth to initialize
            await asyncio.sleep(3)
            return {"status": "success", "message": "Bluetooth adapter reset complete"}
            
        except Exception as e:
            self.logger.error(f"Error during macOS Bluetooth reset: {e}")
            return {"status": "error", "message": str(e)}

    def get_error_statistics(self) -> Dict[str, Any]:
        """Get statistics about BLE errors and recovery attempts."""
        success_rate = 0
        if self.recovery_attempts > 0:
            success_rate = (self.successful_recoveries / self.recovery_attempts) * 100
            
        return {
            "recovery_attempts": self.recovery_attempts,
            "successful_recoveries": self.successful_recoveries,
            "recovery_success_rate": success_rate,
            "adapter_resets": self.adapter_resets,
            "error_counts": self.error_counts,
            "recent_errors": self.recovery_history[-10:] if self.recovery_history else [],
            "timestamp": time.time()
        }
    
    async def diagnose_connection_issues(self, device_address: Optional[str] = None) -> Dict[str, Any]:
        """
        Run diagnostics to identify potential connection issues.
        
        Args:
            device_address: Optional specific device to diagnose
            
        Returns:
            Dict: Diagnostic results
        """
        results = {
            "timestamp": time.time(),
            "platform": self.platform_type,
            "adapter_status": "unknown",
            "issues_detected": [],
            "recommendations": []
        }
        
        # Check adapter status
        adapter_status = await self._check_adapter_status()
        results["adapter_status"] = adapter_status
        
        # Add diagnostics based on error history
        if self.recovery_history:
            # Look for patterns in recent errors
            timeout_count = sum(1 for entry in self.recovery_history[-10:] 
                              if "timeout" in entry["error_type"].lower())
            
            disconnect_count = sum(1 for entry in self.recovery_history[-10:] 
                                 if "disconnect" in entry["error_type"].lower())
            
            permission_count = sum(1 for entry in self.recovery_history[-10:] 
                                 if "permission" in entry["error_type"].lower())
            
            # Add issues and recommendations based on patterns
            if timeout_count >= 3:
                results["issues_detected"].append("Multiple connection timeouts detected")
                results["recommendations"].append("Check for signal interference or increase connection timeout")
                
            if disconnect_count >= 3:
                results["issues_detected"].append("Frequent disconnections detected")
                results["recommendations"].append("Check device battery level and signal strength")
                
            if permission_count >= 1:
                results["issues_detected"].append("Bluetooth permission issues detected")
                results["recommendations"].append("Verify Bluetooth permissions for the application")
        
        return results
    
    async def _check_adapter_status(self) -> str:
        """Check the status of the Bluetooth adapter."""
        try:
            if self.platform_type == "windows":
                cmd = "powershell -Command \"& {Get-PnpDevice -Class Bluetooth | Where-Object {$_.Status -eq 'OK'} | Select-Object Status}\""
            elif self.platform_type == "linux":
                cmd = "hciconfig hci0 status | grep 'UP RUNNING'"
            elif self.platform_type == "macos":
                cmd = "system_profiler SPBluetoothDataType | grep 'Bluetooth Power'"
            else:
                return "unknown"
                
            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if stdout:
                if "OK" in stdout.decode() or "UP RUNNING" in stdout.decode() or "On" in stdout.decode():
                    return "active"
            
            return "inactive"
        except Exception as e:
            self.logger.error(f"Error checking adapter status: {e}")
            return "error"