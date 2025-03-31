"""
Re-export of SystemMonitor from utils module.
This provides backward compatibility for code expecting it in the core package.
"""

from backend.modules.ble.utils.system_monitor import SystemMonitor, get_system_monitor

# Re-export everything
__all__ = ['SystemMonitor', 'get_system_monitor']