import asyncio
import logging
from backend.domain.services.ble_service import BleService
from backend.infrastructure.repositories.ble_repository import BleRepository

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ble_test")

async def test_ble_service():
    """Test the BLE service layer functionality."""
    logger.info("Starting BLE service tests")
    
    # Create dependencies
    repo = BleRepository(logger=logger)
    service = BleService(repository=repo, logger=logger)
    
    # Test 1: Scan for devices
    logger.info("Test 1: Scanning for devices")
    devices = await service.scan_devices(timeout=5)
    logger.info(f"Found {len(devices)} devices:")
    for device in devices:
        logger.info(f"- {device['name']} ({device['id']})")
    
    # Test 2: Connect to a device
    if devices:
        device_id = devices[0]["id"]
        logger.info(f"Test 2: Connecting to device {device_id}")
        success = await service.connect_device(device_id)
        logger.info(f"Connection {'successful' if success else 'failed'}")
        
        # Test 3: Get device info
        if success:
            logger.info(f"Test 3: Getting device info")
            info = await repo.get_device_info(device_id)
            logger.info(f"Device info: {info}")
            
            # Test 4: Disconnect from device
            logger.info(f"Test 4: Disconnecting from device")
            disconnect_success = await service.disconnect_device(device_id)
            logger.info(f"Disconnection {'successful' if disconnect_success else 'failed'}")
    else:
        logger.warning("No devices found, skipping connection tests")
    
    logger.info("BLE service tests completed")

if __name__ == "__main__":
    asyncio.run(test_ble_service())