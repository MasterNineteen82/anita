#######################################################
# ANITA Application Launcher
# This script handles the proper startup of all ANITA components
#######################################################

param (
    [Parameter(Mandatory=$false)]
    [string]$Component = "all",
    
    [Parameter(Mandatory=$false)]
    [string]$PythonExecutable
)

# Configuration
$ProjectRoot = "K:\anita\poc"
$LogDir = Join-Path $ProjectRoot "logs\active"
$LaunchLog = Join-Path $LogDir "app_launch_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"

# Ensure log directory exists
if (-not (Test-Path $LogDir)) {
    New-Item -Path $LogDir -ItemType Directory -Force | Out-Null
}

function Write-Log {
    param (
        [string]$Message,
        [string]$Level = "INFO"
    )
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "[$Level] $timestamp - $Message"
    
    # Write to console with color
    switch ($Level) {
        "INFO" { Write-Host $logMessage -ForegroundColor Cyan }
        "WARNING" { Write-Host $logMessage -ForegroundColor Yellow }
        "ERROR" { Write-Host $logMessage -ForegroundColor Red }
        default { Write-Host $logMessage }
    }
    
    # Write to log file
    $logMessage | Out-File -FilePath $LaunchLog -Append
}

function Test-Command {
    param (
        [string]$Executable,
        [string]$Arguments
    )
    
    try {
        # Execute the command with the executable and arguments
        & $Executable $Arguments -ErrorAction Stop | Out-Null
        # If the command executes without error, return true
        return $true
    } catch {
        # If the command fails, return false
        Write-Log "Command '$Executable $Arguments' failed: $($_.Exception.Message)" -Level "ERROR"
        return $false
    }
}

# Check if Python executable path is provided
if (-not $PythonExecutable) {
    Write-Log "Python executable path not provided. Ensure virtual environment is activated." -Level "ERROR"
    exit 1
}

# Now use $PythonExecutable instead of "python"
Write-Log "Using Python executable: $PythonExecutable" -Level "INFO"

# Check if Python is available
if (-not (Test-Command "$PythonExecutable" "--version")) {
    Write-Log "Python not found. Please ensure the provided path is correct." -Level "ERROR"
    exit 1
}

# Check dependencies
Write-Log "Checking dependencies..."
try {
    & $PythonExecutable -c "import fastapi, uvicorn, alembic, pydantic" -ErrorAction Stop
} catch {
    Write-Log "Missing dependencies or Python error. Running dependency installation..." -Level "WARNING"
    try {
        & $PythonExecutable -m pip install -r "$ProjectRoot\requirements.txt" -ErrorAction Stop
    } catch {
        Write-Log "Failed to install dependencies: $($_.Exception.Message)" -Level "ERROR"
        exit 1
    }
}

# Start the application
Write-Log "Starting ANITA application..."
try {
    # Launch main application
    Write-Log "Launching main application server..."
    if (-not (Test-Path "$ProjectRoot\app.py")) {
        throw "Main application script not found."
    }
    & $PythonExecutable "$ProjectRoot\app.py" -ErrorAction Stop
} catch {
    Write-Log "Failed to start application: $($_.Exception.Message)" -Level "ERROR"
    exit 1
}