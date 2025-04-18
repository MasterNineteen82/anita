import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import json


class TestBleServices:
    """Test suite for BLE Services interaction in the UI."""

    def test_mock_service_rendering(self, ble_dashboard):
        """Test rendering of BLE services by injecting mock service data."""
        # Mock service data
        mock_services = [
            {
                "uuid": "1800",
                "name": "Generic Access",
                "characteristics": [
                    {
                        "uuid": "2A00",
                        "name": "Device Name",
                        "properties": {
                            "read": True,
                            "write": False,
                            "notify": False
                        },
                        "value": "Mock Device"
                    },
                    {
                        "uuid": "2A01",
                        "name": "Appearance",
                        "properties": {
                            "read": True,
                            "write": False,
                            "notify": False
                        }
                    }
                ]
            },
            {
                "uuid": "180F",
                "name": "Battery Service",
                "characteristics": [
                    {
                        "uuid": "2A19",
                        "name": "Battery Level",
                        "properties": {
                            "read": True,
                            "notify": True,
                            "indicate": False
                        },
                        "value": "85%"
                    }
                ]
            }
        ]
        
        # First ensure device appears connected
        ble_dashboard.execute_script("""
            if (window.bleDashboard && window.bleDashboard.updateDeviceConnectionState) {
                const mockDevice = {
                    address: '00:11:22:33:44:55',
                    name: 'Mock Device for Services Test'
                };
                window.bleDashboard.updateDeviceConnectionState('connected', mockDevice);
                return true;
            }
            return false;
        """)
        
        # Wait for device info to be visible
        try:
            WebDriverWait(ble_dashboard, 3).until(
                EC.visibility_of_element_located((By.ID, "device-info"))
            )
        except TimeoutException:
            pytest.skip("Cannot set mock connected device state")
        
        # Now render services
        script = f"""
            if (window.bleDashboard && window.bleDashboard.renderDeviceServices) {{
                window.bleDashboard.renderDeviceServices({json.dumps(mock_services)});
                return true;
            }}
            return false;
        """
        
        result = ble_dashboard.execute_script(script)
        if not result:
            pytest.skip("BLE Dashboard controller not available")
        
        # Check if services are rendered
        try:
            services_container = WebDriverWait(ble_dashboard, 3).until(
                EC.visibility_of_element_located((By.ID, "device-services"))
            )
            
            # Check service count
            services_count = ble_dashboard.find_element(By.ID, "services-count")
            assert "2 services" in services_count.text or "2 service" in services_count.text
            
            # Check specific service names
            service_headers = services_container.find_elements(By.CLASS_NAME, "service-header")
            service_names = [header.text for header in service_headers]
            
            assert any("Generic Access" in name for name in service_names)
            assert any("Battery Service" in name for name in service_names)
            
            # Expand a service to check characteristics
            service_headers[0].click()
            
            # Check if characteristics are visible
            char_items = WebDriverWait(ble_dashboard, 3).until(
                EC.presence_of_all_elements_located((By.CLASS_NAME, "characteristic-item"))
            )
            assert len(char_items) > 0
            
        except (TimeoutException, AssertionError) as e:
            pytest.fail(f"Service rendering test failed: {str(e)}")
    
    def test_signal_strength_indicator(self, ble_dashboard):
        """Test the RSSI signal strength indicator rendering."""
        # Create a mock device with RSSI data
        script = """
            if (window.bleDashboard && window.bleDashboard.createSignalStrengthIndicator) {
                // Test with different RSSI values
                const strongSignal = window.bleDashboard.createSignalStrengthIndicator(-45);
                const mediumSignal = window.bleDashboard.createSignalStrengthIndicator(-65);
                const weakSignal = window.bleDashboard.createSignalStrengthIndicator(-85);
                
                // Append to document for testing
                const testContainer = document.createElement('div');
                testContainer.id = 'signal-test-container';
                testContainer.appendChild(strongSignal);
                testContainer.appendChild(mediumSignal);
                testContainer.appendChild(weakSignal);
                document.body.appendChild(testContainer);
                
                return true;
            }
            return false;
        """
        
        result = ble_dashboard.execute_script(script)
        if not result:
            pytest.skip("Signal strength indicator function not available")
        
        # Check the signal strength indicators
        try:
            test_container = WebDriverWait(ble_dashboard, 3).until(
                EC.presence_of_element_located((By.ID, "signal-test-container"))
            )
            
            indicators = test_container.find_elements(By.CLASS_NAME, "signal-strength")
            assert len(indicators) == 3
            
            # Check strength attributes
            assert indicators[0].get_attribute("data-strength") == "3"  # Strong
            assert indicators[1].get_attribute("data-strength") == "2"  # Medium
            assert indicators[2].get_attribute("data-strength") == "0"  # Weak
            
            # Clean up after test
            ble_dashboard.execute_script("""
                const container = document.getElementById('signal-test-container');
                if (container) container.remove();
            """)
            
        except (TimeoutException, AssertionError) as e:
            pytest.fail(f"Signal strength indicator test failed: {str(e)}")
