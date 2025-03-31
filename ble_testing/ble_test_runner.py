"""
BLE Test Runner

Main component that orchestrates API and WebSocket testing for BLE module.
"""
import os
import sys
import json
import logging
import asyncio
import time
import argparse
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

# Local imports
from openapi_parser import BLESpecParser
from config_manager import BLETestConfig
from api_tester import BLEAPITester
from websocket_tester import BLEWebSocketTester

def setup_logging(log_level='info', output_file=None):
    """Configure logging for the test script."""
    log_levels = {
        'debug': logging.DEBUG,
        'info': logging.INFO,
        'warning': logging.WARNING,
        'error': logging.ERROR
    }
    
    level = log_levels.get(log_level.lower(), logging.INFO)
    
    # Configure root logger
    logger = logging.getLogger('ble_tester')
    logger.setLevel(level)
    
    # Clear existing handlers if any
    if logger.handlers:
        logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    
    # Format
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler)
    
    # File handler if output file is specified
    if output_file:
        file_handler = logging.FileHandler(output_file)
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger

def generate_report(api_results, websocket_results, output_format='text', output_file=None):
    """Generate a test report in the specified format."""
    logger = logging.getLogger('ble_tester.report')
    
    # Add timestamped default output file if not provided
    output_file = output_file or f"ble_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    # Calculate statistics
    total_api_tests = len(api_results)
    successful_api_tests = sum(1 for r in api_results if r['status'] == 'Success')
    total_ws_tests = len(websocket_results)
    successful_ws_tests = sum(1 for r in websocket_results if r['status'] == 'Success')
    total_tests = total_api_tests + total_ws_tests
    successful_tests = successful_api_tests + successful_ws_tests
    
    # Create report data
    report = {
        'timestamp': datetime.now().isoformat(),
        'summary': {
            'total_tests': total_tests,
            'successful_tests': successful_tests,
            'pass_rate': f"{(successful_tests / total_tests * 100) if total_tests > 0 else 0:.2f}%",
            'api_tests': {
                'total': total_api_tests,
                'successful': successful_api_tests,
                'pass_rate': f"{(successful_api_tests / total_api_tests * 100) if total_api_tests > 0 else 0:.2f}%"
            },
            'websocket_tests': {
                'total': total_ws_tests,
                'successful': successful_ws_tests,
                'pass_rate': f"{(successful_ws_tests / total_ws_tests * 100) if total_ws_tests > 0 else 0:.2f}%"
            }
        },
        'api_results': api_results,
        'websocket_results': websocket_results
    }
    
    # Write report to file with utf-8 encoding
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"BLE TEST REPORT - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 80 + "\n")
        f.write(f"SUMMARY: {successful_tests}/{total_tests} tests passed ({report['summary']['pass_rate']})\n")
        f.write(f"  API Tests: {successful_api_tests}/{total_api_tests} passed ({report['summary']['api_tests']['pass_rate']})\n")
        f.write(f"  WebSocket Tests: {successful_ws_tests}/{total_ws_tests} passed ({report['summary']['websocket_tests']['pass_rate']})\n")
        f.write("\n" + "-" * 80 + "\n")
        
        # Write API results
        if api_results:
            f.write("\nAPI TEST RESULTS:\n")
            f.write("-" * 80 + "\n")
            for result in api_results:
                status_indicator = "✓" if result['status'] == 'Success' else "✗"
                f.write(f"{status_indicator} {result['method']} {result['endpoint']}: {result['status']} ({result['latency']} ms)\n")
                if result['status'] != 'Success' and result['error']:
                    f.write(f"   Error: {result['error']}\n")
        
        # Write WebSocket results
        if websocket_results:
            f.write("\nWEBSOCKET TEST RESULTS:\n")
            f.write("-" * 80 + "\n")
            for result in websocket_results:
                status_indicator = "✓" if result['status'] == 'Success' else "✗"
                f.write(f"{status_indicator} {result['endpoint']}: {result['status']} ({result['latency']} ms)\n")
                if result['status'] != 'Success' and result['error']:
                    f.write(f"   Error: {result['error']}\n")
        
        f.write("\n" + "=" * 80 + "\n")
    
    logger.info(f"Report saved to {output_file}")
    return report

