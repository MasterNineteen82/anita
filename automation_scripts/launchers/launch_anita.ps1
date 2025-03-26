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
    
    switch ($Level) {
        "INFO" { Write-Host $logMessage -ForegroundColor Cyan }
        "WARNING" { Write-Host $logMessage -ForegroundColor Yellow }
        "ERROR" { Write-Host $logMessage -ForegroundColor Red }
        default { Write-Host $logMessage }
    }
    
    $logMessage | Out-File -FilePath $LaunchLog -Append
}

function Test-Command {
    param (
        [string]$Executable,
        [string]$Arguments
    )
    
    try {
        # Use Start-Process to avoid alias interference
        $output = Start-Process -FilePath $Executable -ArgumentList $Arguments -NoNewWindow -Wait -PassThru -RedirectStandardOutput "NUL"
        return $output.ExitCode -eq 0
    } catch {
        Write-Log "Command '$Executable $Arguments' failed: $($_.Exception.Message)" -Level "ERROR"
        return $false
    }
}

# Check if Python executable path is provided
if (-not $PythonExecutable) {
    Write-Log "Python executable path not provided. Ensure virtual environment is activated." -Level "ERROR"
    exit 1
}

Write-Log "Using Python executable: $PythonExecutable" -Level "INFO"

# Check if Python is available
if (-not (Test-Command "$PythonExecutable" "--version")) {
    Write-Log "Python not found. Please ensure the provided path is correct." -Level "ERROR"
    exit 1
}

# Check dependencies
Write-Log "Checking dependencies..."
try {
    & $PythonExecutable -c "import fastapi, uvicorn, alembic, pydantic" 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Dependency check failed" }
} catch {
    Write-Log "Missing dependencies or Python error. Running dependency installation..." -Level "WARNING"
    try {
        & $PythonExecutable -m pip install -r "$ProjectRoot\requirements.txt" 2>&1 | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "Pip install failed" }
        Write-Log "Dependencies installed successfully." -Level "INFO"
    } catch {
        Write-Log "Failed to install dependencies: $($_.Exception.Message)" -Level "ERROR"
        exit 1
    }
}

# Start the application with uvicorn
Write-Log "Starting ANITA application..."
try {
    Write-Log "Launching main application server with Uvicorn..."
    if (-not (Test-Path "$ProjectRoot\app.py")) {
        throw "Main application script (app.py) not found."
    }
    # Use array for arguments to avoid PowerShell misinterpretation
    $uvicornArgs = @(
        "-m", "uvicorn",
        "app:app",
        "--host", "0.0.0.0",
        "--port", "8000",
        "--reload",
        "--app-dir", $ProjectRoot
    )
    Start-Process -FilePath $PythonExecutable -ArgumentList $uvicornArgs -NoNewWindow -Wait
} catch {
    Write-Log "Failed to start application: $($_.Exception.Message)" -Level "ERROR"
    exit 1
}