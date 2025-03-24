import asyncio
import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Set, Optional, Any, Callable, Awaitable, TypeVar, Generic

from fastapi import FastAPI
from pydantic import BaseModel

from backend.ws.manager import manager  # Updated
from backend.ws.events import create_event, DeviceStatus  # Updated

logger = logging.getLogger(__name__)

T = TypeVar('T')  # Type for the monitor data

class Monitor(ABC, Generic[T]):
    """Abstract base class for all monitoring tasks."""
    
    def __init__(self, name: str, interval: float = 1.0):
        self.name = name
        self.interval = interval
        self.running = False
        self.task: Optional[asyncio.Task] = None
        self.last_update: Optional[datetime] = None
        self.room_name: Optional[str] = None  # Room to broadcast updates to
        
    async def start(self, room_name: Optional[str] = None) -> None:
        """Start the monitoring task."""
        if self.running:
            logger.warning(f"Monitor {self.name} is already running")
            return
            
        self.room_name = room_name
        self.running = True
        self.task = asyncio.create_task(self._monitoring_loop())
        logger.info(f"Started monitor: {self.name}")
        
    async def stop(self) -> None:
        """Stop the monitoring task."""
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
        """Main monitoring loop."""
        try:
            while self.running:
                start_time = time.time()
                
                try:
                    # Get updated state
                    data = await self.get_state()
                    
                    # Process state changes and send updates
                    await self.process_update(data)
                    
                    # Update timestamp
                    self.last_update = datetime.now()
                except Exception as e:
                    logger.error(f"Error in monitor {self.name}: {str(e)}")
                
                # Calculate sleep time to maintain interval
                elapsed = time.time() - start_time
                sleep_time = max(0.1, self.interval - elapsed)
                await asyncio.sleep(sleep_time)
        except asyncio.CancelledError:
            logger.info(f"Monitoring task {self.name} cancelled")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in monitor {self.name}: {str(e)}")
    
    @abstractmethod
    async def get_state(self) -> T:
        """Get the current state to monitor. Must be implemented by subclasses."""
        pass
    
    @abstractmethod
    async def process_update(self, data: T) -> None:
        """Process state updates and send notifications. Must be implemented by subclasses."""
        pass

    async def broadcast_update(self, event_type: str, **kwargs) -> None:
        """Broadcast an update to the monitor's room."""
        event = create_event(event_type, **kwargs)
        
        if self.room_name:
            await manager.broadcast_to_room(self.room_name, event)
        else:
            await manager.broadcast_message(event)

class DeviceMonitor(Monitor[Dict[str, Dict[str, Any]]]):
    """Monitors the status of connected devices."""
    
    def __init__(self, interval: float = 5.0):
        super().__init__(name="device_monitor", interval=interval)
        self.previous_state: Dict[str, Dict[str, Any]] = {}
        self.device_repositories = []  # List of repositories to check for devices
        
    def register_device_repository(self, repository: Any) -> None:
        """Register a device repository to monitor."""
        self.device_repositories.append(repository)
        
    async def get_state(self) -> Dict[str, Dict[str, Any]]:
        """Get the current state of all devices."""
        devices = {}
        
        # Collect devices from all repositories
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
        """Process changes in device status."""
        # Check for new devices
        for device_id, device_info in current_state.items():
            if device_id not in self.previous_state:
                # New device connected
                await self.broadcast_update(
                    "device.status",
                    device_id=device_id,
                    status=DeviceStatus.CONNECTED,
                    **device_info
                )
                logger.info(f"New device connected: {device_id}")
            elif device_info.get('status') != self.previous_state[device_id].get('status'):
                # Status changed
                await self.broadcast_update(
                    "device.status",
                    device_id=device_id,
                    status=device_info.get('status'),
                    **device_info
                )
                logger.info(f"Device status changed: {device_id} -> {device_info.get('status')}")
        
        # Check for disconnected devices
        for device_id in list(self.previous_state.keys()):
            if device_id not in current_state:
                # Device disconnected
                await self.broadcast_update(
                    "device.status",
                    device_id=device_id,
                    status=DeviceStatus.DISCONNECTED,
                    **{"id": device_id, "type": self.previous_state[device_id].get("type", "unknown")}
                )
                logger.info(f"Device disconnected: {device_id}")
        
        # Update previous state
        self.previous_state = current_state.copy()

