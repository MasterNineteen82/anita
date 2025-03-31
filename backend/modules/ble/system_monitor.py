"""
Re-export of SystemMonitor for backward compatibility.
"""

from backend.modules.ble.utils.system_monitor import SystemMonitor, get_system_monitor

__all__ = ['SystemMonitor', 'get_system_monitor']