import os
import re
import sys

def analyze_failures(failure_text):
    """Extract test failures and categorize them."""
    patterns = {
        'method_signature': r"TypeError: (\w+\.\w+\(\)) got an unexpected keyword argument '(\w+)'",
        'missing_method': r"AttributeError: '(\w+)' object has no attribute '(\w+)'",
        'case_sensitivity': r"AssertionError: assert '([A-Z0-9:]+)' == '([a-z0-9:]+)'",
        'model_validation': r"pydantic_core\._pydantic_core\.ValidationError",
        'async_issues': r"TypeError: object MagicMock can't be used in 'await' expression",
        'http_status': r"assert (\d+) == (\d+)"
    }
    
    issues = {}
    for category, pattern in patterns.items():
        matches = re.findall(pattern, failure_text)
        if matches:
            issues[category] = matches
    
    return issues

if __name__ == "__main__":
    # Read from a file if provided, otherwise use stdin
    if len(sys.argv) > 1:
        with open(sys.argv[1], "r") as f:
            failures = f.read()
    else:
        print("Please paste the test failure output (press Ctrl+Z and Enter when done):")
        failures = sys.stdin.read()
    
    issues = analyze_failures(failures)
    
    print("\n=== TEST FAILURE ANALYSIS ===\n")
    
    if 'method_signature' in issues:
        print("\n== METHOD SIGNATURE ISSUES ==")
        for method, param in issues['method_signature']:
            print(f"- {method} doesn't accept parameter '{param}'")
    
    if 'missing_method' in issues:
        print("\n== MISSING METHOD ISSUES ==")
        for cls, method in issues['missing_method']:
            print(f"- '{cls}' doesn't have method '{method}'")
    
    if 'case_sensitivity' in issues:
        print("\n== CASE SENSITIVITY ISSUES ==")
        for upper, lower in issues['case_sensitivity']:
            print(f"- Expected '{lower}' but got '{upper}'")
    
    if 'model_validation' in issues:
        print("\n== MODEL VALIDATION ISSUES ==")
        print("- Pydantic validation errors (check model field requirements)")
    
    if 'async_issues' in issues:
        print("\n== ASYNC MOCKING ISSUES ==")
        print("- MagicMock objects used directly in 'await' expressions")
    
    if 'http_status' in issues:
        print("\n== HTTP STATUS CODE ISSUES ==")
        for actual, expected in issues['http_status']:
            print(f"- Expected status {expected} but got {actual}")