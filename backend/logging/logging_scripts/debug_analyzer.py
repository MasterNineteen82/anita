import json
from pathlib import Path
import datetime

# Update these paths to use the new structure
BASE_LOG_DIR = Path("logs")
APP_LOG_PATH = BASE_LOG_DIR / "active"  # All app logs are now in active
API_LOG_PATH = BASE_LOG_DIR / "active"  # API logs also in active
ERROR_LOG_PATH = BASE_LOG_DIR  # Error logs directly in logs folder
FRONTEND_LOG_PATH = BASE_LOG_DIR / "active"  # Frontend logs also in active

def get_latest_file(directory, pattern):
    """Get the latest file in a directory matching the pattern"""
    files = list(Path(directory).glob(pattern))
    if not files:
        return None
    return max(files, key=lambda f: f.stat().st_mtime)

def analyze_app_logs():
    latest_app_log = get_latest_file(APP_LOG_PATH, "app_*.log")
    issues = []
    
    if not latest_app_log:
        issues.append({"error": "App Log File Not Found", "suggestion": f"Check if log files exist in {APP_LOG_PATH}"})
        return issues
        
    try:
        with open(latest_app_log, "r", encoding="utf-8") as log_file:
            for line in log_file:
                if "ERROR" in line or "CRITICAL" in line or "WARNING" in line:
                    issue = {"log": line.strip()}
                    # Add specific error detection logic here
                    if "module 'nfc' has no attribute 'core'" in line:
                        issue["error"] = "Backend NFC Module Issue"
                        issue["suggestion"] = "Check if 'nfc' module is correctly installed and that 'core' exists."
                    elif "500 (INTERNAL SERVER ERROR)" in line:
                        issue["error"] = "API Endpoint Failure"
                        issue["suggestion"] = "Ensure API routes are correctly handling requests and logging errors."
                    elif "No readers found" in line:
                        issue["error"] = "Smartcard Reader Not Detected" 
                        issue["suggestion"] = "Ensure that a smartcard reader is connected and the PC/SC service is running."
                    else:
                        issue["error"] = "General Application Error"
                        issue["suggestion"] = "Review the log entry for potential problems."
                        
                    issues.append(issue)
    except Exception as e:
        issues.append({"error": "Error reading app log", "suggestion": str(e)})
        
    return issues

def analyze_frontend_logs():
    latest_frontend_log = get_latest_file(FRONTEND_LOG_PATH, "frontend_*.json")
    issues = []
    
    if not latest_frontend_log:
        issues.append({"error": "Frontend Log File Not Found", "suggestion": f"Check if log files exist in {FRONTEND_LOG_PATH}"})
        return issues
        
    try:
        with open(latest_frontend_log, "r", encoding="utf-8") as log_file:
            try:
                logs = json.load(log_file)
                for entry in logs:
                    # Only focus on errors and warnings
                    if entry.get("level", "").lower() in ["error", "warning"]:
                        issue = {"log": entry.get("message", "No message")}
                        # Add specific frontend error detection logic here
                        if "addEventListener" in entry.get("message", ""):
                            issue["error"] = "JavaScript EventListener Error"
                            issue["suggestion"] = "Ensure that the element exists before adding an event listener."
                        elif "Identifier has already been declared" in entry.get("message", ""):
                            issue["error"] = "Variable Redeclaration"
                            issue["suggestion"] = "Check script.js for duplicate variable declarations and use 'let' or 'const'."
                        elif "Script error." in entry.get("message", ""):
                            issue["error"] = "CORS issue"
                            issue["suggestion"] = "Check the server CORS configuration"
                        else:
                            issue["error"] = "Frontend Issue"
                            issue["suggestion"] = "Review the log entry for potential problems."
                            
                        issues.append(issue)
            except json.JSONDecodeError:
                issues.append({"error": "Invalid JSON in frontend log", "suggestion": f"Check if {latest_frontend_log} contains valid JSON."})
    except Exception as e:
        issues.append({"error": "Error reading frontend log", "suggestion": str(e)})
        
    return issues

def analyze_api_logs():
    latest_api_log = get_latest_file(API_LOG_PATH, "api_*.log")
    issues = []
    
    if not latest_api_log:
        issues.append({"error": "API Log File Not Found", "suggestion": f"Check if log files exist in {API_LOG_PATH}"})
        return issues
        
    try:
        with open(latest_api_log, "r", encoding="utf-8") as log_file:
            for line in log_file:
                if "ERROR" in line or "CRITICAL" in line:
                    issue = {"log": line.strip()}
                    # Add specific API error detection logic here
                    if "404 Not Found" in line:
                        issue["error"] = "API Endpoint Not Found"
                        issue["suggestion"] = "Check that the API endpoint exists and is correctly configured."
                    elif "500 Internal Server Error" in line:
                        issue["error"] = "API Internal Error"
                        issue["suggestion"] = "Check the API handler for exceptions or errors."
                    else:
                        issue["error"] = "API Issue"
                        issue["suggestion"] = "Review the log entry for potential problems."
                        
                    issues.append(issue)
    except Exception as e:
        issues.append({"error": "Error reading API log", "suggestion": str(e)})
        
    return issues

def analyze_error_logs():
    error_logs = list(Path(ERROR_LOG_PATH).glob("*_errors.log"))
    issues = []
    
    if not error_logs:
        issues.append({"error": "No Error Log Files Found", "suggestion": f"Check if error logs exist in {ERROR_LOG_PATH}"})
        return issues
        
    # Analyze only the most recent 3 error logs to avoid overwhelming the report
    for error_log in sorted(error_logs, key=lambda f: f.stat().st_mtime, reverse=True)[:3]:
        try:
            with open(error_log, "r", encoding="utf-8") as log_file:
                for line in log_file:
                    issue = {"log": line.strip(), "file": error_log.name}
                    # Extract component from filename (before _errors.log)
                    component = error_log.stem.split("_")[0]
                    issue["error"] = f"{component.capitalize()} Error"
                    issue["suggestion"] = f"Review the error log for {component}."
                    issues.append(issue)
        except Exception as e:
            issues.append({"error": f"Error reading {error_log.name}", "suggestion": str(e)})
            
    return issues

def generate_report():
    report = {
        "app_errors": analyze_app_logs(),
        "api_errors": analyze_api_logs(),
        "frontend_errors": analyze_frontend_logs(),
        "error_logs": analyze_error_logs()
    }
    return report

def display_report(report):
    print("\n### Debug Report ###\n")
    
    total_issues = sum(len(issues) for issues in report.values())
    print(f"Total issues found: {total_issues}\n")
    
    for category, errors in report.items():
        if errors:
            print(f"\n#### {category.replace('_', ' ').title()} ####\n")
            for i, err in enumerate(errors):
                print(f"  Issue #{i+1}:")
                for key, value in err.items():
                    if key != "log":  # Log entries can be very verbose
                        print(f"    {key.title()}: {value}")
                # Only show the first 100 chars of log to keep the report readable
                if "log" in err:
                    log_excerpt = err["log"][:100] + ("..." if len(err["log"]) > 100 else "")
                    print(f"    Log: {log_excerpt}")
                print()

if __name__ == "__main__":
    debug_report = generate_report()
    display_report(debug_report)
    
    # Generate timestamp for the report file
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    # Update path to use new directory structure
    report_file = Path("logs/reports") / f"debug_report_{timestamp}.json"
    
    # Ensure the reports directory exists
    report_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(debug_report, f, indent=4)
        
    print(f"Debug report generated: {report_file}")