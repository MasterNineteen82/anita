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
        self.platform_type = self._detect_platform()
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
    
    async def reset_adapter(self) -> bool:
        """
        Reset the Bluetooth adapter to recover from serious errors.
        Platform-specific implementations.
        
        Returns:
            bool: Whether reset was successful
        """
        self.adapter_resets += 1
        self.logger.info(f"Resetting Bluetooth adapter (platform: {self.platform_type})")
        
        try:
            if self.platform_type == "windows":
                return await self._reset_adapter_windows()
            elif self.platform_type == "linux":
                return await self._reset_adapter_linux()
            elif self.platform_type == "macos":
                return await self._reset_adapter_macos()
            else:
                self.logger.warning(f"No adapter reset implementation for {self.platform_type}")
                return False
        except Exception as e:
            self.logger.error(f"Error resetting adapter: {e}")
            return False
    
    async def _reset_adapter_windows(self) -> bool:
        """Reset Bluetooth adapter on Windows."""
        try:
            # Use PowerShell to disable and re-enable Bluetooth adapter
            disable_cmd = "powershell -Command \"& {Get-PnpDevice -Class Bluetooth | Where-Object {$_.Status -eq 'OK'} | Disable-PnpDevice -Confirm:$false}\""
            enable_cmd = "powershell -Command \"& {Get-PnpDevice -Class Bluetooth | Where-Object {$_.Status -eq 'Error'} | Enable-PnpDevice -Confirm:$false}\""
            
            # Disable adapter
            self.logger.info("Disabling Bluetooth adapter")
            process = await asyncio.create_subprocess_shell(
                disable_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                self.logger.error(f"Error disabling adapter: {stderr.decode()}")
                return False
            
            # Wait before re-enabling
            await asyncio.sleep(2)
            
            # Enable adapter
            self.logger.info("Re-enabling Bluetooth adapter")
            process = await asyncio.create_subprocess_shell(
                enable_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                self.logger.error(f"Error enabling adapter: {stderr.decode()}")
                return False
            
            # Wait for adapter to initialize
            await asyncio.sleep(3)
            
            self.logger.info("Bluetooth adapter reset successfully")
            return True
        except Exception as e:
            self.logger.error(f"Error during Windows Bluetooth reset: {e}")
            return False
    
    async def _reset_adapter_linux(self) -> bool:
        """Reset Bluetooth adapter on Linux."""
        try:
            # Use rfkill to block and unblock Bluetooth
            block_cmd = "sudo rfkill block bluetooth"
            unblock_cmd = "sudo rfkill unblock bluetooth"
            restart_cmd = "sudo systemctl restart bluetooth"
            
            # Block Bluetooth
            self.logger.info("Blocking Bluetooth adapter")
            process = await asyncio.create_subprocess_shell(
                block_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            # Wait before unblocking
            await asyncio.sleep(2)
            
            # Unblock Bluetooth
            self.logger.info("Unblocking Bluetooth adapter")
            process = await asyncio.create_subprocess_shell(
                unblock_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            # Restart Bluetooth service
            self.logger.info("Restarting Bluetooth service")
            process = await asyncio.create_subprocess_shell(
                restart_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            # Wait for adapter to initialize
            await asyncio.sleep(3)
            
            self.logger.info("Bluetooth adapter reset successfully")
            return True
        except Exception as e:
            self.logger.error(f"Error during Linux Bluetooth reset: {e}")
            return False
    
    async def _reset_adapter_macos(self) -> bool:
        """Reset Bluetooth adapter on macOS."""
        try:
            # Use macOS command to toggle Bluetooth
            toggle_off = "osascript -e 'tell application \"System Preferences\" to activate' -e 'tell application \"System Events\" to tell process \"System Preferences\" to click menu item \"Bluetooth\" of menu \"View\" of menu bar 1' -e 'tell application \"System Events\" to tell process \"System Preferences\" to click checkbox 1 of window \"Bluetooth\"'"
            toggle_on = "osascript -e 'tell application \"System Preferences\" to activate' -e 'tell application \"System Events\" to tell process \"System Preferences\" to click menu item \"Bluetooth\" of menu \"View\" of menu bar 1' -e 'tell application \"System Events\" to tell process \"System Preferences\" to click checkbox 1 of window \"Bluetooth\"'"
            
            # Turn off Bluetooth
            self.logger.info("Turning off Bluetooth")
            process = await asyncio.create_subprocess_shell(
                toggle_off,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
            
            # Wait before turning back on
            await asyncio.sleep(2)
            
            # Turn on Bluetooth
            self.logger.info("Turning on Bluetooth")
            process = await asyncio.create_subprocess_shell(
                toggle_on,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
            
            # Wait for adapter to initialize
            await asyncio.sleep(3)
            
            self.logger.info("Bluetooth adapter reset successfully")
            return True
        except Exception as e:
            self.logger.error(f"Error during macOS Bluetooth reset: {e}")
            return False
    
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