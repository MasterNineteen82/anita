import asyncio
import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Set, Optional, Any, TypeVar, Generic

from fastapi import FastAPI
from backend.ws.manager import manager
from backend.ws.events import create_event, DeviceStatus
from backend.logging.logging_config import setup_logging
from backend.modules.ble_manager import BLEManager  # Import for BLEDeviceMonitor

# Set up logging
logger = setup_logging()

T = TypeVar('T')  # Type for the monitor data

class Monitor(ABC, Generic[T]):
    """Abstract base class for all monitoring tasks."""
    
    def __init__(self, name: str, interval: float = 1.0):
        self.name = name
        self.interval = interval
        self.running = False
        self.task: Optional[asyncio.Task] = None
        self.last_update: Optional[datetime] = None
        self.room_name: Optional[str] = None
        
    async def start(self, room_name: Optional[str] = None) -> None:
        if self.running:
            logger.warning(f"Monitor {self.name} is already running")
            return
        self.room_name = room_name
        self.running = True
        self.task = asyncio.create_task(self._monitoring_loop())
        logger.info(f"Started monitor: {self.name}")
        
    async def stop(self) -> None:
        if not self.running:
            return
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
            self.task = None
        logger.info(f"Stopped monitor: {self.name}")
        
    async def _monitoring_loop(self) -> None:
        try:
            while self.running:
                start_time = time.time()
                try:
                    data = await self.get_state()
                    await self.process_update(data)
                    self.last_update = datetime.now()
                except Exception as e:
                    logger.error(f"Error in monitor {self.name}: {str(e)}", exc_info=True)
                elapsed = time.time() - start_time
                sleep_time = max(0.1, self.interval - elapsed)
                await asyncio.sleep(sleep_time)
        except asyncio.CancelledError:
            logger.info(f"Monitoring task {self.name} cancelled")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in monitor {self.name}: {str(e)}", exc_info=True)
    
    @abstractmethod
    async def get_state(self) -> T:
        pass
    
    @abstractmethod
    async def process_update(self, data: T) -> None:
        pass

    async def broadcast_update(self, event_type: str, **kwargs) -> None:
        clean_kwargs = kwargs.copy()
        event = create_event(event_type, **clean_kwargs)
        if self.room_name:
            await manager.broadcast_to_room(self.room_name, event)
        else:
            await manager.broadcast_message(event)

class DeviceMonitor(Monitor[Dict[str, Dict[str, Any]]]):
    def __init__(self, interval: float = 5.0):
        super().__init__(name="device_monitor", interval=interval)
        self.previous_state: Dict[str, Dict[str, Any]] = {}
        self.device_repositories = []
        
    def register_device_repository(self, repository: Any) -> None:
        self.device_repositories.append(repository)
        
    async def get_state(self) -> Dict[str, Dict[str, Any]]:
        devices = {}
        for repo in self.device_repositories:
            try:
                repo_devices = await repo.get_all_devices()
                for device in repo_devices:
                    device_id = getattr(device, "id", None) or getattr(device, "device_id", None)
                    if device_id:
                        devices[device_id] = {
                            "id": device_id,
                            "type": repo.__class__.__name__,
                            "status": getattr(device, "status", DeviceStatus.CONNECTED),
                            "last_seen": getattr(device, "last_seen", datetime.now()),
                            "data": device.__dict__
                        }
            except Exception as e:
                logger.error(f"Error getting devices from {repo.__class__.__name__}: {str(e)}")
        return devices
    
    async def process_update(self, current_state: Dict[str, Dict[str, Any]]) -> None:
        for device_id, device_info in current_state.items():
            if device_id not in self.previous_state:
                await self.broadcast_update("device.status", device_id=device_id, status=DeviceStatus.CONNECTED, **device_info)
                logger.info(f"New device connected: {device_id}")
            elif device_info.get('status') != self.previous_state[device_id].get('status'):
                await self.broadcast_update("device.status", device_id=device_id, status=device_info.get('status'), **device_info)
                logger.info(f"Device status changed: {device_id} -> {device_info.get('status')}")
        for device_id in list(self.previous_state.keys()):
            if device_id not in current_state:
                await self.broadcast_update(
                    "device.status",
                    device_id=device_id,
                    status=DeviceStatus.DISCONNECTED,
                    **{"id": device_id, "type": self.previous_state[device_id].get("type", "unknown")}
                )
                logger.info(f"Device disconnected: {device_id}")
        self.previous_state = current_state.copy()

