import asyncio
import aiohttp
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("api_test")

async def test_ble_api():
    """Test the BLE API endpoints."""
    logger.info("Starting BLE API tests")
    
    # Base URL for API
    base_url = "http://localhost:8000"  # Adjust if your server runs on a different port
    
    async with aiohttp.ClientSession() as session:
        # Test 1: Scan for devices
        logger.info("Test 1: Scanning for BLE devices")
        async with session.get(f"{base_url}/api/ble/scan?scan_time=5") as response:
            if response.status == 200:
                devices = await response.json()
                logger.info(f"Found {len(devices)} devices")
                for device in devices:
                    logger.info(f"- {device['name']} ({device['address']})")
                
                # Test 2: Connect to the first device
                if devices:
                    device_address = devices[0]["address"]
                    logger.info(f"Test 2: Connecting to device {device_address}")
                    
                    async with session.post(f"{base_url}/api/ble/connect/{device_address}") as connect_response:
                        if connect_response.status == 200:
                            logger.info("Connection successful")
                            connection_data = await connect_response.json()
                            logger.info(f"Response: {connection_data}")
                            
                            # Test 3: Get services
                            logger.info("Test 3: Getting services")
                            async with session.get(f"{base_url}/api/ble/services") as services_response:
                                if services_response.status == 200:
                                    services = await services_response.json()
                                    logger.info(f"Found {len(services)} services")
                                    
                                    # Test 4: If services exist, get characteristics for the first one
                                    if services:
                                        service_uuid = services[0]["uuid"]
                                        logger.info(f"Test 4: Getting characteristics for service {service_uuid}")
                                        
                                        async with session.get(f"{base_url}/api/ble/services/{service_uuid}/characteristics") as char_response:
                                            if char_response.status == 200:
                                                chars = await char_response.json()
                                                logger.info(f"Found {len(chars)} characteristics")
                                            else:
                                                logger.error(f"Failed to get characteristics: {char_response.status}")
                                else:
                                    logger.error(f"Failed to get services: {services_response.status}")
                            
                            # Test 5: Disconnect
                            logger.info("Test 5: Disconnecting from device")
                            async with session.post(f"{base_url}/api/ble/disconnect") as disconnect_response:
                                if disconnect_response.status == 200:
                                    logger.info("Disconnection successful")
                                    disconnect_data = await disconnect_response.json()
                                    logger.info(f"Response: {disconnect_data}")
                                else:
                                    logger.error(f"Disconnection failed: {disconnect_response.status}")
                        else:
                            logger.error(f"Connection failed: {connect_response.status}")
                else:
                    logger.warning("No devices found, skipping connection tests")
            else:
                logger.error(f"Scan failed: {response.status}")
    
    logger.info("BLE API tests completed")

if __name__ == "__main__":
    asyncio.run(test_ble_api())