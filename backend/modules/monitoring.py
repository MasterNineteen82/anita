# backend/modules/monitoring.py
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any
from backend.modules.ble.ble_manager import BLEManager
from backend.ws.manager import manager
from backend.ws.events import create_event, DeviceStatus
from .monitors import Monitor, monitoring_manager

logger = logging.getLogger(__name__)

class MonitoringManager:
    """
    Manages monitoring components across the application.
    Provides a centralized registry for all monitors and their lifecycle.
    """
    
    def __init__(self):
        self.monitors = {}
        self.running = False
        self._task = None
        
    def register_monitor(self, monitor: Monitor) -> None:
        """
        Register a new monitor with the manager.
        
        Args:
            monitor: Monitor instance to register
        """
        if monitor.name in self.monitors:
            logger.warning(f"Monitor with name '{monitor.name}' already registered, replacing")
            
        self.monitors[monitor.name] = monitor
        logger.debug(f"Registered monitor: {monitor.name}")
        
    def unregister_monitor(self, monitor_name: str) -> None:
        """
        Unregister a monitor by name.
        
        Args:
            monitor_name: Name of the monitor to unregister
        """
        if monitor_name in self.monitors:
            # Stop the monitor if running
            monitor = self.monitors[monitor_name]
            if monitor.is_running:
                monitor.stop()
                
            # Remove from registry
            del self.monitors[monitor_name]
            logger.debug(f"Unregistered monitor: {monitor_name}")
            
    def get_monitor(self, monitor_name: str) -> Monitor:
        """
        Get a monitor by name.
        
        Args:
            monitor_name: Name of the monitor to retrieve
            
        Returns:
            The monitor instance if found
            
        Raises:
            KeyError: If monitor not found
        """
        if monitor_name not in self.monitors:
            raise KeyError(f"Monitor '{monitor_name}' not found")
            
        return self.monitors[monitor_name]
    
    async def start_all(self) -> None:
        """Start all registered monitors."""
        if self.running:
            logger.warning("Monitoring manager already running")
            return
            
        self.running = True
        logger.info("Starting all monitors")
        
        # Start each monitor
        for name, monitor in self.monitors.items():
            try:
                if not monitor.is_running:
                    await monitor.start()
                    logger.info(f"Started monitor: {name}")
            except Exception as e:
                logger.error(f"Failed to start monitor '{name}': {str(e)}")
                
    async def stop_all(self) -> None:
        """Stop all registered monitors."""
        if not self.running:
            logger.warning("Monitoring manager not running")
            return
            
        self.running = False
        logger.info("Stopping all monitors")
        
        # Stop each monitor
        for name, monitor in self.monitors.items():
            try:
                if monitor.is_running:
                    await monitor.stop()
                    logger.info(f"Stopped monitor: {name}")
            except Exception as e:
                logger.error(f"Failed to stop monitor '{name}': {str(e)}")
                
    def get_status(self) -> dict:
        """
        Get status of all registered monitors.
        
        Returns:
            Dictionary of monitor names and their status
        """
        return {
            name: {
                "running": monitor.is_running,
                "interval": monitor.interval,
                "last_update": monitor.last_update.isoformat() if monitor.last_update else None
            }
            for name, monitor in self.monitors.items()
        }

# Create a global instance of the monitoring manager
# monitoring_manager = MonitoringManager()

class BLEDeviceMonitor(Monitor[Dict[str, Dict[str, Any]]]):
    """Monitors the status of connected BLE devices."""
    
    def __init__(self, ble_manager: BLEManager, interval: float = 5.0):
        super().__init__(name="ble_device_monitor", interval=interval)
        self.ble_manager = ble_manager
        self.previous_state: Dict[str, Dict[str, Any]] = {}

    async def get_state(self) -> Dict[str, Dict[str, Any]]:
        """Get the current state of the BLE device."""
        devices = {}
        if self.ble_manager.device and self.ble_manager.client and self.ble_manager.client.is_connected:
            devices[self.ble_manager.device] = {
                "id": self.ble_manager.device,
                "type": "ble_device",
                "status": DeviceStatus.CONNECTED,
                "last_seen": datetime.now()
            }
        return devices

    async def process_update(self, current_state: Dict[str, Dict[str, Any]]) -> None:
        """Process changes in BLE device status."""
        # Check for new or changed devices
        for device_id, device_info in current_state.items():
            if device_id not in self.previous_state:
                # New device connected
                await self.broadcast_update(
                    "device.status",
                    device_id=device_id,
                    status=DeviceStatus.CONNECTED,
                    **device_info
                )
                logger.info(f"BLE device connected: {device_id}")
            elif device_info.get('status') != self.previous_state[device_id].get('status'):
                # Status changed
                await self.broadcast_update(
                    "device.status",
                    device_id=device_id,
                    status=device_info.get('status'),
                    **device_info
                )
                logger.info(f"BLE device status changed: {device_id} -> {device_info.get('status')}")

        # Check for disconnected devices
        for device_id in list(self.previous_state.keys()):
            if device_id not in current_state:
                # Device disconnected
                await self.broadcast_update(
                    "device.status",
                    device_id=device_id,
                    status=DeviceStatus.DISCONNECTED,
                    **{"id": device_id, "type": "ble_device"}
                )
                logger.info(f"BLE device disconnected: {device_id}")

        # Update previous state
        self.previous_state = current_state.copy()