class UWBPositionMonitor(Monitor[Dict[str, Dict[str, Any]]]):
    def __init__(self, uwb_system, uwb_repository, interval: float = 0.5):
        super().__init__(name="uwb_position_monitor", interval=interval)
        self.uwb_system = uwb_system
        self.uwb_repository = uwb_repository
        self.tracked_devices: Set[str] = set()
        self.previous_positions: Dict[str, Dict[str, float]] = {}
        self.position_threshold = 0.1
        
    def track_devices(self, device_ids: List[str]) -> None:
        self.tracked_devices = set(device_ids)
        
    async def get_state(self) -> Dict[str, Dict[str, Any]]:
        if not self.tracked_devices:
            return {}
        positions = {}
        try:
            device_positions = await self.uwb_system.get_device_positions(list(self.tracked_devices))
            for device_id, position in device_positions.items():
                positions[device_id] = {
                    "x": position.get("x", 0),
                    "y": position.get("y", 0),
                    "z": position.get("z", 0),
                    "timestamp": datetime.now()
                }
                await self.uwb_repository.update_device_location(device_id, {"x": position.get("x", 0), "y": position.get("y", 0), "z": position.get("z", 0)})
        except Exception as e:
            logger.error(f"Error getting UWB positions: {str(e)}")
        return positions
    
    async def process_update(self, positions: Dict[str, Dict[str, Any]]) -> None:
        if not positions:
            return
        position_updates = {}
        history_updates = []
        for device_id, position in positions.items():
            if self._position_changed(device_id, position):
                position_updates[device_id] = {"x": position.get("x", 0), "y": position.get("y", 0), "z": position.get("z", 0)}
                history_updates.append({"device_id": device_id, "position": position})
                self.previous_positions[device_id] = position.copy()
        if position_updates:
            await self.broadcast_update("uwb.position_update", positions=position_updates, timestamp=datetime.now())
        if history_updates:
            try:
                for update in history_updates:
                    await self.uwb_repository.add_location_history(update["device_id"], update["position"])
            except Exception as e:
                logger.error(f"Error storing position history: {str(e)}")
    
    def _position_changed(self, device_id: str, position: Dict[str, Any]) -> bool:
        if device_id not in self.previous_positions:
            return True
        prev = self.previous_positions[device_id]
        dx = position.get("x", 0) - prev.get("x", 0)
        dy = position.get("y", 0) - prev.get("y", 0)
        dz = position.get("z", 0) - prev.get("z", 0)
        distance = (dx**2 + dy**2 + dz**2)**0.5
        return distance >= self.position_threshold

class SystemHeartbeatMonitor(Monitor[Dict[str, Any]]):
    def __init__(self, interval: float = 30.0):
        super().__init__(name="system_heartbeat", interval=interval)
        self.start_time = time.monotonic()
    
    async def get_state(self) -> Dict[str, Any]:
        uptime = time.monotonic() - self.start_time
        return {
            "server_time": datetime.now(),
            "uptime_seconds": uptime,
            "client_count": len(manager.active_clients),
            "room_count": len(manager.rooms)
        }
    
    async def process_update(self, state: Dict[str, Any]) -> None:
        await self.broadcast_update(
            "system.heartbeat",
            server_time=state["server_time"].isoformat(),
            uptime_seconds=state["uptime_seconds"]
        )
        logger.debug(f"Heartbeat: {state['client_count']} clients, {state['room_count']} rooms, uptime: {state['uptime_seconds']:.1f}s")

class HardwareMonitor(Monitor[Dict[str, Dict[str, Any]]]):
    def __init__(self, interval: float = 5.0):
        super().__init__(name="hardware_monitor", interval=interval)
        self.previous_states: Dict[str, Dict[str, Any]] = {}
    
    async def get_state(self) -> Dict[str, Dict[str, Any]]:
        return {
            "reader_01": {"type": "card_reader", "status": "ready", "last_seen": datetime.now().isoformat()},
            "uwb_node_01": {"type": "uwb_anchor", "status": "connected", "last_seen": datetime.now().isoformat(), "battery": 87},
            "uwb_node_02": {"type": "uwb_anchor", "status": "connected", "last_seen": datetime.now().isoformat(), "battery": 92},
            "bio_scanner_01": {"type": "fingerprint_reader", "status": "standby", "last_seen": datetime.now().isoformat()}
        }
    
    async def process_update(self, current_states: Dict[str, Dict[str, Any]]) -> None:
        for device_id, device_info in current_states.items():
            if device_id not in self.previous_states or self.previous_states[device_id].get("status") != device_info.get("status"):
                status = device_info.get("status")
                device_info_copy = device_info.copy()
                if "status" in device_info_copy:
                    del device_info_copy["status"]
                await self.broadcast_update("device.status", device_id=device_id, status=status, **device_info_copy)
                logger.info(f"Device {device_id} status changed to {status}")
        for device_id in list(self.previous_states.keys()):
            if device_id not in current_states:
                previous_info = self.previous_states[device_id].copy()
                device_type = previous_info.get("type", "unknown")
                if "status" in previous_info:
                    del previous_info["status"]
                await self.broadcast_update("device.status", device_id=device_id, status="disconnected", type=device_type, **previous_info)
                logger.info(f"Device {device_id} disconnected")
        self.previous_states = current_states.copy()

