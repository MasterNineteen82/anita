import asyncio
import logging
import os
import time
import importlib
import sys

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s',
                   handlers=[
                       logging.FileHandler(f"migration_test_{time.strftime('%Y%m%d_%H%M%S')}.log"),
                       logging.StreamHandler()
                   ])
logger = logging.getLogger("test_runner")

async def run_all_tests():
    """Run all BLE migration tests in sequence."""
    logger.info("==== STARTING BLE MIGRATION TESTS ====")
    
    # Ensure the server is running before testing API
    logger.info("Before running API and WebSocket tests, make sure your FastAPI server is running")
    input("Press Enter to continue with tests...")
    
    test_modules = [
        "test_ble_migration",  # Service layer tests
        "test_ble_api",        # API endpoint tests
        "test_ble_websocket"   # WebSocket tests
    ]
    
    for module_name in test_modules:
        try:
            logger.info(f"\n==== RUNNING TEST MODULE: {module_name} ====")
            
            # Dynamic import and run
            module = importlib.import_module(module_name)
            # Look for the main async function
            main_fn_name = f"test_{module_name.split('_', 1)[1]}"
            
            if hasattr(module, main_fn_name):
                await getattr(module, main_fn_name)()
            else:
                # Fallback to any function with "test" in its name
                test_fn = next((fn for fn_name, fn in module.__dict__.items() 
                              if fn_name.startswith("test_") and callable(fn)), None)
                if test_fn:
                    await test_fn()
                else:
                    logger.error(f"No test function found in {module_name}")
            
            logger.info(f"==== COMPLETED TEST MODULE: {module_name} ====\n")
            
            # Pause between tests
            await asyncio.sleep(1)
            
        except Exception as e:
            logger.error(f"Error running {module_name}: {str(e)}", exc_info=True)
    
    logger.info("==== ALL BLE MIGRATION TESTS COMPLETED ====")

if __name__ == "__main__":
    asyncio.run(run_all_tests())