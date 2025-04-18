# Selenium Testing Framework for BLE Dashboard

This directory contains a Selenium-based testing framework for automated testing of the BLE Dashboard frontend UI.

## Overview

The testing framework uses:
- **Selenium WebDriver**: For browser automation
- **pytest**: As the test runner and assertion framework
- **Page Object Model**: For better test maintainability

## Directory Structure

```
frontend/
│
├── conftest.py             # pytest fixtures and configuration
├── requirements-test.txt   # Testing dependencies
├── README.md               # This file
│
├── page_objects/           # Page Object Model classes
│   ├── __init__.py
│   └── ble_dashboard_page.py
│
└── test_*.py               # Test files
```

## Installation

1. Install the required dependencies:

```bash
cd k:\anita\poc\tests\frontend
pip install -r requirements-test.txt
```

2. Make sure you have Chrome installed (the tests use Chrome by default)

## Running Tests

Before running tests, ensure that your BLE Dashboard application is running locally. By default, the tests expect the application to be accessible at `http://localhost:5000/ble_dashboard`.

### Run all tests:

```bash
cd k:\anita\poc\tests\frontend
pytest
```

### Run with HTML report:

```bash
pytest --html=report.html
```

### Run specific test file:

```bash
pytest test_ble_dashboard.py
```

### Run in parallel (faster execution):

```bash
pytest -n 4  # Use 4 parallel processes
```

### Run with verbose output:

```bash
pytest -v
```

## Test Categories

The test suite is organized into several categories:

1. **Basic UI Tests** (`test_ble_dashboard.py`):
   - Verify all components of the BLE Dashboard are present
   - Test basic interactions like clicking buttons
   - Verify UI state changes correctly

2. **BLE Services Tests** (`test_ble_services.py`):
   - Test rendering and interaction with BLE services
   - Test the signal strength indicators

3. **Page Object Model Tests** (`test_with_page_objects.py`):
   - Demonstrates using the Page Object Model for cleaner tests
   - Covers the same functionality as other tests but with improved maintainability

## Mocking Approach

Since the tests need to run without a real BLE backend, we use JavaScript injection to simulate BLE functionality:

- **Mock Device Discovery**: Inject mock device data directly into the UI
- **Mock Connection States**: Simulate connection/disconnection without actual BLE hardware
- **Mock Service Data**: Inject test service data to verify rendering

This approach allows testing the UI without requiring actual BLE hardware or a backend server.

## Writing New Tests

### Using Page Objects

For better maintainability, use the `BleDashboardPage` class in your tests:

```python
def test_example(dashboard_page):
    # Start a scan
    dashboard_page.click_scan_button()
    
    # Wait for scan to complete
    dashboard_page.wait_for_scan_to_complete()
    
    # Check results
    assert dashboard_page.get_device_count() > 0
```

### Injecting Mock Data

To test with mock BLE data:

```python
# Create a mock device
mock_device = {
    "address": "00:11:22:33:44:55",
    "name": "Test Device",
    "rssi": -65
}

# Inject it into the UI
dashboard_page.mock_discovered_device(mock_device)

# Verify it appears in the list
assert dashboard_page.has_device_with_address("00:11:22:33:44:55")
```

## Troubleshooting

- **Tests fail with TimeoutException**: Ensure the BLE Dashboard is running and accessible
- **Element not found errors**: The HTML structure may have changed - update the selectors in the page object models
- **JavaScript execution fails**: Ensure the BLE Dashboard controller is properly initialized

## Known Limitations

- Tests require the frontend to be running separately
- Some tests are skipped if the backend API is not available
- The headless Chrome browser may behave slightly differently than a visible browser
