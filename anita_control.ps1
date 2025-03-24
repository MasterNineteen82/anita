<#
.SYNOPSIS
    ANITA Project Control Script - Manages all automation tasks
.DESCRIPTION
    This script provides a centralized way to manage all ANITA automation tasks,
    including starting/stopping components, updating code, deployment, setup, and diagnostics.
.PARAMETER Command
    The command to execute (start, stop, update, deploy, setup, diagnostics, help)
.PARAMETER Component
    The specific component to target (all, server, smartcard, frontend)
.EXAMPLE
    .\anita_control.ps1 start
    Starts all ANITA components
.EXAMPLE
    .\anita_control.ps1 stop server
    Stops only the server component
.NOTES
    Author: ANITA Team
    Version: 1.1
#>

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet('start', 'stop', 'update', 'deploy', 'setup', 'diagnostics', 'help')]
    [string]$Command,
    
    [Parameter(Mandatory=$false)]
    [ValidateSet('all', 'server', 'smartcard', 'frontend')]
    [string]$Component = "all"
)

# Configuration
$ProjectRoot = "K:\anita\poc"
$ScriptsRoot = Join-Path $ProjectRoot "automation_scripts"
$LogsDir = Join-Path $ProjectRoot "logs\active"

# Ensure logs directory exists
if (-not (Test-Path $LogsDir)) {
    New-Item -Path $LogsDir -ItemType Directory -Force | Out-Null
}

# Log file for this script
$LogFile = Join-Path $LogsDir "anita_control_$(Get-Date -Format 'yyyyMMdd').log"

# Helper Functions
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
        "SUCCESS" { Write-Host $logMessage -ForegroundColor Green }
        default { Write-Host $logMessage -ForegroundColor White }
    }
    
    # Write to log file
    Add-Content -Path $LogFile -Value $logMessage
}

function Test-ScriptExists {
    param (
        [string]$ScriptPath
    )
    
    if (-not (Test-Path $ScriptPath)) {
        Write-Log "Script not found: $ScriptPath" -Level "ERROR"
        return $false
    }
    return $true
}

function Stop-AnitaProcess {
    param (
        [string]$ProcessType
    )

    $stoppedCount = 0
    
    switch ($ProcessType) {
        "server" {
            Write-Log "Stopping server processes..." -Level "INFO"
            Get-Process -Name "python*" | Where-Object { 
                $_.CommandLine -like "*app.py*" -or $_.CommandLine -like "*uvicorn*" 
            } | ForEach-Object {
                Write-Log "Stopping server process: $($_.Id)" -Level "INFO"
                Stop-Process -Id $_.Id -Force
                $stoppedCount++
            }
        }
        
        "smartcard" {
            Write-Log "Stopping smartcard processes..." -Level "INFO"
            Get-Process -Name "python*" | Where-Object { 
                $_.CommandLine -like "*smartcard*" -or $_.CommandLine -like "*card_manager*" 
            } | ForEach-Object {
                Write-Log "Stopping smartcard process: $($_.Id)" -Level "INFO"
                Stop-Process -Id $_.Id -Force
                $stoppedCount++
            }
        }
        
        "frontend" {
            Write-Log "Stopping frontend processes..." -Level "INFO"
            Get-Process -Name "node*", "npm*" | Where-Object { 
                $_.Path -like "*$ProjectRoot*" 
            } | ForEach-Object {
                Write-Log "Stopping frontend process: $($_.Id)" -Level "INFO"
                Stop-Process -Id $_.Id -Force
                $stoppedCount++
            }
        }
        
        "all" {
            # Stop all components
            Stop-AnitaProcess -ProcessType "server"
            Stop-AnitaProcess -ProcessType "smartcard"
            Stop-AnitaProcess -ProcessType "frontend"
            return
        }
    }
    
    if ($stoppedCount -eq 0) {
        Write-Log "No $ProcessType processes found to stop" -Level "WARNING"
    } else {
        Write-Log "Stopped $stoppedCount $ProcessType process(es)" -Level "SUCCESS"
    }
}