class UWBPositionMonitor(Monitor[Dict[str, Dict[str, Any]]]):
    """Monitors UWB device positions in real-time."""
    
    def __init__(self, uwb_system, uwb_repository, interval: float = 0.5):
        super().__init__(name="uwb_position_monitor", interval=interval)
        self.uwb_system = uwb_system
        self.uwb_repository = uwb_repository
        self.tracked_devices: Set[str] = set()
        self.previous_positions: Dict[str, Dict[str, float]] = {}
        self.position_threshold = 0.1  # Minimum movement to trigger update (meters)
        
    def track_devices(self, device_ids: List[str]) -> None:
        """Set the devices to track."""
        self.tracked_devices = set(device_ids)
        
    async def get_state(self) -> Dict[str, Dict[str, Any]]:
        """Get current positions of tracked devices."""
        if not self.tracked_devices:
            return {}
            
        positions = {}
        try:
            # Get positions from UWB system
            device_positions = await self.uwb_system.get_device_positions(list(self.tracked_devices))
            
            # Format for processing
            for device_id, position in device_positions.items():
                positions[device_id] = {
                    "x": position.get("x", 0),
                    "y": position.get("y", 0),
                    "z": position.get("z", 0),
                    "timestamp": datetime.now()
                }
                
                # Update device in repository
                await self.uwb_repository.update_device_location(
                    device_id,
                    {"x": position.get("x", 0), "y": position.get("y", 0), "z": position.get("z", 0)}
                )
        except Exception as e:
            logger.error(f"Error getting UWB positions: {str(e)}")
            
        return positions
    
    async def process_update(self, positions: Dict[str, Dict[str, Any]]) -> None:
        """Process position updates and send notifications."""
        if not positions:
            return
            
        # Prepare position update event
        position_updates = {}
        history_updates = []
        
        for device_id, position in positions.items():
            # Check if position changed significantly
            if self._position_changed(device_id, position):
                position_updates[device_id] = {
                    "x": position.get("x", 0),
                    "y": position.get("y", 0),
                    "z": position.get("z", 0)
                }
                
                # Store in history
                history_updates.append({
                    "device_id": device_id,
                    "position": position
                })
                
                # Update previous position
                self.previous_positions[device_id] = position.copy()
        
        # Send position updates if any changed
        if position_updates:
            await self.broadcast_update(
                "uwb.position_update",
                positions=position_updates,
                timestamp=datetime.now()
            )
            
        # Store history updates in repository
        if history_updates:
            try:
                for update in history_updates:
                    await self.uwb_repository.add_location_history(
                        update["device_id"],
                        update["position"]
                    )
            except Exception as e:
                logger.error(f"Error storing position history: {str(e)}")
    
    def _position_changed(self, device_id: str, position: Dict[str, Any]) -> bool:
        """Check if position changed significantly."""
        if device_id not in self.previous_positions:
            return True
            
        prev = self.previous_positions[device_id]
        
        # Calculate distance between points
        dx = position.get("x", 0) - prev.get("x", 0)
        dy = position.get("y", 0) - prev.get("y", 0)
        dz = position.get("z", 0) - prev.get("z", 0)
        
        distance = (dx**2 + dy**2 + dz**2)**0.5
        
        return distance >= self.position_threshold

class MonitoringManager:
    """Manages all monitoring tasks."""
    
    def __init__(self):
        self.monitors: Dict[str, Monitor] = {}
        
    def register_monitor(self, monitor: Monitor) -> None:
        """Register a monitor."""
        self.monitors[monitor.name] = monitor
        
    async def start_monitor(self, name: str, room_name: Optional[str] = None) -> bool:
        """Start a specific monitor."""
        if name not in self.monitors:
            logger.error(f"Monitor {name} not found")
            return False
            
        await self.monitors[name].start(room_name)
        return True
        
    async def stop_monitor(self, name: str) -> bool:
        """Stop a specific monitor."""
        if name not in self.monitors:
            logger.error(f"Monitor {name} not found")
            return False
            
        await self.monitors[name].stop()
        return True
        
    async def start_all(self) -> None:
        """Start all registered monitors."""
        for name, monitor in self.monitors.items():
            await monitor.start()
            
    async def stop_all(self) -> None:
        """Stop all registered monitors."""
        for name, monitor in self.monitors.items():
            await monitor.stop()
            
    def get_monitor(self, name: str) -> Optional[Monitor]:
        """Get a specific monitor by name."""
        return self.monitors.get(name)
    
    def get_all_monitors(self) -> Dict[str, Monitor]:
        """Get all registered monitors."""
        return self.monitors.copy()
    
    def get_running_monitors(self) -> Dict[str, Monitor]:
        """Get all currently running monitors."""
        return {name: monitor for name, monitor in self.monitors.items() if monitor.running}