class BLEDeviceMonitor(Monitor[List[Dict[str, Any]]]):
    """Monitors BLE devices in real-time."""
    
    def __init__(self, ble_service: BLEManager, interval: float = 5.0):
        super().__init__(name="ble_device_monitor", interval=interval)
        self.ble_service = ble_service
        self.tracked_devices: Set[str] = set()
    
    def track_devices(self, device_addresses: Set[str]):
        """Set the BLE devices to monitor."""
        self.tracked_devices = device_addresses
        logger.info(f"Tracking BLE devices: {self.tracked_devices}")
    
    async def get_state(self) -> List[Dict[str, Any]]:
        """Scan for BLE devices."""
        try:
            devices = await self.ble_service.scan_devices(scan_time=3, active=True)
            return [device for device in devices if not self.tracked_devices or device["address"] in self.tracked_devices]
        except Exception as e:
            logger.error(f"Error scanning BLE devices: {str(e)}", exc_info=True)
            return []
    
    async def process_update(self, devices: List[Dict[str, Any]]) -> None:
        """Broadcast updates for detected BLE devices."""
        for device in devices:
            await self.broadcast_update(
                "ble.device",
                address=device["address"],
                name=device["name"],
                rssi=device["rssi"],
                manufacturer_data=device.get("manufacturer_data", {}),
                services=device.get("service_uuids", [])
            )
            logger.debug(f"BLE device update: {device['address']} - {device['name']}")

class MonitoringManager:
    def __init__(self):
        self.monitors: Dict[str, Monitor] = {}
        
    def register_monitor(self, monitor: Monitor) -> None:
        self.monitors[monitor.name] = monitor
        
    async def start_monitor(self, name: str, room_name: Optional[str] = None) -> bool:
        if name not in self.monitors:
            logger.error(f"Monitor {name} not found")
            return False
        await self.monitors[name].start(room_name)
        return True
        
    async def stop_monitor(self, name: str) -> bool:
        if name not in self.monitors:
            logger.error(f"Monitor {name} not found")
            return False
        await self.monitors[name].stop()
        return True
        
    async def start_all(self) -> None:
        for name, monitor in self.monitors.items():
            await monitor.start()
            
    async def stop_all(self) -> None:
        for name, monitor in self.monitors.items():
            await monitor.stop()
            
    def get_monitor(self, name: str) -> Optional[Monitor]:
        return self.monitors.get(name)
    
    def get_all_monitors(self) -> Dict[str, Monitor]:
        return self.monitors.copy()
    
    def get_running_monitors(self) -> Dict[str, Monitor]:
        return {name: monitor for name, monitor in self.monitors.items() if monitor.running}

# Global instance
monitoring_manager = MonitoringManager()

# Initialize monitors
device_monitor = DeviceMonitor()
system_heartbeat = SystemHeartbeatMonitor()
hardware_monitor = HardwareMonitor()
ble_service = BLEManager(logger=logger)
ble_monitor = BLEDeviceMonitor(ble_service)

# Register monitors
monitoring_manager.register_monitor(device_monitor)
monitoring_manager.register_monitor(system_heartbeat)
monitoring_manager.register_monitor(hardware_monitor)
monitoring_manager.register_monitor(ble_monitor)

def setup_monitoring(app: FastAPI):
    @app.on_event("startup")
    async def startup_monitoring():
        logger.info("Starting monitoring system")
        await monitoring_manager.start_all()
    
    @app.on_event("shutdown")
    async def shutdown_monitoring():
        logger.info("Shutting down monitoring system")
        await monitoring_manager.stop_all()
    
    return monitoring_manager

if __name__ == "__main__":
    monitor = Monitor("example_monitor")
    asyncio.run(monitor.start())