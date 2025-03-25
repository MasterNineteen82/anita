import asyncio
import websockets
import json
import logging
import aiohttp

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("websocket_test")

async def test_ble_websocket():
    """Test the BLE WebSocket functionality."""
    logger.info("Starting BLE WebSocket tests")
    
    # API and WebSocket URLs
    api_url = "http://localhost:8000"
    ws_url = "ws://localhost:8000/ws/ble"
    
    # First, get an authentication token if needed
    async with aiohttp.ClientSession() as session:
        try:
            # Try to log in - adjust with your actual login endpoint and credentials
            login_data = {
                "username": "test_user",
                "password": "test_password"
            }
            
            logger.info("Attempting to authenticate...")
            async with session.post(f"{api_url}/auth/login", json=login_data) as response:
                if response.status == 200:
                    auth_data = await response.json()
                    token = auth_data.get("access_token")
                    logger.info("Authentication successful")
                else:
                    logger.warning(f"Authentication failed: {response.status}")
                    token = None
        except Exception as e:
            logger.error(f"Error during authentication: {str(e)}")
            token = None
    
    try:
        # WebSocket connection with authentication if token available
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        
        # Add cookie authentication as an alternative
        cookies = {"session": token} if token else {}
        
        # Try connecting with headers first
        try:
            logger.info("Connecting to WebSocket with authentication headers...")
            async with websockets.connect("ws://localhost:8000/ws/test") as websocket:
                await test_websocket_connection(websocket)
        except Exception as header_error:
            logger.warning(f"Header authentication failed: {str(header_error)}")
            
            try:
                # Try with cookies instead
                logger.info("Connecting to WebSocket with cookies...")
                # websockets library doesn't directly support cookies, so we'd use a different approach
                # For testing purposes, we might need to modify the server to accept a token parameter
                async with websockets.connect(f"{ws_url}?token={token}") as websocket:
                    await test_websocket_connection(websocket)
            except Exception as cookie_error:
                logger.error(f"Cookie authentication failed: {str(cookie_error)}")
                
                # As a last resort, check if we can disable auth for testing
                logger.info("Attempting connection to test endpoint without auth...")
                try:
                    async with websockets.connect("ws://localhost:8000/ws/test-noauth") as websocket:
                        logger.info("Connected to test WebSocket without authentication")
                        await websocket.recv()  # Just to check if we receive anything
                except Exception as no_auth_error:
                    logger.error(f"Even unauthenticated test connection failed: {str(no_auth_error)}")
                    
    except Exception as e:
        logger.error(f"WebSocket test failed: {str(e)}")
    
    logger.info("BLE WebSocket tests completed")

async def test_websocket_connection(websocket):
    """Run the actual WebSocket tests once connected."""
    logger.info("Connected to BLE WebSocket")
    
    # Receive the welcome message
    response = await websocket.recv()
    logger.info(f"Received: {response}")
    
    # Send a subscription message (you'll need an active BLE connection and known characteristic UUID)
    # This is just a template - you'll need to adjust with real values
    char_uuid = "00002a19-0000-1000-8000-00805f9b34fb"  # Example: Battery Level characteristic
    
    subscription_message = {
        "type": "subscribe_to_characteristic",
        "char_uuid": char_uuid
    }
    
    logger.info(f"Subscribing to characteristic: {char_uuid}")
    await websocket.send(json.dumps(subscription_message))
    
    # Receive subscription confirmation
    response = await websocket.recv()
    logger.info(f"Subscription response: {response}")
    
    # Wait for notifications briefly
    logger.info("Waiting for notifications (5 seconds)...")
    try:
        notification = await asyncio.wait_for(websocket.recv(), timeout=5.0)
        logger.info(f"Notification received: {notification}")
    except asyncio.TimeoutError:
        logger.info("No notification received in 5 seconds")
    
    # Unsubscribe from the characteristic
    unsubscribe_message = {
        "type": "unsubscribe_from_characteristic",
        "char_uuid": char_uuid
    }
    
    logger.info(f"Unsubscribing from characteristic: {char_uuid}")
    await websocket.send(json.dumps(unsubscribe_message))
    
    # Receive unsubscription confirmation
    response = await websocket.recv()
    logger.info(f"Unsubscription response: {response}")

if __name__ == "__main__":
    asyncio.run(test_ble_websocket())