# Create system heartbeat monitor
class SystemHeartbeatMonitor(Monitor[Dict[str, Any]]):
    """Monitor that sends periodic heartbeats to clients."""
    
    def __init__(self, interval: float = 30.0):
        super().__init__(name="system_heartbeat", interval=interval)
        self.start_time = time.monotonic()
    
    async def get_state(self) -> Dict[str, Any]:
        """Get system state."""
        uptime = time.monotonic() - self.start_time
        return {
            "server_time": datetime.now(),
            "uptime_seconds": uptime,
            "client_count": len(manager.active_clients),
            "room_count": len(manager.rooms)
        }
    
    async def process_update(self, state: Dict[str, Any]) -> None:
        """Send heartbeat to clients."""
        await self.broadcast_update(
            "system.heartbeat",
            server_time=state["server_time"].isoformat(),
            uptime_seconds=state["uptime_seconds"]
        )
        
        # Log simple heartbeat status
        logger.debug(f"Heartbeat: {state['client_count']} clients, {state['room_count']} rooms, uptime: {state['uptime_seconds']:.1f}s")

class HardwareMonitor(Monitor[Dict[str, Dict[str, Any]]]):
    """Monitor hardware device states."""
    
    def __init__(self, interval: float = 5.0):
        super().__init__(name="hardware_monitor", interval=interval)
        self.previous_states: Dict[str, Dict[str, Any]] = {}
    
    async def get_state(self) -> Dict[str, Dict[str, Any]]:
        """Get current hardware device states."""
        # In a real implementation, this would connect to hardware interfaces
        # For now, we'll use a simulated implementation
        return {
            "reader_01": {
                "type": "card_reader",
                "status": "ready",
                "last_seen": datetime.now().isoformat()
            },
            "uwb_node_01": {
                "type": "uwb_anchor",
                "status": "connected",
                "last_seen": datetime.now().isoformat(),
                "battery": 87
            },
            "uwb_node_02": {
                "type": "uwb_anchor",
                "status": "connected",
                "last_seen": datetime.now().isoformat(),
                "battery": 92
            },
            "bio_scanner_01": {
                "type": "fingerprint_reader",
                "status": "standby",
                "last_seen": datetime.now().isoformat()
            }
        }
    
    async def process_update(self, current_states: Dict[str, Dict[str, Any]]) -> None:
        """Process hardware state changes."""
        # Check for new or changed devices
        for device_id, device_info in current_states.items():
            if device_id not in self.previous_states or \
               self.previous_states[device_id].get("status") != device_info.get("status"):
                
                # Broadcast device status change
                await self.broadcast_update(
                    "device.status",
                    device_id=device_id,
                    status=device_info.get("status"),
                    **device_info
                )
                
                logger.info(f"Device {device_id} status changed to {device_info.get('status')}")
        
        # Check for disconnected devices
        for device_id in list(self.previous_states.keys()):
            if device_id not in current_states:
                # Device was disconnected
                await self.broadcast_update(
                    "device.status",
                    device_id=device_id,
                    status="disconnected",
                    type=self.previous_states[device_id].get("type", "unknown")
                )
                
                logger.info(f"Device {device_id} disconnected")
        
        # Update previous states
        self.previous_states = current_states.copy()

# Create global instance
monitoring_manager = MonitoringManager()

# Initialize with common monitors
device_monitor = DeviceMonitor()
system_heartbeat = SystemHeartbeatMonitor()
hardware_monitor = HardwareMonitor()

# Register monitors
monitoring_manager.register_monitor(device_monitor)
monitoring_manager.register_monitor(system_heartbeat)
monitoring_manager.register_monitor(hardware_monitor)

# Helper function to set up monitoring with FastAPI
def setup_monitoring(app: FastAPI):
    """Set up the monitoring system with FastAPI application."""
    # Add startup and shutdown handlers
    @app.on_event("startup")
    async def startup_monitoring():
        logger.info("Starting monitoring system")
        await monitoring_manager.start_all()
    
    @app.on_event("shutdown")
    async def shutdown_monitoring():
        logger.info("Shutting down monitoring system")
        await monitoring_manager.stop_all()
    
    return monitoring_manager