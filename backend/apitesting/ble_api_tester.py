#!/usr/bin/env python3
"""
BLE API and WebSocket Testing Tool

Comprehensive testing script for BLE Module API endpoints and WebSocket connections
based on OpenAPI specification.
"""
import argparse
import logging
import sys
import os
from datetime import datetime

# Import the testing modules
from ble_testing.openapi_parser import BLESpecParser
from ble_testing.api_tester import BLEAPITester
from ble_testing.websocket_tester import BLEWebSocketTester
from ble_testing.config_manager import BLETestConfig
from ble_testing.result_reporter import BLEResultReporter

def setup_argparse():
    """Configure command-line arguments for the testing script."""
    parser = argparse.ArgumentParser(description='BLE API and WebSocket Testing Tool')
    
    parser.add_argument('--spec-file', required=True, help='Path to OpenAPI specification file')
    parser.add_argument('--base-url', default='http://localhost:8000', help='Base URL for API requests')
    parser.add_argument('--websocket-url', default='ws://localhost:8000', help='Base URL for WebSocket connections')
    parser.add_argument('--timeout', type=int, default=10, help='Request timeout in seconds')
    parser.add_argument('--retries', type=int, default=1, help='Number of retries for failed requests')
    parser.add_argument('--concurrency', type=int, default=5, help='Maximum concurrent API requests')
    parser.add_argument('--log-level', choices=['debug', 'info', 'warning', 'error'], default='info', 
                        help='Logging level')
    parser.add_argument('--output', default='ble_test_report.json', help='Output file for test results')
    parser.add_argument('--format', choices=['json', 'html', 'text'], default='json', 
                        help='Output format for test results')
    parser.add_argument('--auth-token', help='Authentication token for API requests')
    parser.add_argument('--test-categories', nargs='+', 
                        choices=['adapter', 'scanner', 'device', 'services', 'characteristics', 'notifications', 'all'],
                        default=['all'], help='Categories of tests to run')
    
    return parser.parse_args()

def setup_logging(log_level):
    """Configure logging for the testing script."""
    numeric_level = getattr(logging, log_level.upper(), None)
    logging.basicConfig(
        level=numeric_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(f'ble_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
        ]
    )
    return logging.getLogger('ble_tester')

def main():
    """Main entry point for the BLE API testing script."""
    # Parse command-line arguments
    args = setup_argparse()
    
    # Set up logging
    logger = setup_logging(args.log_level)
    logger.info("Starting BLE API and WebSocket Testing")
    
    # Initialize configuration
    config = BLETestConfig(args)
    logger.info(f"Testing against base URL: {config.get_base_url()}")
    logger.info(f"Using OpenAPI spec: {args.spec_file}")
    
    try:
        # Parse OpenAPI specification
        logger.info("Parsing OpenAPI specification...")
        parser = BLESpecParser(args.spec_file)
        spec = parser.parse_openapi_spec()
        
        # Initialize result reporter
        reporter = BLEResultReporter(config)
        
        # Initialize API tester
        api_tester = BLEAPITester(config, reporter)
        
        # Run API tests based on extracted endpoints
        logger.info("Starting API endpoint tests...")
        if 'all' in args.test_categories or 'adapter' in args.test_categories:
            adapter_endpoints = parser.extract_adapter_endpoints(spec)
            api_tester.test_adapter_endpoints(adapter_endpoints)
        
        if 'all' in args.test_categories or 'scanner' in args.test_categories:
            scanner_endpoints = parser.extract_scanner_endpoints(spec)
            api_tester.test_scanner_endpoints(scanner_endpoints)
        
        if 'all' in args.test_categories or 'device' in args.test_categories:
            device_endpoints = parser.extract_device_endpoints(spec)
            api_tester.test_device_endpoints(device_endpoints)
        
        if 'all' in args.test_categories or 'services' in args.test_categories:
            service_endpoints = parser.extract_service_endpoints(spec)
            api_tester.test_service_endpoints(service_endpoints)
        
        if 'all' in args.test_categories or 'characteristics' in args.test_categories:
            characteristic_endpoints = parser.extract_characteristic_endpoints(spec)
            api_tester.test_characteristic_endpoints(characteristic_endpoints)
        
        # Run WebSocket tests if applicable
        if 'all' in args.test_categories or 'notifications' in args.test_categories:
            logger.info("Starting WebSocket tests...")
            websocket_endpoints = parser.extract_websocket_endpoints(spec)
            websocket_tester = BLEWebSocketTester(config, reporter)
            websocket_tester.test_all_websockets(websocket_endpoints)
        
        # Generate final report
        logger.info("Generating test report...")
        reporter.generate_report()
        
        # Show summary
        reporter.display_summary()
        
    except Exception as e:
        logger.error(f"An error occurred during testing: {str(e)}", exc_info=True)
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())