# Display help information
function Show-Help {
    Clear-Host
    Write-Host "+--------------------------------------+" -ForegroundColor Cyan
    Write-Host "|            ANITA Control Script      |" -ForegroundColor Cyan
    Write-Host "+--------------------------------------+" -ForegroundColor Cyan
    Write-Host "`nUsage: .\anita_control.ps1 [command] [component]`n" -ForegroundColor White
    
    Write-Host "Commands:" -ForegroundColor White
    Write-Host "  start       - Start ANITA components" -ForegroundColor Green
    Write-Host "  stop        - Stop running components" -ForegroundColor Red
    Write-Host "  update      - Update code from repository" -ForegroundColor Blue
    Write-Host "  deploy      - Deploy to target environment" -ForegroundColor Magenta
    Write-Host "  setup       - Configure development environment" -ForegroundColor Yellow
    Write-Host "  diagnostics - Run diagnostic tools" -ForegroundColor Gray
    Write-Host "  help        - Show this help message" -ForegroundColor Cyan
    
    Write-Host "`nComponents (for start/stop):" -ForegroundColor White
    Write-Host "  all         - All components (default)" -ForegroundColor White
    Write-Host "  server      - Backend server only" -ForegroundColor White
    Write-Host "  smartcard   - Smartcard service only" -ForegroundColor White
    Write-Host "  frontend    - Frontend server only" -ForegroundColor White
    
    Write-Host "`nExamples:" -ForegroundColor White
    Write-Host "  .\anita_control.ps1 start" -ForegroundColor White
    Write-Host "  .\anita_control.ps1 stop server" -ForegroundColor White
    Write-Host "  .\anita_control.ps1 update" -ForegroundColor White
}

function Initialize-PythonEnvironment {
    Write-Log "Initializing Python environment..." -Level "INFO"
    
    # Check if Python is available in the system path
    try {
        $pythonVersion = python --version
        Write-Log "Found Python: $pythonVersion" -Level "INFO"
    }
    catch {
        Write-Log "Python not found in PATH. Please install Python 3.8 or higher." -Level "ERROR"
        return $false
    }
    
    # Create virtual environment if it doesn't exist
    $venvPath = Join-Path $ProjectRoot "venv"
    if (-not (Test-Path $venvPath)) {
        Write-Log "Creating virtual environment..." -Level "INFO"
        & python -m venv $venvPath
        if ($LASTEXITCODE -ne 0) {
            Write-Log "Failed to create virtual environment. Make sure Python is installed with venv support." -Level "ERROR"
            return $false
        }
    }
    
    # Activate virtual environment
    $activateScript = Join-Path $venvPath "Scripts\Activate.ps1"
    if (Test-Path $activateScript) {
        Write-Log "Activating virtual environment..." -Level "INFO"
        & $activateScript
        # Verify activation worked
        if ($env:VIRTUAL_ENV) {
            Write-Log "Virtual environment activated: $env:VIRTUAL_ENV" -Level "SUCCESS"
            
            # Ensure pip is up to date
            python -m pip install --upgrade pip | Out-Null
            
            # Check for requirements.txt and install if needed
            $requirementsFile = Join-Path $ProjectRoot "requirements.txt"
            if (Test-Path $requirementsFile) {
                Write-Log "Installing/updating required packages..." -Level "INFO"
                python -m pip install -r $requirementsFile | Out-Null
            }
            
            return $true
        } else {
            Write-Log "Failed to activate virtual environment" -Level "ERROR"
            return $false
        }
    } else {
        Write-Log "Virtual environment activation script not found: $activateScript" -Level "ERROR"
        return $false
    }
}

# Process the command
Write-Log "Running command: $Command (component: $Component)" -Level "INFO"

