"""Bluetooth adapter management and configuration."""

import logging
import asyncio
import platform
import subprocess
import sys
import re
import time
from typing import Dict, Any, List, Optional, Tuple, Union
import uuid

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
        
        # Try to discover adapters on initialization -- REMOVED, will discover on demand
        # try:
        #     self._initialization_task = asyncio.create_task(self.discover_adapters())
        # except RuntimeError:
        #     # If not running in async context, we'll discover later
        #     pass
    
    async def discover_adapters(self, max_retries: int = 3, retry_delay: float = 2.0) -> List[Dict[str, Any]]:
        """
        Discover Bluetooth adapters on the system.
        
        Args:
            max_retries: Maximum number of retries for discovering adapters.
            retry_delay: Delay between retries in seconds.
        
        Returns:
            List of adapter dictionaries
        """
        attempt = 0
        last_error = None
        adapters = []
        enhanced_adapters = []
        
        while attempt < max_retries:
            try:
                self.logger.info(f"Discovering Bluetooth adapters on {platform.system()} (attempt {attempt + 1}/{max_retries})")
                
                adapters = []
                
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
                
                self.logger.info(f"Discovered {len(adapters)} raw adapter(s)")
                self.logger.debug(f"Raw adapters: {adapters}")
                
                # Enhance adapter information
                enhanced_adapters = []
                for adapter in adapters:
                    try:
                        # Make sure all adapters have required fields
                        enhanced_adapter = {
                            "id": adapter.get("address", adapter.get("id", str(uuid.uuid4()))),
                            "name": adapter.get("name", "Unknown Adapter"),
                            "address": adapter.get("address", "00:00:00:00:00:00"),
                            "description": adapter.get("description", ""),
                            "manufacturer": adapter.get("manufacturer", "Unknown"),
                            "status": adapter.get("status", AdapterStatus.UNKNOWN.value),
                            "powered": adapter.get("powered", False),
                            "discovering": adapter.get("discovering", False),
                            "pairable": adapter.get("pairable", False),
                            "paired_devices": adapter.get("paired_devices", 0),
                            "firmware_version": adapter.get("firmware_version", "Unknown"),
                            "supported_features": adapter.get("supported_features", []),
                            "system_info": self._system_info
                        }
                        enhanced_adapters.append(enhanced_adapter)
                        
                        # Update internal state
                        adapter_id = enhanced_adapter["id"]
                        self._adapters[adapter_id] = enhanced_adapter
                        self._adapter_details[adapter_id] = {
                            "last_seen": time.time(),
                            "error_count": 0,
                            "last_error": None
                        }
                        self.logger.debug(f"Processed adapter: {enhanced_adapter['name']} (ID: {adapter_id})")
                    except Exception as e:
                        self.logger.error(f"Error processing adapter {adapter.get('name', 'Unknown')}: {str(e)}")
                        continue
                
                self.logger.info(f"Discovered {len(enhanced_adapters)} Bluetooth adapters")
                
                # If no adapters found, log a warning
                if not enhanced_adapters:
                    self.logger.warning("No Bluetooth adapters discovered")
                
                return enhanced_adapters
            except Exception as e:
                attempt += 1
                last_error = str(e)
                self.logger.warning(f"Attempt {attempt} failed to discover adapters: {e}")
                if attempt < max_retries:
                    await asyncio.sleep(retry_delay)
                continue
        
        self.logger.error(f"Failed to discover adapters after {max_retries} attempts: {last_error}", exc_info=True)
        
        # Return any adapters we managed to discover, even if we encountered errors
        if enhanced_adapters:
            self.logger.info(f"Returning {len(enhanced_adapters)} adapters despite discovery errors")
            return enhanced_adapters
        elif adapters:
            # If we have raw adapters but failed to enhance them, return basic info
            basic_adapters = []
            for adapter in adapters:
                try:
                    basic_adapter = {
                        "id": adapter.get("address", adapter.get("id", str(uuid.uuid4()))),
                        "name": adapter.get("name", "Unknown Adapter"),
                        "address": adapter.get("address", "00:00:00:00:00:00"),
                        "description": adapter.get("description", ""),
                        "manufacturer": adapter.get("manufacturer", "Unknown"),
                        "status": AdapterStatus.UNKNOWN.value,
                        "powered": False,
                        "discovering": False,
                        "pairable": False,
                        "paired_devices": 0,
                        "firmware_version": "Unknown",
                        "supported_features": [],
                        "system_info": self._system_info
                    }
                    basic_adapters.append(basic_adapter)
                    self.logger.debug(f"Created basic adapter: {basic_adapter['name']} (ID: {basic_adapter['id']})")
                except Exception as e:
                    self.logger.error(f"Error creating basic adapter info for {adapter.get('name', 'Unknown')}: {str(e)}")
                    continue
            
            if basic_adapters:
                self.logger.info(f"Returning {len(basic_adapters)} basic adapters as fallback")
                self._adapters.update({a["id"]: a for a in basic_adapters})
                return basic_adapters
        
        # If we have nothing to return, raise an error
        raise BleAdapterError(f"Failed to discover adapters: {last_error}")
    
    async def get_adapter_info(self, adapter_id: Optional[str] = None, max_retries: int = 3, retry_delay: float = 1.0) -> Dict[str, Any]:
        """
        Get detailed information about a specific adapter or the current adapter.
        
        Args:
            adapter_id: ID of the adapter to get information for. If None, use current adapter.
            max_retries: Maximum number of retries for getting adapter information.
            retry_delay: Delay between retries in seconds.
        
        Returns:
            Dictionary containing adapter information
        """
        if adapter_id is None:
            if self._current_adapter is None:
                raise BleAdapterError("No adapter selected and no ID provided")
            adapter_id = self._current_adapter
        
        attempt = 0
        last_error = None
        
        while attempt < max_retries:
            try:
                self.logger.info(f"Getting information for adapter {adapter_id} (attempt {attempt + 1}/{max_retries})")
                
                if adapter_id not in self._adapters:
                    # Refresh adapter list if the requested adapter is not found
                    await self.discover_adapters()
                    if adapter_id not in self._adapters:
                        raise BleAdapterError(f"Adapter {adapter_id} not found")
                
                adapter = self._adapters[adapter_id]
                
                # Attempt to get real-time status if possible
                status_info = await self._get_adapter_status(adapter_id)
                adapter.update(status_info)
                
                # Update last seen timestamp
                self._adapter_details[adapter_id]["last_seen"] = time.time()
                
                self.logger.info(f"Successfully retrieved information for adapter {adapter_id}")
                return adapter
            except Exception as e:
                attempt += 1
                last_error = str(e)
                self.logger.warning(f"Attempt {attempt} failed to get adapter info for {adapter_id}: {e}")
                if adapter_id in self._adapter_details:
                    self._adapter_details[adapter_id]["error_count"] += 1
                    self._adapter_details[adapter_id]["last_error"] = last_error
                if attempt < max_retries:
                    await asyncio.sleep(retry_delay)
                continue
        
        self.logger.error(f"Failed to get adapter info for {adapter_id} after {max_retries} attempts: {last_error}", exc_info=True)
        raise BleAdapterError(f"Failed to get adapter info: {last_error}")
    
    async def select_adapter(self, request: AdapterSelectionRequest) -> AdapterResult:
        """
        Select a specific Bluetooth adapter to use.
        
        Args:
            request: AdapterSelectionRequest object containing the adapter ID
        
        Returns:
            AdapterResult object indicating success or failure
        """
        adapter_id = request.id
        try:
            self.logger.info(f"Selecting Bluetooth adapter: {adapter_id}")
            
            if adapter_id not in self._adapters:
                # Refresh adapter list
                await self.discover_adapters()
                if adapter_id not in self._adapters:
                    raise BleAdapterError(f"Adapter {adapter_id} not found")
            
            # Update current adapter
            self._current_adapter = adapter_id
            
            # Log success
            self.logger.info(f"Successfully selected adapter: {adapter_id}")
            
            # Emit event
            ble_event_bus.emit("adapter_selected", {
                "adapter_id": adapter_id,
                "adapter_name": self._adapters[adapter_id].get("name", "Unknown")
            })
            
            return AdapterResult(
                success=True,
                message=f"Selected adapter {adapter_id}",
                adapter_id=adapter_id
            )
        except Exception as e:
            error_msg = f"Failed to select adapter {adapter_id}: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            if adapter_id in self._adapter_details:
                self._adapter_details[adapter_id]["error_count"] += 1
                self._adapter_details[adapter_id]["last_error"] = str(e)
            return AdapterResult(
                success=False,
                message=error_msg,
                adapter_id=adapter_id
            )
    
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
            
            # Get adapter status - REMOVED await keywords here
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
        """
        Discover Bluetooth adapters on Windows using Windows Management Instrumentation.
        """
        try:
            import win32com.client
            
            self.logger.info("Querying Windows Management Instrumentation for Bluetooth adapters")
            wmi = win32com.client.GetObject("winmgmts:")
            adapters = []
            
            # Query for Bluetooth devices
            bt_devices = wmi.ExecQuery("SELECT * FROM Win32_PnPEntity WHERE Description LIKE '%Bluetooth%' OR Name LIKE '%Bluetooth%'")
            self.logger.info(f"Found {len(bt_devices)} potential Bluetooth devices")
            self.logger.debug(f"Bluetooth devices: {bt_devices}")
            
            for device in bt_devices:
                try:
                    name = device.Name if device.Name else "Unknown Bluetooth Adapter"
                    device_id = device.DeviceID if device.DeviceID else str(uuid.uuid4())
                    status = device.Status if device.Status else "UNKNOWN"
                    
                    adapter = {
                        "id": device_id,
                        "name": name,
                        "address": device_id,  # On Windows, we use DeviceID as address
                        "description": device.Description if device.Description else "Bluetooth Adapter",
                        "manufacturer": device.Manufacturer if device.Manufacturer else "Unknown",
                        "status": status,
                        "powered": status == "OK",
                        "discovering": False,
                        "pairable": False,
                        "paired_devices": 0,
                        "firmware_version": device.DriverVersion if device.DriverVersion else "Unknown",
                        "supported_features": ["BLE"] if "Bluetooth LE" in name or "Bluetooth Low Energy" in name else []
                    }
                    adapters.append(adapter)
                    self.logger.debug(f"Added adapter: {name} (ID: {device_id})")
                except Exception as e:
                    self.logger.error(f"Error processing Windows Bluetooth device: {str(e)}")
                    continue
            
            self.logger.info(f"Discovered {len(adapters)} Bluetooth adapter(s) on Windows")
            if not adapters:
                self.logger.warning("No Bluetooth adapters found on Windows, creating a default adapter")
                adapters.append(self._create_default_adapter())
            
            return adapters
        except Exception as e:
            self.logger.error(f"Failed to discover Windows adapters: {str(e)}", exc_info=True)
            self.logger.info("Creating a default adapter as fallback due to discovery failure")
            return [self._create_default_adapter()]
    
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
        
        # If still no adapters found, create a default one
        if not adapters:
            adapters.append(self._create_default_adapter())
        
        return adapters
    
    async def _discover_mac_adapters(self) -> List[Dict[str, Any]]:
        """Discover adapters on macOS."""
        adapters = []
        
        # On macOS, there's usually just the built-in adapter
        try:
            # Use system_profiler to get Bluetooth info
            result = subprocess.run(
                ["system_profiler", "SPBluetoothDataType"],
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode == 0:
                # REPLACE WITH BETTER REGEX PATTERNS:
                # Address pattern with more flexible format matching
                address_match = re.search(r"Address: ([0-9a-fA-F:]{2}(?::[0-9a-fA-F]{2}){5})", result.stdout)
                name_match = re.search(r"(?:Manufacturer|Name): ([^\n]+)", result.stdout)
                version_match = re.search(r"Bluetooth Version: ([0-9\.]+)", result.stdout)
                
                address = address_match.group(1) if address_match else "00:00:00:00:00:00"
                name = name_match.group(1).strip() if name_match else "Bluetooth Controller"
                version = version_match.group(1) if version_match else "Unknown"
                
                # ADD THIS: More comprehensive adapter info
                adapter = {
                    "name": name,
                    "address": address,
                    "description": f"macOS Bluetooth {version}",
                    "version": version,
                    "available": True,  # Assume available if detected
                    "platform": "darwin"
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

    def get_adapters(self):
        """Get a list of available adapters.
        
        Returns:
            list: List of adapter information dictionaries
        """
        try:
            # If we already have adapters cached, return them
            if getattr(self, "_adapters", None):
                return self._adapters
                
            # Otherwise, create a default adapter
            import platform
            default_adapter = {
                "id": "default",
                "name": f"{platform.system()} Bluetooth Adapter",
                "address": "00:00:00:00:00:00",
                "available": True,
                "status": "active",
                "platform": platform.system().lower()
            }
            
            self._adapters = [default_adapter]
            return self._adapters
        except Exception as e:
            self.logger.error(f"Error getting adapters: {e}")
            return [{
                "id": "error",
                "name": "Error Adapter",
                "address": "00:00:00:00:00:00",
                "available": False,
                "status": "error",
                "error": str(e)
            }]

    def _initialize_adapters_sync(self):
        """Synchronous initialization of adapters for the constructor."""
        try:
            # Platform-specific adapter lookup without async
            if platform.system() == 'Windows':
                self._adapters = self._discover_windows_adapters_sync()
            elif platform.system() == 'Linux':
                self._adapters = self._discover_linux_adapters_sync()
            elif platform.system() == 'Darwin':
                self._adapters = self._discover_mac_adapters_sync() 
            else:
                self._adapters = []
        except Exception as e:
            self.logger.error(f"Error during adapter initialization: {e}")
            self._adapters = []

# Singleton instance (to be initialized on first use)
_adapter_manager = None

def get_adapter_manager() -> BleAdapterManager:
    """Get the singleton adapter manager instance."""
    global _adapter_manager
    if (_adapter_manager is None):
        _adapter_manager = BleAdapterManager()
    return _adapter_manager