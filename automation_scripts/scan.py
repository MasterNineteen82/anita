import requests
import time
import json
import os
import re
import importlib.util
import inspect
from urllib.parse import urljoin, urlparse
from requests.exceptions import RequestException
import sys
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any, Optional, Set, Tuple

BASE_URL = "http://127.0.0.1:8000/"

# Define common API endpoints to scan
DEFAULT_ENDPOINTS = [
    "",  # Root endpoint
    "api/",
    "docs/",
    "redoc/",
    "health/",
    "status/",
    "users/",
    "auth/",
    "login/",
    "logout/",
    "register/",
    "v1/",
    "v2/",
    "swagger/",
    "metrics/",
    "admin/",
    "api/logs",
    "api/available_logs",
    "api/smartcard/status",
    "api/nfc/status",
    # Add more endpoints specific to your application
]

# Common HTTP methods to test
HTTP_METHODS = ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]

class ApiScanner:
    def __init__(self, base_url: str, endpoints: List[str] = None, timeout: int = 10, 
                 auth_token: str = None, project_path: str = None):
        self.base_url = base_url
        self.endpoints = endpoints or DEFAULT_ENDPOINTS
        self.timeout = timeout
        self.results = []
        self.auth_token = auth_token
        self.project_path = project_path
        self.headers = {}
        
        if auth_token:
            self.headers["Authorization"] = f"Bearer {auth_token}"
    
    def analyze_project_structure(self) -> List[str]:
        """Analyze project files to find API endpoints."""
        if not self.project_path or not os.path.exists(self.project_path):
            print(f"Project path not found: {self.project_path}")
            return []
        
        discovered_endpoints = set()
        
        # Patterns to look for in code files
        route_patterns = [
            r'@app\.(?:route|get|post|put|delete|patch)\([\'"]([^\'"]+)[\'"]',  # Flask
            r'@router\.(?:get|post|put|delete|patch)\([\'"]([^\'"]+)[\'"]',  # FastAPI router
            r'path\([\'"]([^\'"]+)[\'"]',  # Django URLs
            r'url\([\'"]([^\'"]+)[\'"]',  # Django older style
        ]
        
        # Files to focus on
        key_files = ['app.py', 'main.py', 'urls.py', 'routes.py', 'views.py', 'api.py']
        
        for root, dirs, files in os.walk(self.project_path):
            for file in files:
                if file.endswith('.py'):
                    is_key_file = file in key_files
                    file_path = os.path.join(root, file)
                    
                    # Only process key files and files in directories that might contain API routes
                    if is_key_file or 'api' in file_path.lower() or 'route' in file_path.lower():
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                                
                                # Look for route patterns
                                for pattern in route_patterns:
                                    for match in re.finditer(pattern, content):
                                        route = match.group(1)
                                        # Normalize the route (remove regex patterns etc.)
                                        route = re.sub(r'{[^}]+}', '', route)
                                        route = route.rstrip('/')
                                        if route and not route.startswith('/'):
                                            route = '/' + route
                                        if route:
                                            discovered_endpoints.add(route.lstrip('/'))
                                            
                        except Exception as e:
                            print(f"Error analyzing file {file_path}: {e}")
        
        # Try to import main application modules
        self._try_import_app_modules()
                
        print(f"Project analysis discovered {len(discovered_endpoints)} potential endpoints")
        return list(discovered_endpoints)
    
    def _try_import_app_modules(self):
        """Try to import main.py or app.py to extract routes programmatically."""
        if not self.project_path:
            return
            
        for module_name in ['main', 'app']:
            module_path = os.path.join(self.project_path, f"{module_name}.py")
            if os.path.exists(module_path):
                try:
                    # Add project path to sys.path
                    if self.project_path not in sys.path:
                        sys.path.insert(0, self.project_path)
                        
                    # Try to import the module
                    spec = importlib.util.spec_from_file_location(module_name, module_path)
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                        
                        # Look for FastAPI or Flask apps
                        for attr_name in dir(module):
                            attr = getattr(module, attr_name)
                            # Check for FastAPI app
                            if hasattr(attr, 'routes') and callable(getattr(attr, 'add_api_route', None)):
                                print(f"Found FastAPI app in {module_name}.py")
                                # Try to extract routes - would need more complex handling
                            # Check for Flask app
                            elif hasattr(attr, 'url_map') and callable(getattr(attr, 'route', None)):
                                print(f"Found Flask app in {module_name}.py")
                                # Could extract Flask routes here
                except Exception as e:
                    print(f"Error importing {module_path}: {e}")
        
    def scan_endpoint(self, endpoint: str, method: str = "GET", data: Dict = None) -> Dict[str, Any]:
        """Scan a specific endpoint with the given HTTP method."""
        url = urljoin(self.base_url, endpoint)
        result = {
            "endpoint": endpoint,
            "url": url,
            "method": method,
            "status_code": None,
            "response_time": None,
            "content_type": None,
            "content_length": None,
            "error": None,
            "success": False
        }
        
        try:
            start_time = time.time()
            
            # Try different content types for requests with bodies
            headers = self.headers.copy()
            if method in ["POST", "PUT", "PATCH"] and not headers.get("Content-Type"):
                headers["Content-Type"] = "application/json"
                
            # Common parameters for all requests
            kwargs = {
                "timeout": self.timeout,
                "headers": headers,
                "allow_redirects": True
            }
            
            if method == "GET":
                response = requests.get(url, **kwargs)
            elif method == "POST":
                response = requests.post(url, json=data, **kwargs)
            elif method == "PUT":
                response = requests.put(url, json=data, **kwargs)
            elif method == "DELETE":
                response = requests.delete(url, **kwargs)
            elif method == "PATCH":
                response = requests.patch(url, json=data, **kwargs)
            elif method == "OPTIONS":
                response = requests.options(url, **kwargs)
            else:
                result["error"] = f"Unsupported method: {method}"
                return result
                
            response_time = time.time() - start_time
            
            result.update({
                "status_code": response.status_code,
                "response_time": round(response_time * 1000, 2),  # Convert to ms
                "content_type": response.headers.get('Content-Type'),
                "content_length": len(response.content),
                "success": 200 <= response.status_code < 300,
                "headers": dict(response.headers),
            })
            
            # Try to parse and include a snippet of the response if it's JSON
            if 'application/json' in result.get('content_type', ''):
                try:
                    result["response_preview"] = json.dumps(response.json(), indent=2)[:200] + "..."
                except json.JSONDecodeError:
                    result["response_preview"] = "Invalid JSON response"
            
            # Check for CORS headers
            if method == "OPTIONS":
                cors_headers = {k: v for k, v in response.headers.items() if 'cors' in k.lower()}
                if cors_headers:
                    result["cors_headers"] = cors_headers
            
        except RequestException as e:
            result["error"] = str(e)
            
        return result
    
    def discover_endpoints(self) -> List[str]:
        """Try to discover additional endpoints by checking API documentation."""
        discovered = []
        
        # Try to get OpenAPI docs
        for doc_endpoint in ["docs", "swagger", "openapi.json", "api/docs", "swagger-ui", "api/schema"]:
            try:
                response = requests.get(urljoin(self.base_url, doc_endpoint), timeout=self.timeout)
                if response.status_code == 200:
                    print(f"Found API documentation at {doc_endpoint}")
                    
                    # If it's OpenAPI JSON, try to parse it
                    if doc_endpoint.endswith('.json') and 'application/json' in response.headers.get('Content-Type', ''):
                        try:
                            api_schema = response.json()
                            if 'paths' in api_schema:
                                for path in api_schema['paths'].keys():
                                    path = path.lstrip('/')
                                    if path:
                                        discovered.append(path)
                                print(f"Extracted {len(discovered)} endpoints from OpenAPI schema")
                        except Exception as e:
                            print(f"Failed to parse OpenAPI schema: {e}")
                    break
            except Exception:
                continue
        
        # If we have a sitemap, try to parse it
        try:
            response = requests.get(urljoin(self.base_url, "sitemap.xml"), timeout=self.timeout)
            if response.status_code == 200 and 'xml' in response.headers.get('Content-Type', ''):
                # Basic regex for URLs in sitemap
                urls = re.findall(r'<loc>(.*?)</loc>', response.text)
                for url in urls:
                    parsed = urlparse(url)
                    path = parsed.path.lstrip('/')
                    if path and path not in discovered:
                        discovered.append(path)
                print(f"Extracted {len(urls)} URLs from sitemap")
        except Exception:
            pass
            
        return discovered
    
    def scan_all(self) -> List[Dict[str, Any]]:
        """Scan all configured endpoints."""
        print(f"Starting scan of {self.base_url}")
        
        # Try to discover additional endpoints from project structure
        if self.project_path:
            project_endpoints = self.analyze_project_structure()
            if project_endpoints:
                print(f"Found {len(project_endpoints)} endpoints in project files")
                self.endpoints.extend(project_endpoints)
        
        # Try to discover additional endpoints from API docs
        discovered = self.discover_endpoints()
        if discovered:
            print(f"Discovered {len(discovered)} additional endpoints from API documentation")
            self.endpoints.extend(discovered)
        
        # Remove duplicates and normalize
        self.endpoints = list(set(self.endpoints))
        self.endpoints = [endpoint.rstrip('/') for endpoint in self.endpoints]
        
        print(f"Scanning {len(self.endpoints)} endpoints...")
        
        # First scan all endpoints with GET
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(self.scan_endpoint, endpoint) for endpoint in self.endpoints]
            self.results = [future.result() for future in futures]
        
        # Then test additional methods on endpoints that responded
        additional_results = []
        working_endpoints = [r["endpoint"] for r in self.results if r["success"] or r["status_code"] == 405]
        
        if working_endpoints:
            print(f"Testing additional HTTP methods on {len(working_endpoints)} responsive endpoints...")
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = []
                for endpoint in working_endpoints:
                    for method in ["POST", "PUT", "DELETE", "PATCH", "OPTIONS"]:
                        # For POST/PUT/PATCH, add a simple test payload
                        data = {"test": "data"} if method in ["POST", "PUT", "PATCH"] else None
                        futures.append(executor.submit(self.scan_endpoint, endpoint, method, data))
                
                additional_results = [future.result() for future in futures]
            
            self.results.extend(additional_results)
        
        return self.results
    
    def print_results(self) -> None:
        """Print scan results in a readable format."""
        success_count = sum(1 for r in self.results if r["success"])
        error_count = len(self.results) - success_count
        
        print("\n" + "="*80)
        print(f"Scan Results - {self.base_url}")
        print(f"Total Requests: {len(self.results)}, Success: {success_count}, Errors: {error_count}")
        print("="*80)
        
        # Group results by endpoint and method
        by_endpoint = {}
        for result in self.results:
            endpoint = result["endpoint"]
            if endpoint not in by_endpoint:
                by_endpoint[endpoint] = []
            by_endpoint[endpoint].append(result)
        
        # Print results grouped by endpoint
        for endpoint, results in sorted(by_endpoint.items()):
            print(f"\n== Endpoint: {endpoint} ==")
            
            # Sort by method
            for result in sorted(results, key=lambda x: x["method"]):
                status = result["status_code"] or "Error"
                if result["error"]:
                    print(f"  {result['method']} - Error: {result['error']}")
                else:
                    print(f"  {result['method']} - Status: {status} - {result['response_time']}ms - "
                          f"{result.get('content_length', 0)} bytes")
                    if result.get("cors_headers"):
                        print(f"    CORS Headers: {result['cors_headers']}")
    
    def save_results(self, filename: str = "api_scan_results.json") -> None:
        """Save scan results to a JSON file."""
        with open(filename, "w") as f:
            json.dump({
                "base_url": self.base_url,
                "scan_time": time.strftime("%Y-%m-%d %H:%M:%S"),
                "results": self.results
            }, f, indent=2)
        print(f"\nResults saved to {filename}")

def main():
    base_url = BASE_URL
    project_path = None
    auth_token = None
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    
    # Check for project path argument
    if len(sys.argv) > 2:
        project_path = sys.argv[2]
        if not os.path.exists(project_path):
            print(f"Warning: Project path {project_path} does not exist")
            project_path = None
    
    # Check for auth token
    if len(sys.argv) > 3:
        auth_token = sys.argv[3]
    
    scanner = ApiScanner(base_url, project_path=project_path, auth_token=auth_token)
    scanner.scan_all()
    scanner.print_results()
    scanner.save_results()

if __name__ == "__main__":
    main()