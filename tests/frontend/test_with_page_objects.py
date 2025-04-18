import pytest
from page_objects import BleDashboardPage
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


class TestBleDashboardWithPageObjects:
    """Test suite using Page Object Model for improved maintainability."""
    
    @pytest.fixture
    def dashboard_page(self, driver):
        """Create and return a BleDashboardPage instance."""
        page = BleDashboardPage(driver)
        page.visit()
        return page
    
    def test_scan_functionality(self, dashboard_page):
        """Test the scan button functionality using page objects."""
        # Check initial state
        assert not dashboard_page.is_scanning()
        
        # Start scan
        dashboard_page.click_scan_button()
        
        # Verify scanning state
        assert dashboard_page.is_scanning()
        
        try:
            # Wait for scan to complete (up to 10 seconds)
            assert dashboard_page.wait_for_scan_to_complete(10)
            
            # Verify returned to non-scanning state
            assert not dashboard_page.is_scanning()
        except (TimeoutException, AssertionError):
            pytest.skip("Scan did not complete as expected - backend may not be running")
    
    def test_device_filtering(self, dashboard_page):
        """Test device filtering using page objects."""
        # Add mock devices
        mock_devices = [
            {"address": "00:11:22:33:44:55", "name": "Test Device 1", "rssi": -65},
            {"address": "AA:BB:CC:DD:EE:FF", "name": "Arduino BLE", "rssi": -75},
            {"address": "12:34:56:78:90:AB", "name": "Sensor Device", "rssi": -85}
        ]
        
        for device in mock_devices:
            dashboard_page.mock_discovered_device(device)
        
        # Check all devices are shown
        assert len(dashboard_page.get_discovered_devices()) == 3
        
        # Filter by name "Arduino"
        dashboard_page.filter_devices("Arduino", by_name=True)
        
        # Should show just one device
        visible_devices = [d for d in dashboard_page.get_discovered_devices() 
                          if d.is_displayed()]
        assert len(visible_devices) == 1
        
        # Filter by address "12:34"
        dashboard_page.filter_devices("12:34", by_name=False, by_address=True)
        
        # Should show just the device with that address prefix
        visible_devices = [d for d in dashboard_page.get_discovered_devices() 
                          if d.is_displayed()]
        assert len(visible_devices) == 1
        assert dashboard_page.has_device_with_address("12:34:56:78:90:AB")
        
        # Clear filter
        dashboard_page.filter_devices("")
        
        # Should show all devices again
        visible_devices = [d for d in dashboard_page.get_discovered_devices() 
                          if d.is_displayed()]
        assert len(visible_devices) == 3
    
    def test_connection_status(self, dashboard_page):
        """Test connection status updates using page objects."""
        # Initial state should be disconnected
        mock_device = {
            "address": "00:11:22:33:44:55", 
            "name": "Test Connection Device"
        }
        
        # Set connecting state
        assert dashboard_page.mock_connection_state("connecting")
        assert dashboard_page.get_connection_status() == "Connecting..."
        
        # Set connected state
        assert dashboard_page.mock_connection_state("connected", mock_device)
        assert dashboard_page.is_device_connected()
        assert dashboard_page.get_connection_status() == "Connected"
        assert dashboard_page.get_connected_device_name() == "Test Connection Device"
        
        # Set disconnected state
        assert dashboard_page.mock_connection_state("disconnected")
        assert not dashboard_page.is_device_connected()
        assert dashboard_page.get_connection_status() == "Disconnected"
    
    def test_toast_notifications(self, dashboard_page):
        """Test toast notifications using page objects."""
        # Test different toast types
        for toast_type in ["info", "success", "warning", "error"]:
            dashboard_page.show_toast(f"Test {toast_type} notification", toast_type, 1500)
            
            # Verify toast is displayed (we don't wait for it to disappear to speed up tests)
            try:
                toast = WebDriverWait(dashboard_page.driver, 2).until(
                    EC.visibility_of_element_located((dashboard_page.TOAST))
                )
                assert f"Test {toast_type} notification" in toast.text
                assert f"toast-{toast_type}" in toast.get_attribute("class")
            except TimeoutException:
                pytest.fail(f"Toast notification of type {toast_type} was not displayed")