async def run_tests(config):
    """Run all API and WebSocket tests based on the extracted endpoints."""
    logger = logging.getLogger('ble_tester.runner')
    
    # Parse OpenAPI spec
    logger.info(f"Parsing OpenAPI specification from {config.spec_file}")
    parser = BLESpecParser(config.spec_file)
    try:
        endpoints = parser.extract_all_endpoints()
    except Exception as e:
        logger.error(f"Failed to parse OpenAPI specification: {str(e)}")
        return [], []
    
    # Initialize testers
    api_tester = BLEAPITester(
        base_url=config.base_url,
        timeout=config.timeout,
        retry_count=config.retry_count,
        headers=config.headers
    )
    
    websocket_tester = BLEWebSocketTester(config.websocket_url, timeout=config.timeout)
    
    # Prepare API endpoints for testing
    all_api_endpoints = []
    for category, endpoints_list in endpoints.items():
        if category != 'websocket_endpoints' and category != 'security':
            all_api_endpoints.extend(endpoints_list)
    
    # Log test plan
    logger.info(f"Preparing to test {len(all_api_endpoints)} API endpoints and "
                f"{len(endpoints['websocket_endpoints'])} WebSocket endpoints")
    
    # Test API endpoints concurrently
    api_results = []
    if all_api_endpoints:
        logger.info("Starting API endpoint tests...")
        with ThreadPoolExecutor(max_workers=config.concurrency) as executor:
            futures = []
            for endpoint in all_api_endpoints:
                future = executor.submit(
                    api_tester.test_endpoint,
                    endpoint['path'],
                    endpoint['method'],
                    endpoint.get('parameters', []),
                    endpoint.get('request_body', {}),
                    endpoint.get('responses', {})
                )
                futures.append(future)
            
            # Collect results as they complete
            for future in futures:
                try:
                    result = future.result()
                    api_results.append(result)
                    
                    # Log result
                    status_str = "✓" if result['status'] == 'Success' else "✗"
                    logger.info(f"{status_str} {result['method']} {result['endpoint']}: {result['status']} "
                                f"({result['latency']} ms)")
                except Exception as e:
                    logger.error(f"Error during API test execution: {str(e)}")
    
    # Test WebSocket endpoints sequentially
    websocket_results = []
    if endpoints['websocket_endpoints']:
        logger.info("Starting WebSocket endpoint tests...")
        for ws_endpoint in endpoints['websocket_endpoints']:
            try:
                result = await websocket_tester.test_websocket_endpoint(
                    ws_endpoint['path'],
                    ws_endpoint.get('parameters', [])
                )
                websocket_results.append(result)
                
                # Log result
                status_str = "✓" if result['status'] == 'Success' else "✗"
                logger.info(f"{status_str} WebSocket {result['endpoint']}: {result['status']} "
                            f"({result['latency']} ms)")
            except Exception as e:
                logger.error(f"Error during WebSocket test: {str(e)}")
                websocket_results.append({
                    'endpoint': ws_endpoint['path'],
                    'type': ws_endpoint.get('type', 'unknown'),
                    'status': 'Failed',
                    'latency': 0,
                    'error': str(e)
                })
    
    return api_results, websocket_results

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='BLE API and WebSocket Testing Tool')
    
    parser.add_argument('--spec-file', required=True, help='Path to the OpenAPI specification file')
    parser.add_argument('--base-url', required=True, help='Base URL for the API endpoints')
    parser.add_argument('--websocket-url', help='Base URL for WebSocket endpoints (if different from base-url)')
    parser.add_argument('--timeout', type=int, default=10, help='Request timeout in seconds (default: 10)')
    parser.add_argument('--retry-count', type=int, default=1, help='Number of retries for failed requests (default: 1)')
    parser.add_argument('--concurrency', type=int, default=5, help='Number of concurrent API tests (default: 5)')
    parser.add_argument('--log-level', choices=['debug', 'info', 'warning', 'error'], default='info',
                        help='Logging level (default: info)')
    parser.add_argument('--log-file', help='Log file path')
    parser.add_argument('--output-format', choices=['text', 'json', 'csv'], default='text',
                        help='Report output format (default: text)')
    parser.add_argument('--output-file', help='Path to save the test report')
    parser.add_argument('--auth-token', help='Authorization token for API requests')
    parser.add_argument('--auth-type', default='Bearer', help='Authorization type (default: Bearer)')
    
    return parser.parse_args()

def normalize_websocket_url(url):
    """Convert HTTP/HTTPS URLs to WS/WSS for WebSocket connections."""
    if url.startswith("http://"):
        return url.replace("http://", "ws://", 1)
    elif url.startswith("https://"):
        return url.replace("https://", "wss://", 1)
    return url

async def main():
    """Main entry point for the BLE test runner."""
    # Parse command line arguments
    args = parse_arguments()
    
    # Setup logging
    logger = setup_logging(args.log_level, args.log_file)
    logger.info("Starting BLE API and WebSocket Testing Tool")
    
    # Prepare headers if authentication is provided
    headers = {}
    if args.auth_token:
        headers['Authorization'] = f"{args.auth_type} {args.auth_token}"
    
    # Create configuration
    config = type('Config', (), {
    'spec_file': args.spec_file,
    'base_url': args.base_url,
    'websocket_url': normalize_websocket_url(args.websocket_url or args.base_url),
    'timeout': args.timeout,
    'retry_count': args.retry_count,
    'concurrency': args.concurrency,
    'headers': headers
})
    # Run tests
    logger.info("Running tests...")
    api_results, websocket_results = await run_tests(config)
    
    # Generate report
    logger.info("Generating test report...")
    generate_report(api_results, websocket_results, args.output_format, args.output_file)
    
    logger.info("Testing completed")

if __name__ == "__main__":
    asyncio.run(main())