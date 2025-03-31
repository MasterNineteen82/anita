"""Bluetooth adapter management and configuration."""

import logging
import asyncio
import platform
import subprocess
import sys
import re
import time
from typing import Dict, Any, List, Optional, Tuple, Union

import bleak
from bleak import BleakScanner, BleakError

from backend.modules.ble.utils.events import ble_event_bus
from backend.modules.ble.models import (
    BleAdapter, AdapterStatus, AdapterSelectionRequest, 
    AdapterResetRequest, AdapterResult
)
from .exceptions import BleAdapterError, BleNotSupportedError

def get_bleak_version():
    """Get the Bleak version safely."""
    try:
        from importlib.metadata import version
        return version("bleak")
    except (ImportError, Exception):
        return "Unknown"

class BleAdapterManager:
    """
    Manages Bluetooth adapters on the system.
    
    Provides capabilities for:
    - Discovering available adapters
    - Selecting specific adapters
    - Configuring adapter settings
    - Resetting adapters when issues occur
    """
    
    def __init__(self, logger=None):
        """
        Initialize the adapter manager.
        
        Args:
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        self._adapters = {}
        self._current_adapter = None
        self._adapter_details = {}
        self._system_info = self._get_system_info()
        
        # Platform-specific initialization
        self._is_windows = platform.system() == "Windows"
        self._is_linux = platform.system() == "Linux"
        self._is_mac = platform.system() == "Darwin"
        
        # Try to discover adapters on initialization
        try:
            asyncio.create_task(self.discover_adapters())
        except RuntimeError:
            # If not running in async context, we'll discover later
            pass
    
    async def discover_adapters(self) -> List[Dict[str, Any]]:
        """
        Discover Bluetooth adapters on the system.
        
        Returns:
            List of adapter dictionaries
        """
        adapters = []
        
        try:
            if self._is_windows:
                # On Windows, use Windows Management Instrumentation
                adapters = await self._discover_windows_adapters()
            elif self._is_linux:
                # On Linux, use BlueZ tools
                adapters = await self._discover_linux_adapters()
            elif self._is_mac:
                # On macOS, look for default adapter
                adapters = await self._discover_mac_adapters()
            else:
                self.logger.warning(f"Unsupported platform: {platform.system()}")
                adapters = [self._create_default_adapter()]
            
            # Cache the adapters
            self._adapters = {a["address"]: a for a in adapters}
            
            # If no current adapter but we found some, set the first one
            if not self._current_adapter and adapters:
                self._current_adapter = adapters[0]["address"]
            
            # Emit event
            try:
                # Use create_task to properly handle the coroutine
                asyncio.create_task(ble_event_bus.emit("adapters_discovered", {
                    "adapters": adapters,
                    "count": len(adapters)
                }))
            except RuntimeError:
                # If not in an event loop, log but don't crash
                self.logger.debug("Could not emit adapters_discovered event - no running event loop")
            
            return adapters
        except Exception as e:
            self.logger.error(f"Error discovering adapters: {e}", exc_info=True)
            
            # Create a default adapter as fallback
            default_adapter = self._create_default_adapter()
            adapters = [default_adapter]
            self._adapters = {default_adapter["address"]: default_adapter}
            self._current_adapter = default_adapter["address"]
            
            return adapters
    
    async def select_adapter(self, request: Union[AdapterSelectionRequest, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Select a specific Bluetooth adapter.
        
        Args:
            request: Adapter selection request with address or index
            
        Returns:
            Dictionary with selection result
        """
        # Convert dict to model if necessary
        if isinstance(request, dict):
            request = AdapterSelectionRequest(**request)
        
        try:
            # Make sure we have discovered adapters
            if not self._adapters:
                await self.discover_adapters()
            
            # If still no adapters, we can't select one
            if not self._adapters:
                raise BleAdapterError("No Bluetooth adapters found")
            
            # Try to select by address
            if request.address:
                if request.address in self._adapters:
                    self._current_adapter = request.address
                    adapter = self._adapters[request.address]
                else:
                    raise BleAdapterError(f"Adapter with address {request.address} not found")
            # Try to select by index
            elif request.index is not None:
                adapter_list = list(self._adapters.values())
                if 0 <= request.index < len(adapter_list):
                    adapter = adapter_list[request.index]
                    self._current_adapter = adapter["address"]
                else:
                    raise BleAdapterError(f"Adapter index {request.index} out of range")
            else:
                # If neither address nor index provided, use current adapter
                if not self._current_adapter:
                    # If no current adapter, use the first one
                    self._current_adapter = list(self._adapters.keys())[0]
                adapter = self._adapters[self._current_adapter]
            
            # Configure the adapter if needed
            if request.power_on:
                await self._power_adapter(adapter["address"], True)
            
            # Emit event
            ble_event_bus.emit("adapter_selected", {
                "adapter": adapter,
                "address": adapter["address"]
            })
            
            return {
                "selected": True,
                "adapter": adapter,
                "current": True
            }
        except BleAdapterError:
            raise
        except Exception as e:
            self.logger.error(f"Error selecting adapter: {e}", exc_info=True)
            raise BleAdapterError(f"Error selecting adapter: {e}")
    
    async def get_adapter_status(self, address: Optional[str] = None) -> Dict[str, Any]:
        """
        Get the status of a Bluetooth adapter.
        
        Args:
            address: Optional adapter address (uses current if None)
            
        Returns:
            Dictionary with adapter status
        """
        try:
            # Use specified address or current adapter
            adapter_address = address or self._current_adapter
            
            # If no adapter, try to discover
            if not adapter_address:
                await self.discover_adapters()
                adapter_address = self._current_adapter
            
            if not adapter_address:
                raise BleAdapterError("No Bluetooth adapter available")
            
            # Get adapter status
            if self._is_windows:
                status = await self._get_windows_adapter_status(adapter_address)
            elif self._is_linux:
                status = await self._get_linux_adapter_status(adapter_address)
            elif self._is_mac:
                status = await self._get_mac_adapter_status(adapter_address)
            else:
                # Default status for unsupported platforms
                status = {
                    "available": True,
                    "powered": True,
                    "service_running": True,
                    "address": adapter_address,
                    "name": "Unknown Adapter"
                }
            
            # Get adapter details
            adapter = self._adapters.get(adapter_address, {
                "address": adapter_address,
                "name": "Unknown Adapter"
            })
            
            # Create full status result
            result = {
                **status,
                "adapter": adapter,
                "system": self._system_info,
                "current": adapter_address == self._current_adapter
            }
            
            return result
        except BleAdapterError:
            raise
        except Exception as e:
            self.logger.error(f"Error getting adapter status: {e}", exc_info=True)
            raise BleAdapterError(f"Error getting adapter status: {e}")
    
    async def reset_adapter(self, request: Optional[Union[AdapterResetRequest, Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Reset a Bluetooth adapter.
        
        Args:
            request: Optional reset request with configuration
            
        Returns:
            Dictionary with reset result
        """
        # Convert dict to model if necessary
        if isinstance(request, dict):
            request = AdapterResetRequest(**request)
        
        # Use defaults if not provided
        if request is None:
            request = AdapterResetRequest()
        
        try:
            # Use specified address or current adapter
            adapter_address = request.address or self._current_adapter
            
            # If no adapter, try to discover
            if not adapter_address:
                await self.discover_adapters()
                adapter_address = self._current_adapter
            
            if not adapter_address:
                raise BleAdapterError("No Bluetooth adapter available to reset")
            
            # Log the reset attempt
            self.logger.info(f"Resetting Bluetooth adapter {adapter_address}")
            
            # Emit event before reset
            ble_event_bus.emit("adapter_resetting", {
                "address": adapter_address
            })
            
            # Perform the reset
            actions_taken = []
            
            if self._is_windows:
                success, actions = await self._reset_windows_adapter(adapter_address, request)
                actions_taken.extend(actions)
            elif self._is_linux:
                success, actions = await self._reset_linux_adapter(adapter_address, request)
                actions_taken.extend(actions)
            elif self._is_mac:
                success, actions = await self._reset_mac_adapter(adapter_address, request)
                actions_taken.extend(actions)
            else:
                # Unsupported platform - just power cycle
                await self._power_adapter(adapter_address, False)
                await asyncio.sleep(1.0)
                await self._power_adapter(adapter_address, True)
                success = True
                actions_taken.append("Power cycled adapter")
            
            # Get updated status
            status = await self.get_adapter_status(adapter_address)
            
            # Emit event after reset
            ble_event_bus.emit("adapter_reset", {
                "address": adapter_address,
                "success": success,
                "actions_taken": actions_taken,
                "status": status
            })
            
            return {
                "success": success,
                "message": "Adapter reset complete" if success else "Adapter reset failed",
                "adapter_address": adapter_address,
                "adapter_status": status,
                "actions_taken": actions_taken
            }
        except BleAdapterError:
            raise
        except Exception as e:
            self.logger.error(f"Error resetting adapter: {e}", exc_info=True)
            raise BleAdapterError(f"Error resetting adapter: {e}")
    
    def get_current_adapter(self) -> Optional[Dict[str, Any]]:
        """
        Get the current adapter.
        
        Returns:
            Dictionary with adapter information or None
        """
        if not self._current_adapter or self._current_adapter not in self._adapters:
            return None
        
        return self._adapters[self._current_adapter]
    
    # Platform-specific methods
    async def _discover_windows_adapters(self) -> List[Dict[str, Any]]:
        """Discover adapters on Windows."""
        adapters = []
        
        try:
            # Try to use Windows Management Instrumentation
            import wmi
            
            wmi_conn = wmi.WMI()
            bt_devices = wmi_conn.Win32_PnPEntity(PNPClass="Bluetooth")
            
            for device in bt_devices:
                if "adapter" in device.Name.lower() or "radio" in device.Name.lower():
                    # This is likely a Bluetooth adapter
                    adapter = {
                        "name": device.Name,
                        "address": device.DeviceID,
                        "description": device.Description,
                        "manufacturer": device.Manufacturer,
                        "status": device.Status,
                        "system_name": device.SystemName
                    }
                    adapters.append(adapter)
        except Exception as e:
            self.logger.warning(f"Error using WMI to discover adapters: {e}")
        
        # If WMI failed or found no adapters, fall back to bleak
        if not adapters:
            try:
                # See if we can get the default adapter
                scanner = BleakScanner()
                bleak_adapters = getattr(scanner, "_adapter", None)
                
                if bleak_adapters and hasattr(bleak_adapters, "interfaces"):
                    for idx, interface in enumerate(bleak_adapters.interfaces):
                        adapter = {
                            "name": f"Bluetooth Adapter {idx}",
                            "address": interface,
                            "index": idx,
                            "description": "Discovered via Bleak"
                        }
                        adapters.append(adapter)
            except Exception as e:
                self.logger.warning(f"Error using bleak to discover adapters: {e}")
        
        # If still no adapters, create a default one
        if not adapters:
            adapters.append(self._create_default_adapter())
        
        return adapters
    
    async def _discover_linux_adapters(self) -> List[Dict[str, Any]]:
        """Discover adapters on Linux."""
        adapters = []
        
        try:
            # Use bluetoothctl to list adapters
            result = subprocess.run(
                ["bluetoothctl", "list"],
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode == 0:
                # Parse the output
                # Expected format: "Controller XX:XX:XX:XX:XX:XX DeviceName"
                for line in result.stdout.splitlines():
                    if line.strip().startswith("Controller"):
                        parts = line.strip().split(" ", 2)
                        if len(parts) >= 2:
                            address = parts[1]
                            name = parts[2] if len(parts) > 2 else f"Adapter {address}"
                            
                            adapter = {
                                "name": name,
                                "address": address,
                                "description": "Bluetooth Controller"
                            }
                            adapters.append(adapter)
        except Exception as e:
            self.logger.warning(f"Error using bluetoothctl to discover adapters: {e}")
        
        # If bluetoothctl failed, try hciconfig
        if not adapters:
            try:
                result = subprocess.run(
                    ["hciconfig", "-a"],
                    capture_output=True,
                    text=True,
                    check=False
                )
                
                if result.returncode == 0:
                    # Parse the output to find adapters
                    current_adapter = None
                    
                    for line in result.stdout.splitlines():
                        line = line.strip()
                        
                        if line.startswith("hci"):
                            # New adapter
                            parts = line.split(":", 1)
                            if len(parts) >= 1:
                                hci_name = parts[0]
                                current_adapter = {
                                    "name": hci_name,
                                    "address": "",
                                    "description": "Bluetooth Controller"
                                }
                        
                        elif current_adapter and "BD Address:" in line:
                            # Extract address
                            match = re.search(r"BD Address: ([0-9A-F:]+)", line)
                            if match:
                                current_adapter["address"] = match.group(1)
                                adapters.append(current_adapter)
                                current_adapter = None
            except Exception as e:
                self.logger.warning(f"Error using hciconfig to discover adapters: {e}")
        
        # If still no adapters, create a default one
        if not adapters:
            adapters.append(self._create_default_adapter())
        
        return adapters
    
    async def _discover_mac_adapters(self) -> List[Dict[str, Any]]:
        """Discover adapters on macOS."""
        adapters = []
        
        # On macOS, there's usually just the built-in adapter
        # Try to get some information about it
        try:
            # Use system_profiler to get Bluetooth info
            result = subprocess.run(
                ["system_profiler", "SPBluetoothDataType"],
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode == 0:
                # Try to extract the address
                address_match = re.search(r"Address: ([0-9a-fA-F:]+)", result.stdout)
                name_match = re.search(r"Manufacturer: ([^\n]+)", result.stdout)
                
                address = address_match.group(1) if address_match else "00:00:00:00:00:00"
                name = name_match.group(1).strip() if name_match else "Bluetooth Controller"
                
                adapter = {
                    "name": name,
                    "address": address,
                    "description": "Built-in Bluetooth"
                }
                adapters.append(adapter)
        except Exception as e:
            self.logger.warning(f"Error discovering macOS adapters: {e}")
        
        # If discovery failed, create a default adapter
        if not adapters:
            adapters.append(self._create_default_adapter())
        
        return adapters
    
    async def _power_adapter(self, address: str, power_on: bool) -> bool:
        """
        Power on or off a Bluetooth adapter.
        
        Args:
            address: Adapter address
            power_on: True to power on, False to power off
            
        Returns:
            True if successful
        """
        try:
            if self._is_windows:
                # On Windows, we can't reliably power adapters via API
                # Just indicate success
                return True
            elif self._is_linux:
                # On Linux, use bluetoothctl or hciconfig
                adapter = self._get_hci_name(address)
                
                if adapter:
                    cmd = ["sudo", "hciconfig", adapter, "up" if power_on else "down"]
                    result = subprocess.run(cmd, capture_output=True, check=False)
                    return result.returncode == 0
                return False
            elif self._is_mac:
                # On macOS, we can't directly power adapters
                # Could try to use blueutil but it's not usually installed
                return True
            else:
                return False
        except Exception as e:
            self.logger.error(f"Error powering adapter: {e}", exc_info=True)
            return False
    
    async def _get_windows_adapter_status(self, address: str) -> Dict[str, Any]:
        """Get adapter status on Windows."""
        status = {
            "available": False,
            "powered": False,
            "service_running": False,
            "address": address
        }
        
        try:
            # Check if Bluetooth service is running
            import wmi
            
            wmi_conn = wmi.WMI()
            bt_service = wmi_conn.Win32_Service(Name="bthserv")
            
            if bt_service:
                service_status = bt_service[0].State
                status["service_running"] = service_status == "Running"
            
            # Check adapter status
            bt_devices = wmi_conn.Win32_PnPEntity(DeviceID=address)
            
            if bt_devices:
                device = bt_devices[0]
                status["available"] = device.Status == "OK"
                status["powered"] = device.Status == "OK"
                status["name"] = device.Name
            else:
                # If we can't find the adapter by exact ID, look for similar
                bt_devices = wmi_conn.Win32_PnPEntity(PNPClass="Bluetooth")
                
                for device in bt_devices:
                    if address in device.DeviceID:
                        status["available"] = device.Status == "OK"
                        status["powered"] = device.Status == "OK"
                        status["name"] = device.Name
                        break
        except Exception as e:
            self.logger.warning(f"Error getting Windows adapter status: {e}")
            
            # Just assume the adapter is available
            status.update({
                "available": True,
                "powered": True,
                "service_running": True
            })
        
        return status
    
    async def _get_linux_adapter_status(self, address: str) -> Dict[str, Any]:
        """Get adapter status on Linux."""
        status = {
            "available": False,
            "powered": False,
            "service_running": False,
            "address": address
        }
        
        try:
            # Check if Bluetooth service is running
            service_result = subprocess.run(
                ["systemctl", "is-active", "bluetooth"],
                capture_output=True,
                text=True,
                check=False
            )
            
            status["service_running"] = service_result.stdout.strip() == "active"
            
            # Get adapter details
            hci_name = self._get_hci_name(address)
            
            if hci_name:
                # Use hciconfig to check if adapter is up
                hci_result = subprocess.run(
                    ["hciconfig", hci_name],
                    capture_output=True,
                    text=True,
                    check=False
                )
                
                status["available"] = "UP" in hci_result.stdout
                status["powered"] = "UP RUNNING" in hci_result.stdout
                
                # Try to get the adapter name
                matches = re.search(r"Name: '([^']+)'", hci_result.stdout)
                if matches:
                    status["name"] = matches.group(1)
        except Exception as e:
            self.logger.warning(f"Error getting Linux adapter status: {e}")
            
            # Just assume the adapter is available
            status.update({
                "available": True,
                "powered": True,
                "service_running": True
            })
        
        return status
    
    async def _get_mac_adapter_status(self, address: str) -> Dict[str, Any]:
        """Get adapter status on macOS."""
        status = {
            "available": False,
            "powered": False,
            "service_running": False,
            "address": address
        }
        
        try:
            # Use system_profiler to check Bluetooth status
            result = subprocess.run(
                ["system_profiler", "SPBluetoothDataType"],
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode == 0:
                status["available"] = "Bluetooth Power" in result.stdout
                status["powered"] = "Bluetooth Power: On" in result.stdout
                status["service_running"] = "Bluetooth Power: On" in result.stdout
                
                # Try to extract the name
                name_match = re.search(r"Hardware Settings:\n\s+Name: ([^\n]+)", result.stdout)
                if name_match:
                    status["name"] = name_match.group(1).strip()
        except Exception as e:
            self.logger.warning(f"Error getting macOS adapter status: {e}")
            
            # Just assume the adapter is available
            status.update({
                "available": True,
                "powered": True,
                "service_running": True
            })
        
        return status
    
    async def _reset_windows_adapter(
        self, address: str, request: AdapterResetRequest
    ) -> Tuple[bool, List[str]]:
        """Reset adapter on Windows."""
        actions_taken = []
        
        try:
            # First try to restart the Bluetooth service
            if request.restart_service:
                actions_taken.append("Restarting Bluetooth service")
                
                try:
                    # Use PowerShell to restart the service
                    subprocess.run(
                        ["powershell", "-Command", "Restart-Service bthserv -Force"],
                        capture_output=True,
                        check=False
                    )
                except Exception as e:
                    self.logger.warning(f"Error restarting Bluetooth service: {e}")
            
            # Wait a moment
            await asyncio.sleep(2)
            
            if request.disconnect_devices:
                actions_taken.append("Disconnecting devices (not supported on Windows)")
            
            # Try to rescan
            if request.rescan:
                actions_taken.append("Triggering scan")
                
                try:
                    # Use PowerShell to trigger a scan
                    subprocess.run(
                        ["powershell", "-Command", "Get-PnpDevice -Class Bluetooth | ForEach-Object { Disable-PnpDevice -InstanceId $_.InstanceId -Confirm:$false }"],
                        capture_output=True,
                        check=False
                    )
                    
                    await asyncio.sleep(1)
                    
                    subprocess.run(
                        ["powershell", "-Command", "Get-PnpDevice -Class Bluetooth | ForEach-Object { Enable-PnpDevice -InstanceId $_.InstanceId -Confirm:$false }"],
                        capture_output=True,
                        check=False
                    )
                except Exception as e:
                    self.logger.warning(f"Error triggering scan: {e}")
            
            # We can't reliably power cycle the adapter on Windows
            return True, actions_taken
        except Exception as e:
            self.logger.error(f"Error resetting Windows adapter: {e}", exc_info=True)
            return False, actions_taken
    
    async def _reset_linux_adapter(
        self, address: str, request: AdapterResetRequest
    ) -> Tuple[bool, List[str]]:
        """Reset adapter on Linux."""
        actions_taken = []
        
        try:
            # Get hci name
            hci_name = self._get_hci_name(address)
            
            if not hci_name:
                return False, actions_taken
            
            # Restart Bluetooth service if requested
            if request.restart_service:
                actions_taken.append("Restarting Bluetooth service")
                
                try:
                    subprocess.run(
                        ["sudo", "systemctl", "restart", "bluetooth"],
                        capture_output=True,
                        check=False
                    )
                except Exception as e:
                    self.logger.warning(f"Error restarting Bluetooth service: {e}")
            
            # Disconnect devices if requested
            if request.disconnect_devices:
                actions_taken.append("Disconnecting devices")
                
                try:
                    # Get connected devices
                    result = subprocess.run(
                        ["bluetoothctl", "devices"],
                        capture_output=True,
                        text=True,
                        check=False
                    )
                    
                    devices = []
                    for line in result.stdout.splitlines():
                        if line.strip().startswith("Device "):
                            parts = line.strip().split(" ", 2)
                            if len(parts) >= 2:
                                devices.append(parts[1])
                    
                    # Disconnect each device
                    for device in devices:
                        try:
                            subprocess.run(
                                ["bluetoothctl", "disconnect", device],
                                capture_output=True,
                                check=False
                            )
                        except Exception:
                            pass
                except Exception as e:
                    self.logger.warning(f"Error disconnecting devices: {e}")
            
            # Power cycle the adapter
            actions_taken.append("Power cycling adapter")
            
            try:
                # Down
                subprocess.run(
                    ["sudo", "hciconfig", hci_name, "down"],
                    capture_output=True,
                    check=False
                )
                
                await asyncio.sleep(1)
                
                # Up
                subprocess.run(
                    ["sudo", "hciconfig", hci_name, "up"],
                    capture_output=True,
                    check=False
                )
            except Exception as e:
                self.logger.warning(f"Error power cycling adapter: {e}")
            
            # Trigger scan if requested
            if request.rescan:
                actions_taken.append("Triggering scan")
                
                try:
                    subprocess.run(
                        ["bluetoothctl", "scan", "on"],
                        capture_output=True,
                        check=False
                    )
                    
                    # Let it scan for a moment
                    await asyncio.sleep(2)
                    
                    subprocess.run(
                        ["bluetoothctl", "scan", "off"],
                        capture_output=True,
                        check=False
                    )
                except Exception as e:
                    self.logger.warning(f"Error triggering scan: {e}")
            
            return True, actions_taken
        except Exception as e:
            self.logger.error(f"Error resetting Linux adapter: {e}", exc_info=True)
            return False, actions_taken
    
    async def _reset_mac_adapter(
        self, address: str, request: AdapterResetRequest
    ) -> Tuple[bool, List[str]]:
        """Reset adapter on macOS."""
        actions_taken = []
        
        try:
            # On macOS, we can't easily restart the Bluetooth service
            # or power cycle the adapter from command line
            
            # Try to toggle Bluetooth off and on
            actions_taken.append("Toggling Bluetooth")
            
            try:
                # First check if blueutil is installed
                check_result = subprocess.run(
                    ["which", "blueutil"],
                    capture_output=True,
                    check=False
                )
                
                if check_result.returncode == 0:
                    # blueutil is installed, use it
                    # Turn off
                    subprocess.run(
                        ["blueutil", "--power", "0"],
                        capture_output=True,
                        check=False
                    )
                    
                    await asyncio.sleep(2)
                    
                    # Turn on
                    subprocess.run(
                        ["blueutil", "--power", "1"],
                        capture_output=True,
                        check=False
                    )
                else:
                    # blueutil not available, just log
                    actions_taken[-1] = "Toggling Bluetooth (not available)"
            except Exception as e:
                self.logger.warning(f"Error toggling Bluetooth: {e}")
            
            # If requested to disconnect devices, we could try
            if request.disconnect_devices:
                actions_taken.append("Disconnecting devices (not supported on macOS)")
            
            # If requested to rescan, we could try
            if request.rescan:
                actions_taken.append("Triggering scan")
                
                try:
                    if check_result.returncode == 0:
                        # Use blueutil to trigger a scan
                        subprocess.run(
                            ["blueutil", "--inquiry", "2"],
                            capture_output=True,
                            check=False
                        )
                    else:
                        actions_taken[-1] = "Triggering scan (not available)"
                except Exception as e:
                    self.logger.warning(f"Error triggering scan: {e}")
            
            return True, actions_taken
        except Exception as e:
            self.logger.error(f"Error resetting macOS adapter: {e}", exc_info=True)
            return False, actions_taken
    
    def _get_hci_name(self, address: str) -> Optional[str]:
        """Get hci name from address."""
        # First check cache
        if address in self._adapter_details and "hci_name" in self._adapter_details[address]:
            return self._adapter_details[address]["hci_name"]
        
        # Try to get hci name
        for adapter in self._adapters.values():
            if adapter["address"] == address and "name" in adapter and adapter["name"].startswith("hci"):
                # Cache it
                if address not in self._adapter_details:
                    self._adapter_details[address] = {}
                self._adapter_details[address]["hci_name"] = adapter["name"]
                return adapter["name"]
        
        # Try to get it from hciconfig
        try:
            result = subprocess.run(
                ["hciconfig", "-a"],
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode == 0:
                current_hci = None
                
                for line in result.stdout.splitlines():
                    line = line.strip()
                    
                    if line.startswith("hci"):
                        # New adapter
                        parts = line.split(":", 1)
                        if len(parts) >= 1:
                            current_hci = parts[0]
                    
                    elif current_hci and "BD Address:" in line:
                        # Extract address
                        match = re.search(r"BD Address: ([0-9A-F:]+)", line)
                        if match and match.group(1) == address:
                            # Cache it
                            if address not in self._adapter_details:
                                self._adapter_details[address] = {}
                            self._adapter_details[address]["hci_name"] = current_hci
                            return current_hci
        except Exception as e:
            self.logger.warning(f"Error getting hci name: {e}")
        
        return None
    
    def _create_default_adapter(self) -> Dict[str, Any]:
        """Create a default adapter."""
        return {
            "name": "Default Bluetooth Adapter",
            "address": "00:00:00:00:00:00",
            "description": "Default adapter"
        }
    
    def _get_system_info(self) -> Dict[str, Any]:
        """Get system information."""
        return {
            "platform": platform.system(),
            "platform_version": platform.version(),
            "python_version": platform.python_version(),
            "bleak_version": get_bleak_version(),
            "os_details": {
                "release": platform.release(),
                "machine": platform.machine()
            }
        }

# Singleton instance (to be initialized on first use)
_adapter_manager = None

def get_adapter_manager() -> BleAdapterManager:
    """Get the singleton adapter manager instance."""
    global _adapter_manager
    if _adapter_manager is None:
        _adapter_manager = BleAdapterManager()
    return _adapter_manager