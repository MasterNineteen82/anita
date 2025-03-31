import json
import csv
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Union

"""
BLE Result Reporter Module

Handles test result collection, reporting, and formatting for the BLE testing framework.
"""


class BLEResultReporter:
    """
    Handles collecting, processing, and outputting test results for BLE testing.
    Supports multiple output formats and report generation.
    """
    
    SUPPORTED_FORMATS = ["text", "json", "csv", "html"]
    
    def __init__(self, config):
        """
        Initialize the result reporter with configuration settings.
        
        Args:
            config: Configuration object with test settings
        """
        self.config = config
        self.api_results = []
        self.websocket_results = []
        self.logger = logging.getLogger('ble_tester.reporter')
        # Ensure output directory exists if specified in config
        self._validate_output_directory()
    
    def _validate_output_directory(self) -> None:
        """Ensure the output directory exists if specified in configuration."""
        try:
            output_path = getattr(self.config, 'output', None)
            if output_path:
                directory = os.path.dirname(output_path)
                if directory and not os.path.exists(directory):
                    os.makedirs(directory)
                    self.logger.info(f"Created output directory: {directory}")
        except Exception as e:
            self.logger.warning(f"Failed to validate/create output directory: {str(e)}")
    
    def record_api_result(self, endpoint: str, method: str, status: bool, 
                           status_code: int, latency: float, error: str = None, 
                           payload: Any = None) -> Dict[str, Any]:
        """
        Record the result of an API test.
        
        Args:
            endpoint: The API endpoint that was tested
            method: HTTP method used (GET, POST, etc.)
            status: Boolean indicating success or failure
            status_code: HTTP status code returned
            latency: Response time in milliseconds
            error: Error message if test failed
            payload: Request/response payload for reference
            
        Returns:
            Dictionary containing the recorded result
        """
        try:
            result = {
                'endpoint': endpoint,
                'method': method,
                'status': 'Success' if status else 'Failure',
                'status_code': status_code,
                'latency': latency,
                'error': error,
                'payload': payload,
                'timestamp': datetime.now().isoformat()
            }
            self.api_results.append(result)
            return result
        except Exception as e:
            self.logger.error(f"Failed to record API result: {str(e)}")
            # Create a fallback minimal result
            fallback_result = {
                'endpoint': str(endpoint),
                'method': str(method),
                'status': 'Error',
                'status_code': 0,
                'latency': 0,
                'error': f"Recording error: {str(e)}",
                'timestamp': datetime.now().isoformat()
            }
            self.api_results.append(fallback_result)
            return fallback_result
    
    def record_websocket_result(self, endpoint: str, ws_type: str, status: bool, 
                                latency: float, error: str = None, 
                                payload: Any = None) -> Dict[str, Any]:
        """
        Record the result of a WebSocket test.
        
        Args:
            endpoint: The WebSocket endpoint that was tested
            ws_type: Type of WebSocket test (notification, subscription, etc.)
            status: Boolean indicating success or failure
            latency: Response time in milliseconds
            error: Error message if test failed
            payload: WebSocket message payload for reference
            
        Returns:
            Dictionary containing the recorded result
        """
        try:
            result = {
                'endpoint': endpoint,
                'type': ws_type,
                'status': 'Success' if status else 'Failure',
                'latency': latency,
                'error': error,
                'payload': payload,
                'timestamp': datetime.now().isoformat()
            }
            self.websocket_results.append(result)
            return result
        except Exception as e:
            self.logger.error(f"Failed to record WebSocket result: {str(e)}")
            # Create a fallback minimal result
            fallback_result = {
                'endpoint': str(endpoint),
                'type': str(ws_type),
                'status': 'Error',
                'latency': 0,
                'error': f"Recording error: {str(e)}",
                'timestamp': datetime.now().isoformat()
            }
            self.websocket_results.append(fallback_result)
            return fallback_result
    
    def calculate_statistics(self) -> Dict[str, Any]:
        """
        Calculate test statistics from recorded results.
        
        Returns:
            Dictionary with test statistics
        """
        try:
            total_api_tests = len(self.api_results)
            successful_api_tests = sum(1 for r in self.api_results if r['status'] == 'Success')
            
            total_ws_tests = len(self.websocket_results)
            successful_ws_tests = sum(1 for r in self.websocket_results if r['status'] == 'Success')
            
            total_tests = total_api_tests + total_ws_tests
            successful_tests = successful_api_tests + successful_ws_tests
            
            # Safe division for calculating percentages
            api_pass_rate = (successful_api_tests / total_api_tests * 100) if total_api_tests > 0 else 0
            ws_pass_rate = (successful_ws_tests / total_ws_tests * 100) if total_ws_tests > 0 else 0
            total_pass_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0
            
            return {
                'timestamp': datetime.now().isoformat(),
                'summary': {
                    'total_tests': total_tests,
                    'successful_tests': successful_tests,
                    'pass_rate': f"{total_pass_rate:.2f}%",
                    'api_tests': {
                        'total': total_api_tests,
                        'successful': successful_api_tests,
                        'pass_rate': f"{api_pass_rate:.2f}%"
                    },
                    'websocket_tests': {
                        'total': total_ws_tests,
                        'successful': successful_ws_tests,
                        'pass_rate': f"{ws_pass_rate:.2f}%"
                    }
                },
                'api_results': self.api_results,
                'websocket_results': self.websocket_results
            }
        except Exception as e:
            self.logger.error(f"Failed to calculate statistics: {str(e)}")
            # Return minimal statistics in case of error
            return {
                'timestamp': datetime.now().isoformat(),
                'summary': {
                    'total_tests': 0,
                    'successful_tests': 0,
                    'pass_rate': "0.00%",
                    'api_tests': {'total': 0, 'successful': 0, 'pass_rate': "0.00%"},
                    'websocket_tests': {'total': 0, 'successful': 0, 'pass_rate': "0.00%"}
                },
                'error': str(e)
            }
    
    def generate_report(self, output_format: Optional[str] = None, 
                        output_file: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate a test report in the specified format.
        
        Args:
            output_format: Format for the output report (text, json, csv, html)
            output_file: Path to save the report file
            
        Returns:
            Dictionary with report data
        """
        try:
            # Use config values if not specified
            output_format = output_format or getattr(self.config, 'format', 'text')
            output_file = output_file or getattr(self.config, 'output', None)
            
            # Validate output format
            if output_format not in self.SUPPORTED_FORMATS:
                self.logger.warning(f"Unsupported output format '{output_format}', defaulting to 'text'")
                output_format = 'text'
            
            # Calculate statistics and create report data
            report = self.calculate_statistics()
            
            # Get summary values for easier access
            total_tests = report['summary']['total_tests']
            successful_tests = report['summary']['successful_tests']
            total_api_tests = report['summary']['api_tests']['total']
            successful_api_tests = report['summary']['api_tests']['successful']
            total_ws_tests = report['summary']['websocket_tests']['total']
            successful_ws_tests = report['summary']['websocket_tests']['successful']
            
            # Output based on format
            if output_format == 'json':
                self._generate_json_report(report, output_file)
            elif output_format == 'csv':
                self._generate_csv_report(output_file)
            elif output_format == 'html':
                self._generate_html_report(report, output_file)
            else:  # Text format
                self._generate_text_report(report, output_file)
            
            return report
            
        except Exception as e:
            self.logger.error(f"Failed to generate report: {str(e)}")
            return {
                'error': f"Report generation failed: {str(e)}",
                'timestamp': datetime.now().isoformat()
            }
    
    def _generate_json_report(self, report: Dict[str, Any], output_file: Optional[str]) -> None:
        """Generate a JSON format report."""
        try:
            if output_file:
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(report, f, indent=2, default=str)
                self.logger.info(f"JSON report saved to {output_file}")
            else:
                # Make sure JSON is properly serialized for non-serializable objects
                print(json.dumps(report, indent=2, default=str))
        except (IOError, PermissionError) as e:
            self.logger.error(f"Failed to write JSON report to {output_file}: {str(e)}")
            print(f"Error writing to file: {str(e)}")
            # Print to console as fallback
            print(json.dumps(report, indent=2, default=str))
        except Exception as e:
            self.logger.error(f"Unexpected error generating JSON report: {str(e)}")
    
    def _generate_csv_report(self, output_file: Optional[str]) -> None:
        """Generate a CSV format report."""
        if not output_file:
            self.logger.error("CSV format requires an output file")
            print("Error: CSV format requires an output file to be specified")
            return
            
        try:
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['Test Type', 'Endpoint', 'Method', 'Status', 'Status Code', 'Latency (ms)', 'Error'])
                
                # API tests
                for result in self.api_results:
                    writer.writerow([
                        'API',
                        result['endpoint'],
                        result['method'],
                        result['status'],
                        result.get('status_code', ''),
                        result['latency'],
                        result.get('error', '') or ''
                    ])
                
                # WebSocket tests
                for result in self.websocket_results:
                    writer.writerow([
                        'WebSocket',
                        result['endpoint'],
                        result.get('type', 'unknown'),
                        result['status'],
                        '',
                        result['latency'],
                        result.get('error', '') or ''
                    ])
            self.logger.info(f"CSV report saved to {output_file}")
        except (IOError, PermissionError) as e:
            self.logger.error(f"Failed to write CSV report to {output_file}: {str(e)}")
            print(f"Error writing to file: {str(e)}")
        except Exception as e:
            self.logger.error(f"Unexpected error generating CSV report: {str(e)}")
    
    def _generate_html_report(self, report: Dict[str, Any], output_file: Optional[str]) -> None:
        """Generate an HTML format report."""
        try:
            # Simple HTML template for the report
            html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>BLE API Test Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #333366; }}
        h2 {{ color: #336699; }}
        .summary {{ background-color: #f0f0f0; padding: 10px; border-radius: 5px; }}
        .success {{ color: green; }}
        .failure {{ color: red; }}
        table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
        th, td {{ text-align: left; padding: 8px; border-bottom: 1px solid #ddd; }}
        th {{ background-color: #336699; color: white; }}
        tr:hover {{ background-color: #f5f5f5; }}
        .error-details {{ color: red; margin-left: 20px; }}
    </style>
</head>
<body>
    <h1>BLE API Test Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</h1>
    
    <div class="summary">
        <h2>Summary</h2>
        <p>Total Tests: {report['summary']['total_tests']} | 
           Passed: {report['summary']['successful_tests']} | 
           Pass Rate: {report['summary']['pass_rate']}</p>
        <p>API Tests: {report['summary']['api_tests']['total']} | 
           Passed: {report['summary']['api_tests']['successful']} | 
           Pass Rate: {report['summary']['api_tests']['pass_rate']}</p>
        <p>WebSocket Tests: {report['summary']['websocket_tests']['total']} | 
           Passed: {report['summary']['websocket_tests']['successful']} | 
           Pass Rate: {report['summary']['websocket_tests']['pass_rate']}</p>
    </div>
"""
            
            # API Results Table
            if self.api_results:
                html_content += """
    <h2>API Test Results</h2>
    <table>
        <tr>
            <th>Status</th>
            <th>Method</th>
            <th>Endpoint</th>
            <th>Status Code</th>
            <th>Latency (ms)</th>
        </tr>
"""
                for result in self.api_results:
                    status_class = "success" if result['status'] == 'Success' else "failure"
                    status_symbol = "✓" if result['status'] == 'Success' else "✗"
                    
                    html_content += f"""
        <tr>
            <td class="{status_class}">{status_symbol}</td>
            <td>{result['method']}</td>
            <td>{result['endpoint']}</td>
            <td>{result.get('status_code', '')}</td>
            <td>{result['latency']}</td>
        </tr>"""
                    
                    if result['status'] != 'Success' and result.get('error'):
                        html_content += f"""
        <tr>
            <td colspan="5" class="error-details">Error: {result['error']}</td>
        </tr>"""
                
                html_content += """
    </table>
"""
            
            # WebSocket Results Table
            if self.websocket_results:
                html_content += """
    <h2>WebSocket Test Results</h2>
    <table>
        <tr>
            <th>Status</th>
            <th>Endpoint</th>
            <th>Type</th>
            <th>Latency (ms)</th>
        </tr>
"""
                for result in self.websocket_results:
                    status_class = "success" if result['status'] == 'Success' else "failure"
                    status_symbol = "✓" if result['status'] == 'Success' else "✗"
                    
                    html_content += f"""
        <tr>
            <td class="{status_class}">{status_symbol}</td>
            <td>{result['endpoint']}</td>
            <td>{result.get('type', 'unknown')}</td>
            <td>{result['latency']}</td>
        </tr>"""
                    
                    if result['status'] != 'Success' and result.get('error'):
                        html_content += f"""
        <tr>
            <td colspan="4" class="error-details">Error: {result['error']}</td>
        </tr>"""
                
                html_content += """
    </table>
"""
            
            # Close HTML
            html_content += """
</body>
</html>
"""
            
            if output_file:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                self.logger.info(f"HTML report saved to {output_file}")
            else:
                print("HTML report cannot be displayed in console. Please provide an output file.")
        
        except (IOError, PermissionError) as e:
            self.logger.error(f"Failed to write HTML report to {output_file}: {str(e)}")
            print(f"Error writing to file: {str(e)}")
        except Exception as e:
            self.logger.error(f"Unexpected error generating HTML report: {str(e)}")
    
    def _generate_text_report(self, report: Dict[str, Any], output_file: Optional[str]) -> None:
        """Generate a text format report."""
        try:
            # Extract summary values
            total_tests = report['summary']['total_tests']
            successful_tests = report['summary']['successful_tests']
            total_api_tests = report['summary']['api_tests']['total']
            successful_api_tests = report['summary']['api_tests']['successful']
            total_ws_tests = report['summary']['websocket_tests']['total']
            successful_ws_tests = report['summary']['websocket_tests']['successful']
            
            # Determine status indicators based on environment
            # Windows cmd doesn't display Unicode checkmarks well
            if sys.platform == 'win32' and not os.environ.get('WT_SESSION'):  # Not in Windows Terminal
                success_mark = "+"
                failure_mark = "x"
            else:
                success_mark = "✓"
                failure_mark = "✗"
            
            # Create the text report content
            report_content = "\n" + "=" * 80 + "\n"
            report_content += f"BLE API TEST REPORT - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            report_content += "=" * 80 + "\n"
            report_content += f"SUMMARY: {successful_tests}/{total_tests} tests passed ({report['summary']['pass_rate']})\n"
            report_content += f"  API Tests: {successful_api_tests}/{total_api_tests} passed ({report['summary']['api_tests']['pass_rate']})\n"
            report_content += f"  WebSocket Tests: {successful_ws_tests}/{total_ws_tests} passed ({report['summary']['websocket_tests']['pass_rate']})\n"
            report_content += "\n" + "-" * 80 + "\n"
            
            # Add API results
            if self.api_results:
                report_content += "\nAPI TEST RESULTS:\n"
                report_content += "-" * 80 + "\n"
                for result in self.api_results:
                    status_indicator = success_mark if result['status'] == 'Success' else failure_mark
                    report_content += f"{status_indicator} {result['method']} {result['endpoint']}: {result['status']} ({result['latency']} ms)\n"
                    if result['status'] != 'Success' and result.get('error'):
                        report_content += f"   Error: {result['error']}\n"
            
            # Add WebSocket results
            if self.websocket_results:
                report_content += "\nWEBSOCKET TEST RESULTS:\n"
                report_content += "-" * 80 + "\n"
                for result in self.websocket_results:
                    status_indicator = success_mark if result['status'] == 'Success' else failure_mark
                    report_content += f"{status_indicator} {result['endpoint']}: {result['status']} ({result['latency']} ms)\n"
                    if result['status'] != 'Success' and result.get('error'):
                        report_content += f"   Error: {result['error']}\n"
            
            report_content += "\n" + "=" * 80 + "\n"
            
            # Print to console
            print(report_content)
            
            # Save to file if specified
            if output_file:
                try:
                    # Ensure directory exists
                    output_path = Path(output_file)
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write(report_content)
                    self.logger.info(f"Text report saved to {output_file}")
                except Exception as e:
                    self.logger.error(f"Failed to write text report to file: {str(e)}")
                    print(f"Error writing to file: {str(e)}")
        
        except Exception as e:
            self.logger.error(f"Failed to generate text report: {str(e)}")
            print(f"Error generating report: {str(e)}")
    
    def display_summary(self) -> None:
        """Display a summary of test results to the console."""
        try:
            report = self.calculate_statistics()
            total = report['summary']['total_tests']
            successful = report['summary']['successful_tests']
            
            print("\n" + "=" * 60)
            print(f"TEST SUMMARY: {successful}/{total} tests passed ({report['summary']['pass_rate']})")
            print("=" * 60)
            
            # Add more detailed breakdown
            if total > 0:
                api_tests = report['summary']['api_tests']
                ws_tests = report['summary']['websocket_tests']
                
                if api_tests['total'] > 0:
                    print(f"API Tests    : {api_tests['successful']}/{api_tests['total']} passed ({api_tests['pass_rate']})")
                
                if ws_tests['total'] > 0:
                    print(f"WebSocket    : {ws_tests['successful']}/{ws_tests['total']} passed ({ws_tests['pass_rate']})")
        
        except Exception as e:
            self.logger.error(f"Failed to display summary: {str(e)}")
            print(f"Error displaying test summary: {str(e)}")