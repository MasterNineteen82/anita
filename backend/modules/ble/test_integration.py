"""Integration test for the refactored BLE module."""

import asyncio
import logging
import sys
import os
import time

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger("BLE-Integration-Test")

# Import the BLE components
from backend.modules.ble.ble_service import BleService
from backend.modules.ble.ble_metrics import BleMetricsCollector, SystemMonitor
from backend.modules.ble.managers.adapter_manager import BleAdapterManager
from backend.modules.ble.managers.device_manager import BleDeviceManager
from backend.modules.ble.managers.service_manager import BleServiceManager
from backend.modules.ble.managers.notification_manager import BleNotificationManager

async def test_adapter_manager():
    """Test the adapter manager."""
    logger.info("=== Testing Adapter Manager ===")
    
    metrics = BleMetricsCollector()
    adapter_manager = BleAdapterManager(metrics_collector=metrics, logger=logger)
    
    # Get adapters
    logger.info("Getting adapters...")
    adapters = await adapter_manager.get_adapters()
    logger.info(f"Found {len(adapters)} adapters")
    
    for i, adapter in enumerate(adapters, 1):
        logger.info(f"Adapter {i}: {adapter.get('name')} ({adapter.get('address')})")
    
    # Try to select the first adapter if any
    if adapters:
        adapter_id = adapters[0].get('device_id') or adapters[0].get('address')
        logger.info(f"Selecting adapter: {adapter_id}")
        result = await adapter_manager.select_adapter(adapter_id)
        logger.info(f"Selection result: {result.get('status')} - {result.get('message')}")
    
    return adapters

async def test_device_manager(adapters):
    """Test the device manager."""
    logger.info("\n=== Testing Device Manager ===")
    
    if not adapters:
        logger.warning("No adapters available, skipping device tests")
        return
    
    metrics = BleMetricsCollector()
    device_manager = BleDeviceManager(metrics_collector=metrics, logger=logger)
    
    # Scan for devices
    logger.info("Scanning for devices...")
    try:
        scan_results = await device_manager.scan_devices(scan_time=5.0)
        logger.info(f"Found {len(scan_results)} devices")
        
        for i, device in enumerate(scan_results, 1):
            if isinstance(device, dict):
                logger.info(f"Device {i}: {device.get('name')} ({device.get('address')})")
            else:
                logger.info(f"Device {i}: {getattr(device, 'name', 'Unknown')} ({getattr(device, 'address', 'Unknown')})")
        
        return scan_results
    except Exception as e:
        logger.error(f"Error scanning for devices: {e}")
        return []

async def test_service_manager():
    """Test the service manager."""
    logger.info("\n=== Testing Service Manager ===")
    
    service_manager = BleServiceManager(logger=logger)
    
    # Test service description lookup
    service_uuids = ["1800", "1801", "180f", "180a"]
    for uuid in service_uuids:
        desc = service_manager._get_service_description(uuid)
        logger.info(f"Service {uuid} description: {desc}")
    
    # Test characteristic description lookup
    char_uuids = ["2a00", "2a01", "2a19", "2a29"]
    for uuid in char_uuids:
        desc = service_manager._get_characteristic_description(uuid)
        logger.info(f"Characteristic {uuid} description: {desc}")

async def test_notification_manager():
    """Test the notification manager."""
    logger.info("\n=== Testing Notification Manager ===")
    
    notification_manager = BleNotificationManager(logger=logger)
    
    # Register a test callback
    test_char = "2a19"  # Battery level
    logger.info(f"Adding callback for {test_char}")
    
    def test_callback(char_uuid, data):
        logger.info(f"Notification from {char_uuid}: {data.hex() if isinstance(data, bytes) else data}")
    
    callback_id = notification_manager.add_callback(test_char, test_callback)
    logger.info(f"Callback ID: {callback_id}")
    
    # Simulate a notification
    logger.info("Simulating a notification")
    notification_manager.process_notification(test_char, bytes([75]))  # 75% battery
    
    # Get active notifications
    notification_manager.mark_notification_active(test_char)
    active = notification_manager.get_active_notifications()
    logger.info(f"Active notifications: {active}")
    
    # Get history
    history = notification_manager.get_notification_history(test_char)
    logger.info(f"Notification history: {history}")
    
    # Remove callback
    removed = notification_manager.remove_callback(test_char, callback_id)
    logger.info(f"Callback removed: {removed}")

async def test_metrics_and_system_monitor():
    """Test the metrics collector and system monitor."""
    logger.info("\n=== Testing Metrics and System Monitor ===")
    
    metrics = BleMetricsCollector()
    
    # Record some test operations
    op_id = metrics.record_scan_start()
    logger.info(f"Started scan operation {op_id}")
    
    # Simulate some work
    await asyncio.sleep(1)
    
    metrics.record_scan_complete(op_id, True, 10)
    logger.info("Recorded scan completion")
    
    # Get operation metrics
    op_metrics = metrics.get_operation_metrics()
    logger.info(f"Operation metrics: {op_metrics}")
    
    # Test system monitor
    monitor = SystemMonitor()
    system_info = monitor.get_system_info()
    logger.info(f"System info: Platform: {system_info.get('platform')}, CPU: {system_info.get('processor')}")
    
    system_metrics = monitor.get_system_metrics()
    logger.info(f"System metrics: CPU: {system_metrics.get('cpu', {}).get('percent')}%, " +
                f"Memory: {system_metrics.get('memory', {}).get('percent')}%")
    
    # Test Bluetooth health report
    health_report = monitor.get_bluetooth_health_report()
    logger.info(f"Health report status: {health_report.get('status')}")
    if health_report.get('issues'):
        logger.info(f"Health issues: {health_report.get('issues')}")
    if health_report.get('recommendations'):
        logger.info(f"Recommendations: {health_report.get('recommendations')}")

async def main():
    """Run all tests."""
    logger.info("Starting BLE Integration Tests")
    
    try:
        # Test adapter manager
        adapters = await test_adapter_manager()
        
        # Test device manager
        devices = await test_device_manager(adapters)
        
        # Test service manager
        await test_service_manager()
        
        # Test notification manager
        await test_notification_manager()
        
        # Test metrics and system monitor
        await test_metrics_and_system_monitor()
        
        logger.info("\nAll tests completed successfully!")
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(main())