switch ($Command) {
    'start' {
        Write-Log "Starting ANITA components: $Component" -Level "INFO"
        
        $launchScript = Join-Path $ScriptsRoot "launchers\launch_anita.ps1"
        if (Test-ScriptExists $launchScript) {
            if (Initialize-PythonEnvironment) {
                # Pass the virtual environment info to the launch script
                & $launchScript -Component $Component -VenvPath (Join-Path $ProjectRoot "venv")
                if ($LASTEXITCODE -ne 0) {
                    Write-Log "Launch script failed with exit code $LASTEXITCODE" -Level "ERROR"
                } else {
                    Write-Log "Components started successfully" -Level "SUCCESS"
                }
            } else {
                Write-Log "Failed to initialize Python environment" -Level "ERROR"
            }
        }
    }
    
    'stop' {
        Write-Log "Stopping ANITA components: $Component" -Level "INFO"
        Stop-AnitaProcess -ProcessType $Component
    }
    
    'update' {
        Write-Log "Updating ANITA code from repository" -Level "INFO"
        $repoManagerScript = Join-Path $ScriptsRoot "git\repo_manager.py"
        
        if (Test-ScriptExists $repoManagerScript) {
            if (Initialize-PythonEnvironment) {
                python $repoManagerScript
                if ($LASTEXITCODE -ne 0) {
                    Write-Log "Repository update failed with exit code $LASTEXITCODE" -Level "ERROR"
                } else {
                    Write-Log "Repository update completed successfully" -Level "SUCCESS"
                }
            } else {
                Write-Log "Failed to initialize Python environment" -Level "ERROR"
            }
        }
    }
    
    'deploy' {
        Write-Log "Deploying ANITA to target environment" -Level "INFO"
        $deployScript = Join-Path $ScriptsRoot "deployment\deploy.py"
        
        if (Test-ScriptExists $deployScript) {
            if (Initialize-PythonEnvironment) {
                python $deployScript
                if ($LASTEXITCODE -ne 0) {
                    Write-Log "Deployment failed with exit code $LASTEXITCODE" -Level "ERROR"
                } else {
                    Write-Log "Deployment completed successfully" -Level "SUCCESS"
                }
            } else {
                Write-Log "Failed to initialize Python environment" -Level "ERROR"
            }
        }
    }
    
    'setup' {
        Write-Log "Setting up ANITA development environment" -Level "INFO"
        $setupScript = Join-Path $ScriptsRoot "setup\setup.py"
        
        if (Test-ScriptExists $setupScript) {
            if (Initialize-PythonEnvironment) {
                python $setupScript
                if ($LASTEXITCODE -ne 0) {
                    Write-Log "Setup failed with exit code $LASTEXITCODE" -Level "ERROR"
                } else {
                    Write-Log "Setup completed successfully" -Level "SUCCESS"
                }
            } else {
                Write-Log "Failed to initialize Python environment" -Level "ERROR"
            }
        }
    }
    
    'diagnostics' {
        Write-Log "Running ANITA diagnostics" -Level "INFO"
        $scanScript = Join-Path $ScriptsRoot "diagnostics\scan.py"
        
        if (Test-ScriptExists $scanScript) {
            if (Initialize-PythonEnvironment) {
                python $scanScript
                if ($LASTEXITCODE -ne 0) {
                    Write-Log "Diagnostics failed with exit code $LASTEXITCODE" -Level "ERROR"
                } else {
                    Write-Log "Diagnostics completed successfully" -Level "SUCCESS"
                }
            } else {
                Write-Log "Failed to initialize Python environment" -Level "ERROR"
            }
        }
    }
    
    'help' {
        Show-Help
    }
    
    default {
        Write-Log "Unknown command: $Command" -Level "ERROR"
        Show-Help
    }
}

# End of script message
if ($Command -ne "help") {
    Write-Host "`nCommand '$Command' completed. See log at: $LogFile" -ForegroundColor Cyan
}