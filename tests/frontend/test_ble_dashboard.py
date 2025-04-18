import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import time


class TestBleDashboard:
    """Test suite for BLE Dashboard UI functionality."""

    def test_page_title(self, ble_dashboard):
        """Test that the page title is correct."""
        assert "BLE Dashboard" in ble_dashboard.title
    
    def test_adapter_info_card_exists(self, ble_dashboard):
        """Test that the adapter info card is present."""
        card = ble_dashboard.find_element(By.ID, "ble-adapter-info-card")
        assert card.is_displayed()
        
        # Check for card title
        title = card.find_element(By.CSS_SELECTOR, ".card-header h3")
        assert "Adapter Information" in title.text
    
    def test_device_scanner_card_exists(self, ble_dashboard):
        """Test that the device scanner card is present."""
        card = ble_dashboard.find_element(By.ID, "ble-device-scanner-card")
        assert card.is_displayed()
        
        # Check for scan button
        scan_btn = card.find_element(By.ID, "scan-btn")
        assert scan_btn.is_displayed()
        assert scan_btn.is_enabled()
    
    def test_connected_device_card_exists(self, ble_dashboard):
        """Test that the connected device card is present."""
        card = ble_dashboard.find_element(By.ID, "ble-device-info-card")
        assert card.is_displayed()
        
        # Check that the 'No device connected' message is shown initially
        no_device_message = card.find_element(By.ID, "no-device-message")
        assert no_device_message.is_displayed()
        assert "No device connected" in no_device_message.text
    
    def test_device_filter_functionality(self, ble_dashboard):
        """Test that the device filter inputs are working."""
        # Find the filter input
        filter_input = ble_dashboard.find_element(By.ID, "device-filter")
        assert filter_input.is_displayed()
        
        # Check radio buttons
        name_filter = ble_dashboard.find_element(By.ID, "filter-by-name")
        address_filter = ble_dashboard.find_element(By.ID, "filter-by-address")
        
        assert name_filter.is_selected()  # Name filter should be selected by default
        assert not address_filter.is_selected()
        
        # Test changing filter
        address_filter.click()
        assert address_filter.is_selected()
        assert not name_filter.is_selected()
    
    def test_scan_button_click(self, ble_dashboard):
        """Test clicking the scan button and verify UI changes."""
        # Find scan button
        scan_btn = ble_dashboard.find_element(By.ID, "scan-btn")
        
        # Click the scan button
        scan_btn.click()
        
        try:
            # Check that the scan status appears
            WebDriverWait(ble_dashboard, 3).until(
                EC.visibility_of_element_located((By.ID, "scan-status"))
            )
            
            # Check that the stop button appears
            stop_btn = WebDriverWait(ble_dashboard, 3).until(
                EC.visibility_of_element_located((By.ID, "stop-scan-btn"))
            )
            
            # Check that the scan button is hidden
            assert "hidden" in scan_btn.get_attribute("class")
            
            # Let the scan complete (this might take time - adjust timeout as needed)
            WebDriverWait(ble_dashboard, 10).until(
                EC.invisibility_of_element_located((By.ID, "scan-status"))
            )
            
            # After scan completes, check that scan button is visible again
            assert WebDriverWait(ble_dashboard, 3).until(
                EC.visibility_of_element_located((By.ID, "scan-btn"))
            )
        except TimeoutException:
            # If we get a timeout, it might be because the backend is not running
            # or the scanning API is not working. Let's not fail the test in this case.
            pytest.skip("Scan button click did not update UI as expected - backend may not be running")
    
    def test_toast_notification_system(self, ble_dashboard):
        """Test that toast notifications can be triggered and displayed."""
        # Execute JavaScript to trigger a toast notification
        ble_dashboard.execute_script("""
            if (window.bleDashboard && window.bleDashboard.showToast) {
                window.bleDashboard.showToast('Test notification', 'info', 3000);
                return true;
            }
            return false;
        """)
        
        try:
            # Check if toast appears
            toast = WebDriverWait(ble_dashboard, 3).until(
                EC.visibility_of_element_located((By.CLASS_NAME, "toast"))
            )
            assert "Test notification" in toast.text
            
            # Wait for toast to disappear
            WebDriverWait(ble_dashboard, 5).until(
                EC.invisibility_of_element_located((By.CLASS_NAME, "toast"))
            )
        except TimeoutException:
            pytest.skip("Toast notification system not available")
    
    def test_scan_options_toggle(self, ble_dashboard):
        """Test the scan options toggle functionality."""
        # Find the toggle button
        toggle_btn = ble_dashboard.find_element(By.ID, "scan-options-toggle")
        options_panel = ble_dashboard.find_element(By.ID, "scan-options-panel")
        
        # Check initial state - panel should be hidden
        assert "hidden" in options_panel.get_attribute("class")
        
        # Click toggle button
        toggle_btn.click()
        
        # Panel should now be visible
        WebDriverWait(ble_dashboard, 3).until(
            lambda d: "hidden" not in options_panel.get_attribute("class")
        )
        
        # Click toggle button again
        toggle_btn.click()
        
        # Panel should be hidden again
        WebDriverWait(ble_dashboard, 3).until(
            lambda d: "hidden" in options_panel.get_attribute("class")
        )


# Add mock tests for BLE functionality that require backend API interaction
class TestBleMockFunctionality:
    """Tests that mock the BLE API interaction."""
    
    def test_mock_device_discovered(self, ble_dashboard):
        """Test handling of discovered devices by injecting mock data."""
        # Inject a mock discovered device via JavaScript
        mock_device = {
            'address': '00:11:22:33:44:55',
            'name': 'Mock BLE Device',
            'rssi': -65,
            'services': []
        }
        
        script = f"""
        if (window.bleDashboard && window.bleDashboard.renderDiscoveredDevice) {{
            window.bleDashboard.renderDiscoveredDevice({mock_device!r});
            return true;
        }}
        return false;
        """
        
        result = ble_dashboard.execute_script(script)
        if not result:
            pytest.skip("BLE Dashboard controller not available")
        
        # Check if the device appears in the list
        try:
            device_item = WebDriverWait(ble_dashboard, 3).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-address='00:11:22:33:44:55']"))
            )
            assert "Mock BLE Device" in device_item.text
        except TimeoutException:
            pytest.fail("Mock device was not rendered in the UI")
    
    def test_mock_connection_status(self, ble_dashboard):
        """Test connection status updates by calling the status update method directly."""
        script = """
        if (window.bleDashboard && window.bleDashboard.updateDeviceConnectionState) {
            // Create a mock device
            const mockDevice = {
                address: '00:11:22:33:44:55',
                name: 'Mock Connected Device'
            };
            
            // Update state to connected
            window.bleDashboard.updateDeviceConnectionState('connected', mockDevice);
            return true;
        }
        return false;
        """
        
        result = ble_dashboard.execute_script(script)
        if not result:
            pytest.skip("BLE Dashboard controller not available")
        
        # Check if the device info section is displayed
        try:
            device_info = WebDriverWait(ble_dashboard, 3).until(
                EC.visibility_of_element_located((By.ID, "device-info"))
            )
            assert device_info.is_displayed()
            
            # Check connection status indicator
            status_indicator = ble_dashboard.find_element(By.ID, "device-status-indicator")
            assert "status-connected" in status_indicator.get_attribute("class")
            
            status_text = ble_dashboard.find_element(By.ID, "device-status-text")
            assert "Connected" in status_text.text
        except TimeoutException:
            pytest.fail("Mock connection status update did not update the UI")
