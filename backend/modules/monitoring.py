# backend/modules/monitoring.py
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any
from .ble_manager import BLEManager
from backend.ws.manager import manager
from backend.ws.events import create_event, DeviceStatus
from .monitors import Monitor  # Updated import

logger = logging.getLogger(__name__)

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