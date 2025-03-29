"""Bluetooth adapter management functionality."""

import logging
import platform
import asyncio
import time
import os
from typing import Dict, Any, List, Optional

# For Windows adapter detection
try:
    import wmi
    import winreg
    HAS_WMI = True
except ImportError:
    HAS_WMI = False

class BleAdapterManager:
    """Manage Bluetooth adapters, including detection, selection, and recovery."""
    
    def __init__(self, metrics_collector=None, logger=None):
        """Initialize the adapter manager."""
        self.logger = logger or logging.getLogger(__name__)
        self.metrics_collector = metrics_collector
        self.system_platform = platform.system()
        self.selected_adapter = None
        self._adapter_address = None
        self._adapter_index = None  # For Linux (hci0, hci1, etc.)
        
    async def get_adapters(self) -> List[Dict[str, Any]]:
        """
        Get a list of all available Bluetooth adapters on the system.
        
        Returns:
            List of adapter information dictionaries
        """
        adapters = []
        
        try:
            if self.system_platform == "Windows":
                adapters = await self._get_windows_adapters()
            elif self.system_platform == "Linux":
                adapters = await self._get_linux_adapters()
            elif self.system_platform == "Darwin":  # macOS
                adapters = await self._get_macos_adapters()
            else:
                self.logger.warning(f"Unsupported platform: {self.system_platform}")
                
            # Record metrics if available
            if self.metrics_collector and hasattr(self.metrics_collector, "record_adapter_scan"):
                self.metrics_collector.record_adapter_scan(
                    platform=self.system_platform,
                    adapter_count=len(adapters),
                    success=len(adapters) > 0
                )
                
            return adapters
        except Exception as e:
            self.logger.error(f"Error getting adapters: {e}", exc_info=True)
            
            # Record error in metrics if available
            if self.metrics_collector and hasattr(self.metrics_collector, "record_adapter_error"):
                self.metrics_collector.record_adapter_error(
                    operation="get_adapters",
                    error_type=type(e).__name__,
                    error_message=str(e)
                )
            
            return []
    
    async def _get_windows_adapters(self) -> List[Dict[str, Any]]:
        """
        Get available Bluetooth adapters on Windows.
        
        Returns:
            List of adapter information
        """
        adapters = []
        
        if not HAS_WMI:
            self.logger.warning("WMI not available, cannot enumerate Windows adapters")
            return adapters
        
        try:
            w = wmi.WMI()
            
            # Get Bluetooth adapters from Device Manager
            for adapter in w.Win32_PnPEntity():
                if (adapter.PNPDeviceID and 
                    ("bluetooth" in adapter.PNPDeviceID.lower() or 
                     (hasattr(adapter, 'Caption') and adapter.Caption and "bluetooth" in adapter.Caption.lower()))):
                    
                    adapter_info = {
                        "device_id": adapter.DeviceID,
                        "name": adapter.Caption or "Unknown Bluetooth Adapter",
                        "manufacturer": adapter.Manufacturer or "Unknown",
                        "status": adapter.Status or "Unknown",
                        "pnp_id": adapter.PNPDeviceID,
                        "address": "Unknown",  # Will be populated later if possible
                        "platform": "Windows",
                        "available": adapter.Status == "OK",
                        "hardware": {
                            "vendor": adapter.Manufacturer or "Unknown",
                            "model": adapter.Caption or "Unknown",
                            "firmware": "Unknown"
                        }
                    }
                    
                    # Try to get MAC address from registry
                    try:
                        registry_path = r"SYSTEM\CurrentControlSet\Services\BTHPORT\Parameters\Keys"
                        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, registry_path) as key:
                            i = 0
                            while True:
                                try:
                                    addr = winreg.EnumKey(key, i)
                                    if len(addr) == 12:  # MAC address length
                                        formatted_addr = ':'.join([addr[i:i+2] for i in range(0, 12, 2)])
                                        adapter_info["address"] = formatted_addr.upper()
                                        break
                                    i += 1
                                except WindowsError:
                                    break
                    except Exception as e:
                        self.logger.debug(f"Could not get adapter MAC from registry: {e}")
                    
                    adapters.append(adapter_info)
            
            # If no adapters found, try an alternative approach
            if not adapters:
                # Look at network adapters
                for adapter in w.Win32_NetworkAdapter():
                    if adapter.Name and "bluetooth" in adapter.Name.lower():
                        adapters.append({
                            "device_id": adapter.DeviceID,
                            "name": adapter.Name,
                            "manufacturer": adapter.Manufacturer or "Unknown",
                            "address": adapter.MACAddress or "Unknown",
                            "platform": "Windows",
                            "available": adapter.NetEnabled,
                            "hardware": {
                                "vendor": adapter.Manufacturer or "Unknown",
                                "model": adapter.ProductName or adapter.Name,
                                "firmware": "Unknown"
                            }
                        })
            
            return adapters
        
        except Exception as e:
            self.logger.error(f"Error enumerating Windows adapters: {e}", exc_info=True)
            return []
    
    async def _get_linux_adapters(self) -> List[Dict[str, Any]]:
        """
        Get available Bluetooth adapters on Linux.
        
        Returns:
            List of adapter information
        """
        adapters = []
        
        try:
            # Use hciconfig to get adapter list
            import subprocess
            result = subprocess.check_output(
                ["hciconfig", "-a"], 
                stderr=subprocess.STDOUT
            ).decode("utf-8")
            
            # Parse hciconfig output
            current_adapter = None
            for line in result.splitlines():
                line = line.strip()
                
                # New adapter section
                if line.startswith("hci"):
                    # Save previous adapter if any
                    if current_adapter:
                        adapters.append(current_adapter)
                    
                    # Start new adapter
                    hci_name = line.split(":", 1)[0]
                    current_adapter = {
                        "device_id": hci_name,
                        "name": f"Bluetooth Adapter ({hci_name})",
                        "address": "Unknown",
                        "platform": "Linux",
                        "available": "UP RUNNING" in line,
                        "hardware": {
                            "vendor": "Unknown",
                            "model": "Unknown",
                            "firmware": "Unknown"
                        }
                    }
                
                # Look for adapter details
                elif current_adapter:
                    if "BD Address:" in line:
                        current_adapter["address"] = line.split("BD Address:", 1)[1].strip()
                    elif "Manufacturer:" in line:
                        current_adapter["hardware"]["vendor"] = line.split("Manufacturer:", 1)[1].strip()
                    elif "HCI Version:" in line:
                        parts = line.split("HCI Version:", 1)[1].strip()
                        if "Revision:" in parts:
                            version, revision = parts.split("Revision:")
                            current_adapter["hardware"]["firmware"] = f"HCI {version.strip()} (Rev {revision.strip()})"
            
            # Add the last adapter if any
            if current_adapter:
                adapters.append(current_adapter)
            
            return adapters
        
        except Exception as e:
            self.logger.error(f"Error enumerating Linux adapters: {e}", exc_info=True)
            return []
    
    async def _get_macos_adapters(self) -> List[Dict[str, Any]]:
        """
        Get available Bluetooth adapters on macOS.
        
        Returns:
            List of adapter information
        """
        adapters = []
        
        try:
            # On macOS, we need to use system_profiler
            import subprocess
            result = subprocess.check_output(
                ["system_profiler", "SPBluetoothDataType"], 
                stderr=subprocess.STDOUT
            ).decode("utf-8")
            
            # Extract controller information
            controller_info = {}
            current_section = None
            
            for line in result.splitlines():
                line = line.strip()
                
                # Look for Bluetooth Controller section
                if "Bluetooth Controller" in line:
                    current_section = "controller"
                    continue
                
                # Process controller data
                if current_section == "controller" and ":" in line:
                    key, value = [part.strip() for part in line.split(":", 1)]
                    controller_info[key] = value
            
            # Create adapter entry
            if controller_info:
                adapters.append({
                    "device_id": "macos_adapter",
                    "name": controller_info.get("Name", "Bluetooth Adapter"),
                    "address": controller_info.get("Address", "Unknown"),
                    "platform": "macOS",
                    "available": True,  # Assume available if detected
                    "hardware": {
                        "vendor": controller_info.get("Manufacturer", "Apple Inc."),
                        "model": controller_info.get("Transport", "Unknown"),
                        "firmware": controller_info.get("Firmware Version", "Unknown")
                    }
                })
            
            return adapters
        
        except Exception as e:
            self.logger.error(f"Error enumerating macOS adapters: {e}", exc_info=True)
            return []
    
    async def select_adapter(self, adapter_id: str) -> Dict[str, Any]:
        """
        Select a specific Bluetooth adapter for use.
        
        Args:
            adapter_id: Identifier for the adapter (device_id, address, etc.)
            
        Returns:
            Result of the selection operation
        """
        try:
            # Get all adapters
            adapters = await self.get_adapters()
            
            if not adapters:
                return {
                    "status": "error",
                    "message": "No Bluetooth adapters available"
                }
            
            # Find the specified adapter
            selected = None
            for adapter in adapters:
                # Match by any identifier
                if (adapter.get("device_id") == adapter_id or
                    adapter.get("address") == adapter_id or
                    adapter.get("name") == adapter_id):
                    selected = adapter
                    break
            
            if not selected:
                return {
                    "status": "error",
                    "message": f"Adapter {adapter_id} not found"
                }
            
            # Store selected adapter
            self.selected_adapter = selected
            self._adapter_address = selected.get("address")
            
            # Platform-specific adapter selection
            if self.system_platform == "Windows":
                # Windows-specific selection (limited support in Bleak)
                result = await self._select_windows_adapter(selected)
            elif self.system_platform == "Linux":
                # Linux adapter selection
                result = await self._select_linux_adapter(selected)
            elif self.system_platform == "Darwin":
                # macOS doesn't support selecting adapters
                result = {
                    "status": "warning",
                    "message": "macOS does not support selecting specific adapters"
                }
            else:
                result = {
                    "status": "error",
                    "message": f"Unsupported platform: {self.system_platform}"
                }
            
            # Record metrics if available
            if self.metrics_collector and hasattr(self.metrics_collector, "record_adapter_selection"):
                self.metrics_collector.record_adapter_selection(
                    adapter_id=adapter_id,
                    success=result.get("status") != "error",
                    platform=self.system_platform
                )
            
            # Add adapter info to result
            result["adapter"] = selected
            
            return result
        
        except Exception as e:
            self.logger.error(f"Error selecting adapter: {e}", exc_info=True)
            
            # Record error in metrics if available
            if self.metrics_collector and hasattr(self.metrics_collector, "record_adapter_error"):
                self.metrics_collector.record_adapter_error(
                    operation="select_adapter",
                    error_type=type(e).__name__,
                    error_message=str(e)
                )
            
            return {
                "status": "error",
                "message": f"Error selecting adapter: {str(e)}"
            }
    
    async def _select_windows_adapter(self, adapter: Dict[str, Any]) -> Dict[str, Any]:
        """
        Select a specific adapter on Windows.
        
        Args:
            adapter: Adapter information
            
        Returns:
            Result of the selection operation
        """
        # Windows has limited adapter selection support with Bleak
        # We'll store the selection for future scan operations
        self._adapter_address = adapter.get("address")
        
        # Set environment variable that might be used by Bleak in future
        if self._adapter_address:
            os.environ["BLEAK_ADAPTER_ADDRESS"] = self._adapter_address
        
        return {
            "status": "success",
            "message": f"Selected adapter: {adapter.get('name')} ({adapter.get('address')})"
        }
    
    async def _select_linux_adapter(self, adapter: Dict[str, Any]) -> Dict[str, Any]:
        """
        Select a specific adapter on Linux.
        
        Args:
            adapter: Adapter information
            
        Returns:
            Result of the selection operation
        """
        device_id = adapter.get("device_id")
        
        if not device_id:
            return {
                "status": "error",
                "message": "Missing device ID for Linux adapter"
            }
        
        # Store the HCI device index (hci0, hci1, etc.)
        self._adapter_index = device_id
        
        # Set environment variable for Bleak to use
        os.environ["BLEAK_ADAPTER"] = device_id
        
        return {
            "status": "success",
            "message": f"Selected adapter: {device_id} ({adapter.get('address')})"
        }
    
    async def reset_adapter(self, adapter_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Reset a Bluetooth adapter.
        
        Args:
            adapter_id: Optional adapter ID to reset, uses selected/default adapter if None
            
        Returns:
            Result of the reset operation
        """
        try:
            # If adapter_id is provided, select it first
            if adapter_id:
                select_result = await self.select_adapter(adapter_id)
                if select_result.get("status") == "error":
                    return select_result
            
            # Platform-specific reset
            if self.system_platform == "Windows":
                result = await self._reset_windows_adapter()
            elif self.system_platform == "Linux":
                result = await self._reset_linux_adapter()
            elif self.system_platform == "Darwin":
                result = await self._reset_macos_adapter()
            else:
                result = {
                    "status": "error",
                    "message": f"Unsupported platform: {self.system_platform}"
                }
            
            # Record metrics if available
            if self.metrics_collector and hasattr(self.metrics_collector, "record_adapter_reset"):
                self.metrics_collector.record_adapter_reset(
                    adapter_id=adapter_id or self._adapter_address or "default",
                    success=result.get("status") != "error",
                    platform=self.system_platform
                )
            
            return result
        
        except Exception as e:
            self.logger.error(f"Error resetting adapter: {e}", exc_info=True)
            
            # Record error in metrics if available
            if self.metrics_collector and hasattr(self.metrics_collector, "record_adapter_error"):
                self.metrics_collector.record_adapter_error(
                    operation="reset_adapter",
                    error_type=type(e).__name__,
                    error_message=str(e)
                )
            
            return {
                "status": "error",
                "message": f"Error resetting adapter: {str(e)}"
            }
    
    async def _reset_windows_adapter(self) -> Dict[str, Any]:
        """
        Reset a Bluetooth adapter on Windows.
        
        Returns:
            Result of the reset operation
        """
        try:
            # Try PowerShell command to restart the Bluetooth service
            import subprocess
            
            # First try restarting the Bluetooth Support Service
            self.logger.info("Attempting to restart Windows Bluetooth Support Service")
            subprocess.run(
                ["powershell", "-Command", "Restart-Service -Name bthserv -Force"],
                check=False
            )
            
            # Give it time to restart
            await asyncio.sleep(2)
            
            # Check if service is running
            status_result = subprocess.run(
                ["powershell", "-Command", "Get-Service -Name bthserv | Select-Object -ExpandProperty Status"],
                capture_output=True,
                text=True,
                check=False
            )
            
            service_running = "Running" in status_result.stdout
            
            if not service_running:
                return {
                    "status": "error",
                    "message": "Failed to restart Bluetooth services"
                }
            
            # Give Bluetooth stack time to initialize
            await asyncio.sleep(3)
            
            return {
                "status": "success",
                "message": "Bluetooth adapter reset successfully"
            }
        
        except Exception as e:
            self.logger.error(f"Error resetting Windows adapter: {e}", exc_info=True)
            return {
                "status": "error",
                "message": f"Error resetting adapter: {str(e)}"
            }
    
    async def _reset_linux_adapter(self) -> Dict[str, Any]:
        """
        Reset a Bluetooth adapter on Linux.
        
        Returns:
            Result of the reset operation
        """
        try:
            # Use hciconfig to reset the adapter
            import subprocess
            
            hci_device = self._adapter_index or "hci0"
            
            # Down the interface
            self.logger.info(f"Resetting Linux Bluetooth adapter {hci_device}")
            subprocess.run(["sudo", "hciconfig", hci_device, "down"], check=False)
            
            # Wait a moment
            await asyncio.sleep(1)
            
            # Bring it back up
            subprocess.run(["sudo", "hciconfig", hci_device, "up"], check=False)
            
            # Wait for initialization
            await asyncio.sleep(2)
            
            # Check if adapter is up
            result = subprocess.run(
                ["hciconfig", hci_device], 
                capture_output=True,
                text=True,
                check=False
            )
            
            if "UP RUNNING" not in result.stdout:
                return {
                    "status": "error",
                    "message": f"Failed to reset adapter {hci_device}"
                }
            
            return {
                "status": "success",
                "message": f"Bluetooth adapter {hci_device} reset successfully"
            }
        
        except Exception as e:
            self.logger.error(f"Error resetting Linux adapter: {e}", exc_info=True)
            return {
                "status": "error",
                "message": f"Error resetting adapter: {str(e)}"
            }
    
    async def _reset_macos_adapter(self) -> Dict[str, Any]:
        """
        Reset a Bluetooth adapter on macOS.
        
        Returns:
            Result of the reset operation
        """
        try:
            # For macOS, we can try to restart the Bluetooth daemon
            # This requires admin privileges
            self.logger.info("Attempting to restart macOS Bluetooth service")
            
            # Try Apple Script to toggle Bluetooth
            import subprocess
            
            # Turn Bluetooth off
            subprocess.run([
                "osascript", "-e", 
                "tell application \"System Preferences\" to activate", "-e",
                "tell application \"System Events\" to tell process \"System Preferences\" to click menu item \"Bluetooth\" of menu \"View\" of menu bar 1", "-e",
                "delay 1", "-e",
                "tell application \"System Events\" to tell process \"System Preferences\" to click checkbox 1 of window \"Bluetooth\"", "-e",
                "delay 2"
            ], check=False)
            
            # Turn Bluetooth back on
            subprocess.run([
                "osascript", "-e",
                "tell application \"System Events\" to tell process \"System Preferences\" to click checkbox 1 of window \"Bluetooth\"", "-e",
                "delay 2", "-e",
                "tell application \"System Preferences\" to quit"
            ], check=False)
            
            # Give Bluetooth time to initialize
            await asyncio.sleep(5)
            
            return {
                "status": "success",
                "message": "Attempted to reset Bluetooth adapter"
            }
        
        except Exception as e:
            self.logger.error(f"Error resetting macOS adapter: {e}", exc_info=True)
            return {
                "status": "error",
                "message": f"Error resetting adapter: {str(e)}"
            }
    
    def get_selected_adapter(self) -> Optional[Dict[str, Any]]:
        """Get the currently selected adapter or None if no adapter is selected."""
        return self.selected_adapter
    
    def get_adapter_address(self) -> Optional[str]:
        """Get the currently selected adapter address or None if no adapter is selected."""
        return self._adapter_address
    
    def get_adapter_index(self) -> Optional[str]:
        """Get the currently selected adapter index (Linux) or None if no adapter is selected."""
        return self._adapter_index