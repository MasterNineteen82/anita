import pytest
import os
import sys
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))


@pytest.fixture(scope="session")
def driver():
    """
    Create and return a WebDriver instance for testing.
    """
    # Set up Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in headless mode (no GUI)
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")  # Set window size

    # Initialize Chrome driver with automatic driver management
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=chrome_options
    )
    
    # Set implicit wait time
    driver.implicitly_wait(10)
    
    yield driver
    
    # Teardown - close the browser
    driver.quit()


@pytest.fixture(scope="function")
def ble_dashboard(driver):
    """
    Navigate to the BLE dashboard page before each test.
    """
    # Replace with the actual URL of your BLE dashboard
    driver.get("http://localhost:5000/ble_dashboard")
    
    # Wait for the page to load
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    
    # Wait for the dashboard container to be visible
    WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.CLASS_NAME, "ble-container"))
    )
    
    return driver
