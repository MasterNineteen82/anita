import os
import re
import sys
import requests
import logging
import json
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor
import argparse

"""
Diagnostic tool for analyzing frontend and backend issues in a web application.
This script helps identify why HTML templates are showing errors.
"""

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DiagnosticTool:
    def __init__(self, app_path='app.py', templates_dir='templates', 
                 base_url='http://localhost:8000', static_dir='static'):
        self.app_path = app_path
        self.templates_dir = templates_dir
        self.static_dir = static_dir
        self.base_url = base_url
        self.routes = []
        self.templates = []
        self.static_files = []
        self.issues = []
        self.detected_framework = None

    def auto_detect_structure(self):
        """Auto-detect project structure and framework used."""
        logger.info("Auto-detecting project structure...")
        
        # Common project structures
        structures = [
            # Flask standard
            {'app': 'app.py', 'templates': 'templates', 'static': 'static'},
            # Flask with blueprints
            {'app': 'app.py', 'templates': 'app/templates', 'static': 'app/static'},
            # Django standard
            {'app': 'manage.py', 'templates': 'templates', 'static': 'static'},
            # React + Flask
            {'app': 'backend/app.py', 'templates': 'frontend/build', 'static': 'frontend/build/static'},
            # Vue + Flask
            {'app': 'backend/app.py', 'templates': 'frontend/dist', 'static': 'frontend/dist/assets'},

            {'app': 'poc/app.py', 'templates': 'poc/frontend/templates', 'static': 'poc/frontend/static'},
            {'app': 'app.py', 'templates': 'frontend/templates', 'static': 'frontend/static'},
        ]
        
        # Try to detect structure
        for structure in structures:
            if os.path.exists(structure['app']):
                logger.info(f"Detected app file at {structure['app']}")
                self.app_path = structure['app']
                
                if os.path.exists(structure['templates']):
                    logger.info(f"Detected templates at {structure['templates']}")
                    self.templates_dir = structure['templates']
                
                if os.path.exists(structure['static']):
                    logger.info(f"Detected static files at {structure['static']}")
                    self.static_dir = structure['static']
                
                # Detect framework
                if 'manage.py' in structure['app']:
                    self.detected_framework = 'Django'
                else:
                    with open(structure['app'], 'r') as f:
                        content = f.read()
                        if 'flask' in content.lower():
                            self.detected_framework = 'Flask'
                        elif 'fastapi' in content.lower():
                            self.detected_framework = 'FastAPI'
                
                logger.info(f"Detected framework: {self.detected_framework or 'Unknown'}")
                break
        
        return self.app_path, self.templates_dir, self.static_dir

    def scan_templates(self):
        """Scan template directory for HTML files."""
        logger.info(f"Scanning templates directory: {self.templates_dir}")
        
        if not os.path.exists(self.templates_dir):
            self.issues.append(f"Templates directory '{self.templates_dir}' not found")
            return []
            
        templates = []
        for root, _, files in os.walk(self.templates_dir):
            for file in files:
                if file.endswith(('.html', '.htm', '.jinja', '.jinja2')):
                    template_path = os.path.join(root, file)
                    rel_path = os.path.relpath(template_path, self.templates_dir)
                    templates.append({
                        'path': template_path,
                        'relative_path': rel_path,
                        'route_path': '/' + rel_path.replace('\\', '/').replace('.html', '')
                                             .replace('.htm', '').replace('.jinja', '')
                                             .replace('.jinja2', ''),
                        'last_modified': os.path.getmtime(template_path)
                    })
                    
        self.templates = templates
        logger.info(f"Found {len(templates)} HTML templates")
        return templates

    def scan_static_files(self):
        """Scan static directory for CSS/JS files."""
        logger.info(f"Scanning static directory: {self.static_dir}")
        
        if not os.path.exists(self.static_dir):
            self.issues.append(f"Static directory '{self.static_dir}' not found")
            return []
            
        static_files = []
        for root, _, files in os.walk(self.static_dir):
            for file in files:
                if file.endswith(('.css', '.js')):
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, self.static_dir)
                    static_files.append({
                        'path': file_path,
                        'relative_path': rel_path,
                        'type': 'css' if file.endswith('.css') else 'js',
                        'last_modified': os.path.getmtime(file_path)
                    })
                    
        self.static_files = static_files
        logger.info(f"Found {len(static_files)} static files")
        return static_files

    def extract_routes(self):
        """Extract routes from the app file."""
        logger.info(f"Extracting routes from {self.app_path}")
        
        if not os.path.exists(self.app_path):
            self.issues.append(f"Application file '{self.app_path}' not found")
            return []
            
        with open(self.app_path, 'r') as f:
            content = f.read()
        
        # Framework-specific route patterns
        route_patterns = {
            'Flask': [
                r'@app\.route\([\'"](.+?)[\'"](,\s*methods=\[.+?\])?\)',
                r'@blueprint\.route\([\'"](.+?)[\'"](,\s*methods=\[.+?\])?\)',
                r'@\w+\.route\([\'"](.+?)[\'"](,\s*methods=\[.+?\])?\)'
            ],
            'Django': [
                r'path\([\'"](.+?)[\'"](,\s*\w+\.as_view\(\)|\s*,\s*\w+)'
            ],
            'FastAPI': [
                r'@app\.(get|post|put|delete|patch)\([\'"](.+?)[\'"](,\s*.+?)?\)',
                r'@router\.(get|post|put|delete|patch)\([\'"](.+?)[\'"](,\s*.+?)?\)',  # Add router support
                r'include_router\((\w+)\.router(,\s*prefix=[\'"](.+?)[\'"])?\)'  # Add include_router support
            ]
        }
        
        routes = []
        patterns = route_patterns.get(self.detected_framework or 'Flask', route_patterns['Flask'])
        
        for pattern in patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                if self.detected_framework == 'FastAPI':
                    route_path = match.group(2)  # FastAPI pattern has method as group 1
                    http_method = match.group(1).upper()
                else:
                    route_path = match.group(1)
                    http_method = 'GET'  # Default
                    if match.group(0) and 'methods' in match.group(0):
                        methods_match = re.search(r'methods=\[(.*?)\]', match.group(0))
                        if methods_match:
                            http_method = methods_match.group(1).split(',')[0].strip().strip("'\"")
                
                routes.append({
                    'path': route_path,
                    'method': http_method,
                    'line': content[:match.start()].count('\n') + 1,
                    'full_match': match.group(0)
                })
        
        # Try to extract template references
        for route in routes:
            # Different frameworks have different template rendering patterns
            template_patterns = {
                'Flask': r'render_template\([\'"](.+?)[\'"](,|\))',
                'Django': r'render\(.*[\'"](.+?)[\'"](,|\))',
                'FastAPI': r'templates\.TemplateResponse\([\'"](.+?)[\'"](,|\))'
            }
            
            pattern = template_patterns.get(self.detected_framework or 'Flask', template_patterns['Flask'])
            
            # Find the function body for this route
            route_idx = content.find(route['full_match'])
            next_def = content.find('def', route_idx)
            if next_def == -1:
                next_def = len(content)
            
            # Find opening brace after the def
            func_start = content.find(':', next_def)
            if func_start == -1:
                continue
                
            # Find next function or end of file
            next_func = content.find('def ', func_start)
            if next_func == -1:
                next_func = len(content)
            
            route_func = content[func_start:next_func]
            template_match = re.search(pattern, route_func)
            if template_match:
                route['template'] = template_match.group(1)
        
        self.routes = routes
        logger.info(f"Found {len(routes)} routes in application")
        return routes

    def analyze_templates(self):
        """Analyze HTML templates for common issues."""
        logger.info("Analyzing templates for common issues")
        
        for template in self.templates:
            try:
                with open(template['path'], 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check for from tags
                from_tags = re.findall(r'{%\s*from\s+[\'"](.+?)[\'"]', content)
                
                for from_source in from_tags:
                    from_path = os.path.join(self.templates_dir, from_source)
                    if not os.path.exists(from_path):
                        self.issues.append(f"Template {template['relative_path']} imports from non-existent template: {from_source}")
                
                # Check for common template issues
                soup = BeautifulSoup(content, 'html.parser')
                
                # Check for broken extends/includes
                extends_tags = re.findall(r'{%\s*extends\s+[\'"](.+?)[\'"]', content)
                include_tags = re.findall(r'{%\s*include\s+[\'"](.+?)[\'"]', content)
                
                for parent in extends_tags:
                    parent_path = os.path.join(self.templates_dir, parent)
                    if not os.path.exists(parent_path):
                        self.issues.append(f"Template {template['relative_path']} extends non-existent template: {parent}")
                
                for include in include_tags:
                    include_path = os.path.join(self.templates_dir, include)
                    if not os.path.exists(include_path):
                        self.issues.append(f"Template {template['relative_path']} includes non-existent template: {include}")
                
                # Check for broken static references
                static_refs = []
                for link in soup.find_all('link'):
                    if 'href' in link.attrs:
                        static_refs.append(link['href'])
                
                for script in soup.find_all('script'):
                    if 'src' in script.attrs:
                        static_refs.append(script['src'])
                
                for img in soup.find_all('img'):
                    if 'src' in img.attrs:
                        static_refs.append(img['src'])
                
                # Check static references
                for ref in static_refs:
                    if ref.startswith(('http://', 'https://', '//', 'data:')):
                        continue  # External or data URL
                    
                    if ref.startswith('/static/') or ref.startswith('static/'):
                        ref_path = ref.replace('/static/', '').replace('static/', '')
                        static_path = os.path.join(self.static_dir, ref_path)
                        if not os.path.exists(static_path):
                            self.issues.append(f"Template {template['relative_path']} references non-existent static file: {ref}")
                
                # Check for undefined variables (basic check)
                variable_pattern = r'{{(.+?)}}'
                variables = re.findall(variable_pattern, content)
                for var in variables:
                    var = var.strip()
                    if '.' not in var and not any(keyword in var for keyword in ['url_for', 'config', 'request', 'static', '|']):
                        # This is a basic check and may have false positives
                        template['possible_undefined'] = template.get('possible_undefined', []) + [var]
                
            except Exception as e:
                self.issues.append(f"Error analyzing template {template['relative_path']}: {str(e)}")

    def test_routes(self, test_server=True, max_workers=5):
        """Test routes for proper responses if a server is running."""
        if not test_server:
            logger.info("Skipping route testing (no server specified)")
            return
        
        logger.info(f"Testing routes against server at {self.base_url}")
        
        # Filter out routes with parameters for automatic testing
        testable_routes = []
        for route in self.routes:
            # Skip routes with path parameters for automatic testing
            if '<' in route['path'] and '>' in route['path']:
                logger.info(f"Skipping route with parameters: {route['path']}")
                continue
            if route['method'] in ['GET', 'POST']:
                testable_routes.append(route)
        
        # Test routes in parallel for better performance
        def test_route(route):
            try:
                url = urljoin(self.base_url, route['path'].rstrip('/') or '/')
                if route['method'] == 'GET':
                    response = requests.get(url, timeout=5)
                elif route['method'] == 'POST':
                    # Simple POST with empty data for testing
                    response = requests.post(url, data={}, timeout=5)
                else:
                    return  # Skip non-GET/POST routes for now
                
                route['status_code'] = response.status_code
                route['response_size'] = len(response.content)
                route['content_type'] = response.headers.get('content-type', '')
                
                if response.status_code >= 400:
                    self.issues.append(f"Route {route['path']} returned status code {response.status_code}")
                    
                # Basic check for error messages in HTML response
                if 'text/html' in route['content_type']:
                    error_patterns = [
                        "error", "exception", "traceback", "not found", "undefined",
                        "jinja2.exceptions", "werkzeug", "internal server error"
                    ]
                    for pattern in error_patterns:
                        if pattern in response.text.lower():
                            self.issues.append(f"Route {route['path']} contains possible error text: '{pattern}'")
                            break
                    
            except requests.RequestException as e:
                self.issues.append(f"Error testing route {route['path']}: {str(e)}")
                route['error'] = str(e)
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            executor.map(test_route, testable_routes)

    def find_missing_route_templates(self):
        """Find templates without corresponding routes and vice versa."""
        template_paths = {t['route_path']: t for t in self.templates}
        route_paths = {r['path']: r for r in self.routes}
        
        # Find templates without routes
        for template in self.templates:
            if template['route_path'] not in route_paths:
                self.issues.append(f"Template {template['relative_path']} has no corresponding route")
                template['no_route'] = True
        
        # Find routes without templates (only for routes that likely render templates)
        for route in self.routes:
            if route.get('template'):
                template_file = route['template']
                template_full_path = os.path.join(self.templates_dir, template_file)
                if not os.path.exists(template_full_path):
                    self.issues.append(f"Route {route['path']} references non-existent template: {template_file}")
                    route['missing_template'] = True

    def generate_report(self, output_file=None):
        """Generate a diagnostic report."""
        report = "\n" + "="*80 + "\n"
        report += " DIAGNOSTIC REPORT ".center(80, "=") + "\n"
        report += "="*80 + "\n\n"
        
        report += f"Framework: {self.detected_framework or 'Unknown'}\n"
        report += f"Application file: {self.app_path}\n"
        report += f"Templates directory: {self.templates_dir}\n"
        report += f"Static files directory: {self.static_dir}\n"
        report += f"Found {len(self.templates)} HTML templates\n"
        report += f"Found {len(self.static_files)} static files\n"
        report += f"Found {len(self.routes)} routes in application\n"
        report += f"Identified {len(self.issues)} potential issues\n\n"
        
        if self.issues:
            report += "ISSUES FOUND:\n"
            for i, issue in enumerate(self.issues, 1):
                report += f"{i}. {issue}\n"
        else:
            report += "No issues found. If errors still occur, consider:\n"
            report += "- Checking application logs for runtime errors\n"
            report += "- Verifying database connections and configurations\n"
            report += "- Examining JavaScript console for frontend errors\n"
            report += "- Checking for issues in static files (CSS, JS)\n"
        
        report += "\n" + "="*80 + "\n"
        
        print(report)
        
        # Output to file if requested
        if output_file:
            with open(output_file, 'w') as f:
                f.write(report)
            
            # Also save detailed JSON data
            json_file = output_file.replace('.txt', '.json')
            if json_file == output_file:
                json_file += '.json'
                
            with open(json_file, 'w') as f:
                json.dump({
                    'framework': self.detected_framework,
                    'app_path': self.app_path,
                    'templates_dir': self.templates_dir,
                    'static_dir': self.static_dir,
                    'templates': self.templates,
                    'routes': self.routes,
                    'static_files': self.static_files,
                    'issues': self.issues
                }, f, indent=2)
                
            logger.info(f"Report saved to {output_file} and {json_file}")

    def run_diagnostics(self, test_server=False, auto_detect=True, output_file=None):
        """Run all diagnostic checks."""
        if auto_detect:
            self.auto_detect_structure()
            
        self.scan_templates()
        self.scan_static_files()
        self.extract_routes()
        self.analyze_templates()
        if test_server:
            self.test_routes(test_server=True)
        self.find_missing_route_templates()
        self.generate_report(output_file)
        
        return {
            'templates': self.templates,
            'routes': self.routes,
            'static_files': self.static_files,
            'issues': self.issues
        }

if __name__ == "__main__":
    
    parser = argparse.ArgumentParser(description='Diagnose web application frontend/backend issues')
    parser.add_argument('--app', default='app.py', help='Path to application file (default: app.py)')
    parser.add_argument('--templates', default='templates', help='Path to templates directory (default: templates)')
    parser.add_argument('--static', default='static', help='Path to static files directory (default: static)')
    parser.add_argument('--url', default='http://localhost:5000', help='Base URL for testing routes (default: http://localhost:5000)')
    parser.add_argument('--test-server', action='store_true', help='Test routes against running server')
    parser.add_argument('--auto-detect', action='store_true', help='Auto-detect project structure')
    parser.add_argument('--output', help='Output file for diagnostic report')
    
    args = parser.parse_args()
    
    diagnostic = DiagnosticTool(
        app_path=args.app,
        templates_dir=args.templates,
        static_dir=args.static,
        base_url=args.url
    )
    
    diagnostic.run_diagnostics(
        test_server=args.test_server,
        auto_detect=args.auto_detect,
        output_file=args.output
    )
