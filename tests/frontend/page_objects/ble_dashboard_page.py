from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


class BleDashboardPage:
    """Page object for the BLE Dashboard page.
    
    This class provides methods to interact with elements on the BLE Dashboard page,
    making tests more maintainable and readable.
    """
    
    # Locators
    SCAN_BUTTON = (By.ID, "scan-btn")
    STOP_SCAN_BUTTON = (By.ID, "stop-scan-btn")
    SCAN_STATUS = (By.ID, "scan-status")
    SCAN_PROGRESS_BAR = (By.ID, "scan-progress-bar")
    DEVICE_FILTER = (By.ID, "device-filter")
    FILTER_BY_NAME = (By.ID, "filter-by-name")
    FILTER_BY_ADDRESS = (By.ID, "filter-by-address")
    FILTER_BY_SIGNAL = (By.ID, "filter-by-signal")
    DISCOVERED_DEVICES_LIST = (By.ID, "discovered-devices-list")
    NO_DEVICES_MESSAGE = (By.ID, "no-device-message")
    DEVICE_COUNT = (By.ID, "device-count")
    
    # Connected Device Card
    DEVICE_INFO_CARD = (By.ID, "ble-device-info-card")
    DEVICE_INFO = (By.ID, "device-info")
    STATUS_INDICATOR = (By.ID, "device-status-indicator")
    STATUS_TEXT = (By.ID, "device-status-text")
    DISCONNECT_BUTTON = (By.ID, "disconnect-btn")
    DEVICE_NAME = (By.ID, "device-name")
    DEVICE_ADDRESS = (By.ID, "device-address")
    DEVICE_RSSI = (By.ID, "device-rssi")
    DEVICE_SERVICES = (By.ID, "device-services")
    
    # Toast Notifications
    TOAST_CONTAINER = (By.CLASS_NAME, "toast-container")
    TOAST = (By.CLASS_NAME, "toast")
    
    def __init__(self, driver):
        self.driver = driver
        
    def visit(self, base_url="http://localhost:5000"):
        """Navigate to the BLE Dashboard page."""
        self.driver.get(f"{base_url}/ble_dashboard")
        self.wait_for_page_to_load()
        return self
    
    def wait_for_page_to_load(self, timeout=10):
        """Wait for the page to fully load."""
        WebDriverWait(self.driver, timeout).until(
            EC.visibility_of_element_located((By.CLASS_NAME, "ble-container"))
        )
        return self
    
    def click_scan_button(self):
        """Click the scan button."""
        self.driver.find_element(*self.SCAN_BUTTON).click()
        return self
    
    def click_stop_scan_button(self):
        """Click the stop scan button."""
        self.driver.find_element(*self.STOP_SCAN_BUTTON).click()
        return self
    
    def is_scanning(self):
        """Check if scanning is in progress."""
        try:
            scan_status = self.driver.find_element(*self.SCAN_STATUS)
            return "hidden" not in scan_status.get_attribute("class")
        except:
            return False
    
    def wait_for_scan_to_complete(self, timeout=10):
        """Wait for the scan to complete."""
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.invisibility_of_element_located(self.SCAN_STATUS)
            )
            return True
        except TimeoutException:
            return False
    
    def filter_devices(self, filter_text, by_name=True, by_address=False):
        """Filter devices by name or address."""
        # Set the filter text
        filter_input = self.driver.find_element(*self.DEVICE_FILTER)
        filter_input.clear()
        filter_input.send_keys(filter_text)
        
        # Select the appropriate filter type
        if by_name:
            self.driver.find_element(*self.FILTER_BY_NAME).click()
        elif by_address:
            self.driver.find_element(*self.FILTER_BY_ADDRESS).click()
        
        return self
    
    def get_device_count(self):
        """Get the current device count from the UI."""
        count_element = self.driver.find_element(*self.DEVICE_COUNT)
        text = count_element.text
        
        # Extract number from text like "Found 5 device(s)" or "Showing 3 of 5 devices"
        import re
        match = re.search(r"(\d+)(?=\s+of\s+(\d+))?", text)
        if match:
            return int(match.group(1))
        return 0
    
    def get_discovered_devices(self):
        """Get list of discovered devices from the UI."""
        devices_list = self.driver.find_element(*self.DISCOVERED_DEVICES_LIST)
        device_elements = devices_list.find_elements(By.CLASS_NAME, "device-item")
        return device_elements
    
    def has_device_with_address(self, address):
        """Check if a device with the given address exists in the list."""
        devices = self.get_discovered_devices()
        for device in devices:
            if device.get_attribute("data-address") == address:
                return True
        return False
    
    def disconnect_device(self):
        """Click the disconnect button."""
        disconnect_btn = self.driver.find_element(*self.DISCONNECT_BUTTON)
        disconnect_btn.click()
        return self
    
    def get_connection_status(self):
        """Get the current connection status from the UI."""
        try:
            status_text = self.driver.find_element(*self.STATUS_TEXT)
            return status_text.text
        except:
            return "Unknown"
    
    def is_device_connected(self):
        """Check if any device is currently connected."""
        try:
            status_indicator = self.driver.find_element(*self.STATUS_INDICATOR)
            return "status-connected" in status_indicator.get_attribute("class")
        except:
            return False
    
    def get_connected_device_name(self):
        """Get the name of the connected device."""
        try:
            name_element = self.driver.find_element(*self.DEVICE_NAME)
            return name_element.text
        except:
            return None
    
    def execute_javascript(self, script):
        """Execute JavaScript code on the page."""
        return self.driver.execute_script(script)
    
    def show_toast(self, message, type="info", duration=3000):
        """Show a toast notification using JavaScript."""
        script = f"""
        if (window.bleDashboard && window.bleDashboard.showToast) {{
            window.bleDashboard.showToast('{message}', '{type}', {duration});
            return true;
        }}
        return false;
        """
        return self.execute_javascript(script)
    
    def mock_discovered_device(self, device_data):
        """Inject a mock discovered device into the UI."""
        import json
        script = f"""
        if (window.bleDashboard && window.bleDashboard.renderDiscoveredDevice) {{
            window.bleDashboard.renderDiscoveredDevice({json.dumps(device_data)});
            return true;
        }}
        return false;
        """
        return self.execute_javascript(script)
    
    def mock_connection_state(self, state, device=None):
        """Set a mock connection state."""
        device_json = "null"
        if device:
            import json
            device_json = json.dumps(device)
            
        script = f"""
        if (window.bleDashboard && window.bleDashboard.updateDeviceConnectionState) {{
            window.bleDashboard.updateDeviceConnectionState('{state}', {device_json});
            return true;
        }}
        return false;
        """
        return self.execute_javascript(script)
    
    def mock_services(self, services_data):
        """Inject mock service data into the UI."""
        import json
        script = f"""
        if (window.bleDashboard && window.bleDashboard.renderDeviceServices) {{
            window.bleDashboard.renderDeviceServices({json.dumps(services_data)});
            return true;
        }}
        return false;
        """
        return self.execute_javascript(script)
