# Logging Reorganization and Archiving Script
# This script reorganizes the logging structure and archives redundant files

# Enable error display
$ErrorActionPreference = "Stop"

# Define paths
$ProjectRoot = "K:\anita\poc"
$LogsRoot = Join-Path $ProjectRoot "logs"
$BackendLoggingDir = Join-Path $ProjectRoot "backend\logging"
$OldLoggingDir = Join-Path $ProjectRoot "logging"
$ArchiveDir = Join-Path $LogsRoot "archive"
$ActiveLogsDir = Join-Path $LogsRoot "active"
$RedundantFilesDir = Join-Path $ArchiveDir "redundant_files"
$ScriptsDir = Join-Path $BackendLoggingDir "logging_scripts"

# Timestamp for archiving
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"

# Create function to log messages with color support
function Write-LogMessage {
    param (
        [Parameter(Mandatory=$true)]
        [string]$Message,
        
        [Parameter(Mandatory=$false)]
        [ValidateSet("INFO", "WARNING", "ERROR")]
        [string]$Level = "INFO"
    )
    
    $TimeStamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $Icon = switch ($Level) {
        "INFO" { "[i]" }
        "WARNING" { "[!]" }
        "ERROR" { "[X]" }
    }
    
    $FormattedMessage = "$TimeStamp $Icon $Message"
    
    # Use color based on level
    switch ($Level) {
        "INFO" { Write-Host $FormattedMessage -ForegroundColor Cyan }
        "WARNING" { Write-Host $FormattedMessage -ForegroundColor Yellow }
        "ERROR" { Write-Host $FormattedMessage -ForegroundColor Red }
        default { Write-Host $FormattedMessage -ForegroundColor Cyan }
    }
}
# Function to test if a directory exists and create it if specified
function Test-DirectoryExists {
    param (
        [Parameter(Mandatory=$true)]
        [string]$Path,
        
        [Parameter(Mandatory=$false)]
        [switch]$CreateIfMissing
    )
    
    if (-not (Test-Path $Path)) {
        if ($CreateIfMissing) {
            Write-LogMessage "Creating directory: $Path"
            New-Item -Path $Path -ItemType Directory -Force | Out-Null
            return $true
        } else {
            Write-LogMessage "Directory does not exist: $Path" -Level "WARNING"
            return $false
        }
    }
    return $true
}

# Function to archive a file
function Move-FileToArchive {
    param (
        [Parameter(Mandatory=$true)]
        [string]$SourcePath,
        
        [Parameter(Mandatory=$true)]
        [string]$DestinationDir,
        
        [Parameter(Mandatory=$false)]
        [switch]$DeleteOriginal = $false
    )
    
    if (Test-Path $SourcePath) {
        $FileName = Split-Path $SourcePath -Leaf
        $DestPath = Join-Path $DestinationDir "$FileName.archived_$Timestamp"
        
        # Make sure destination directory exists
        Test-DirectoryExists -Path $DestinationDir
        
        # Copy or move file
        if ($DeleteOriginal) {
            Write-LogMessage "Moving file: $SourcePath -> $DestPath"
            Move-Item -Path $SourcePath -Destination $DestPath -Force
        } else {
            Write-LogMessage "Copying file: $SourcePath -> $DestPath"
            Copy-Item -Path $SourcePath -Destination $DestPath -Force
        }
        return $true
    } else {
        Write-LogMessage "Source file does not exist: $SourcePath" -Level "WARNING"
        return $false
    }
}

# Start reorganization process
Write-LogMessage "Starting logging system reorganization..."

# Step 1: Ensure all required directories exist
Write-LogMessage "Setting up directory structure..."
Test-DirectoryExists -Path $LogsRoot
Test-DirectoryExists -Path $BackendLoggingDir
Test-DirectoryExists -Path $ArchiveDir
Test-DirectoryExists -Path $ActiveLogsDir
Test-DirectoryExists -Path $RedundantFilesDir
Test-DirectoryExists -Path $ScriptsDir

# Step 2: Move current log files to active directory - improved with error handling
Write-LogMessage "Moving current log files to active directory..."
$LogFiles = Get-ChildItem -Path $LogsRoot -Filter "*.log" -File
foreach ($LogFile in $LogFiles) {
    $DestPath = Join-Path $ActiveLogsDir $LogFile.Name
    try {
        # Try to move the file
        Move-Item -Path $LogFile.FullName -Destination $DestPath -Force -ErrorAction Stop
        Write-LogMessage "Moved: $($LogFile.Name) -> active/"
    } catch {
        # If the file is in use, try to copy it instead
        if ($_.Exception.Message -like "*because it is being used by another process*") {
            Write-LogMessage "File in use: $($LogFile.Name). Attempting to copy instead..." -Level "WARNING"
            try {
                # Copy the file instead of moving it
                Copy-Item -Path $LogFile.FullName -Destination $DestPath -Force -ErrorAction Stop
                Write-LogMessage "Copied: $($LogFile.Name) -> active/ (original remains in place)"
                
                # Add to a list of files to clean up later
                $InUseFiles += $LogFile.FullName
            } catch {
                Write-LogMessage "Could not copy file: $($LogFile.Name). $($_.Exception.Message)" -Level "ERROR"
            }
        } else {
            Write-LogMessage "Error moving file: $($LogFile.Name). $($_.Exception.Message)" -Level "ERROR"
        }
    }
}

# Step 3: Handle redundant logging directory
if (Test-Path $OldLoggingDir) {
    Write-LogMessage "Processing redundant logging directory..."
    
    # Handle duplicate logging_config.py
    $OldConfigPath = Join-Path $OldLoggingDir "logging_config.py"
    if (Test-Path $OldConfigPath) {
        Move-FileToArchive -SourcePath $OldConfigPath -DestinationDir $RedundantFilesDir -DeleteOriginal
    }
    
    # Handle duplicate logging_scripts directory
    $OldScriptsDir = Join-Path $OldLoggingDir "logging_scripts"
    if (Test-Path $OldScriptsDir) {
        $OldScriptFiles = Get-ChildItem -Path $OldScriptsDir -File
        foreach ($ScriptFile in $OldScriptFiles) {
            Move-FileToArchive -SourcePath $ScriptFile.FullName -DestinationDir $RedundantFilesDir -DeleteOriginal
        }
        
        # Remove empty directory
        if ((Get-ChildItem -Path $OldScriptsDir -Recurse | Measure-Object).Count -eq 0) {
            Remove-Item -Path $OldScriptsDir -Force -Recurse
            Write-LogMessage "Removed empty directory: $OldScriptsDir"
        }
    }
    
    # Consider removing the entire old logging directory if empty
    if ((Get-ChildItem -Path $OldLoggingDir -Recurse | Measure-Object).Count -eq 0) {
        Remove-Item -Path $OldLoggingDir -Force -Recurse
        Write-LogMessage "Removed empty directory: $OldLoggingDir"
    }
}

# Step 4: Set up monthly archive structure
$CurrentMonth = Get-Date -Format "yyyy-MM"
$CurrentMonthDir = Join-Path $ArchiveDir $CurrentMonth
Test-DirectoryExists -Path $CurrentMonthDir

# Step 5: Find and organize old log files
Write-LogMessage "Organizing old log files..."
$ThirtyDaysAgo = (Get-Date).AddDays(-30)

# Process app_*.log files
$OldLogs = Get-ChildItem -Path $ActiveLogsDir -Filter "app_*.log" | Where-Object {
    try {
        $DatePart = $_.Name.Split("_")[1]
        $FileDate = [DateTime]::ParseExact($DatePart.Substring(0, 8), "yyyyMMdd", $null)
        return $FileDate -lt $ThirtyDaysAgo
    } catch {
        Write-LogMessage "Could not parse date from filename: $($_.Name)" -Level "WARNING"
        return $false
    }
}

foreach ($OldLog in $OldLogs) {
    try {
        $DatePart = $OldLog.Name.Split("_")[1]
        $FileDate = [DateTime]::ParseExact($DatePart.Substring(0, 8), "yyyyMMdd", $null)
        $MonthDir = Join-Path $ArchiveDir ($FileDate.ToString("yyyy-MM"))
        Test-DirectoryExists -Path $MonthDir
        
        $DestPath = Join-Path $MonthDir $OldLog.Name
        Move-Item -Path $OldLog.FullName -Destination $DestPath -Force
        Write-LogMessage "Archived: $($OldLog.Name) -> $($FileDate.ToString('yyyy-MM'))/"
    } catch {
        Write-LogMessage "Error processing file $($OldLog.Name): $_" -Level "ERROR"
    }
}

# Step 6: Set up log maintenance script if needed
$MaintenanceScriptPath = Join-Path $ScriptsDir "log_maintenance.py"
if (-not (Test-Path $MaintenanceScriptPath)) {
    Write-LogMessage "Log maintenance script not found. Creating..." -Level "WARNING"
    
    # Copy from your existing script or create a new one
    # (This step is not needed if you've already created log_maintenance.py)
}

# Step 7: Create a scheduled task to run maintenance script (optional - uncomment to enable)
<#
$TaskName = "ANITA_LogMaintenance"
$TaskExists = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue

if (-not $TaskExists) {
    Write-LogMessage "Creating scheduled task for log maintenance..."
    
    $Action = New-ScheduledTaskAction -Execute "python" -Argument "$MaintenanceScriptPath"
    $Trigger = New-ScheduledTaskTrigger -Daily -At "00:00"
    $Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopOnIdleEnd
    
    Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -RunLevel Highest -User "SYSTEM"
    Write-LogMessage "Scheduled task created: $TaskName"
} else {
    Write-LogMessage "Scheduled task already exists: $TaskName"
}
#>

# Step 8: Update any references if needed
# This would require modifying your application code - showing example search only
Write-LogMessage "Searching for references to old logging modules..."

# Define directories to exclude
$ExcludeDirs = @(
    "venv",
    "env",
    ".venv",
    ".env",
    "node_modules",
    "dist",
    "build",
    "ext",
    "archive",
    "archives",
    "__pycache__",
    ".git"
)

# Create a filtering function
function Should-ProcessFile {
    param (
        [Parameter(Mandatory=$true)]
        [string]$FilePath
    )
    
    # Check if the file path contains any of the excluded directories
    foreach ($dir in $ExcludeDirs) {
        if ($FilePath -like "*\$dir\*") {
            return $false
        }
    }
    return $true
}

# Find all Python files that don't reside in excluded directories
$PythonFiles = Get-ChildItem -Path $ProjectRoot -Recurse -File -Include "*.py" | 
    Where-Object { Should-ProcessFile $_.FullName }

# Count total files searched
$TotalFiles = $PythonFiles.Count
Write-LogMessage "Found $TotalFiles Python files to check (excluding system directories)"

# Search for different logging import patterns
$ImportPatterns = @(
    "from logging\.logging_config",
    "from logging\.",
    "import logging"
)

$AllReferencesToUpdate = @()

foreach ($pattern in $ImportPatterns) {
    $Matches = $PythonFiles | Select-String -Pattern $pattern -SimpleMatch
    if ($Matches) {
        $AllReferencesToUpdate += $Matches
    }
}

# Group by file path to show consolidated results
$GroupedReferences = $AllReferencesToUpdate | Group-Object -Property Path

if ($GroupedReferences.Count -gt 0) {
    Write-LogMessage "Found references to old logging modules in $($GroupedReferences.Count) files:" -Level "WARNING"
    foreach ($FileGroup in $GroupedReferences) {
        Write-LogMessage "  File: $($FileGroup.Name)" -Level "WARNING"
        foreach ($Match in $FileGroup.Group) {
            Write-LogMessage "    Line $($Match.LineNumber): $($Match.Line.Trim())" -Level "WARNING"
        }
    }
    
    # Optionally create a report file
    $ReportPath = Join-Path $LogsRoot "logging_imports_report.txt"
    "Files with logging imports that need to be updated:`n" | Set-Content -Path $ReportPath
    foreach ($FileGroup in $GroupedReferences) {
        "File: $($FileGroup.Name)" | Add-Content -Path $ReportPath
        foreach ($Match in $FileGroup.Group) {
            "  Line $($Match.LineNumber): $($Match.Line.Trim())" | Add-Content -Path $ReportPath
        }
        "`n" | Add-Content -Path $ReportPath
    }
    Write-LogMessage "Detailed report saved to: $ReportPath" -Level "INFO"
    
    # Ask if user wants to create an update script
    Write-Host ""
    $CreateScript = Read-Host "Do you want to create an update script to help fix these imports? (y/n)"
    if ($CreateScript -eq 'y') {
        $UpdateScriptPath = Join-Path $ProjectRoot "automation_scripts\update_logging_imports.ps1"
        @"
# Logging Import Update Script
# Generated on $(Get-Date)

`$FilesToUpdate = @(
$(($GroupedReferences | ForEach-Object { "    '$($_.Name)'" }) -join ",`n")
)

foreach (`$file in `$FilesToUpdate) {
    Write-Host "Processing `$file..." -ForegroundColor Cyan
    `$content = Get-Content -Path `$file
    `$updated = `$content -replace 'from logging\.', 'from backend.logging.'
    
    # Show preview of changes
    for (`$i = 0; `$i -lt `$content.Count; `$i++) {
        if (`$content[`$i] -ne `$updated[`$i]) {
            Write-Host "  Line `$(`$i+1):" -ForegroundColor Yellow
            Write-Host "    Old: `$(`$content[`$i])" -ForegroundColor Red
            Write-Host "    New: `$(`$updated[`$i])" -ForegroundColor Green
        }
    }
    
    `$confirm = Read-Host "Apply changes? (y/n)"
    if (`$confirm -eq 'y') {
        `$updated | Set-Content -Path `$file
        Write-Host "Updated `$file" -ForegroundColor Green
    }
}

Write-Host "Import update complete!" -ForegroundColor Green
"@ | Set-Content -Path $UpdateScriptPath
        Write-LogMessage "Update script created at: $UpdateScriptPath" -Level "INFO"
        Write-LogMessage "Run this script to interactively update the imports" -Level "INFO"
    }
} else {
    Write-LogMessage "No references to old logging modules found. No updates needed." -Level "INFO"
}

Write-LogMessage "Logging system reorganization completed!" -Level "INFO"
Write-Host "Logging system reorganization completed!" -ForegroundColor Green
Write-LogMessage "New structure:"
Write-LogMessage "  - $LogsRoot/active/           # Current logs"
Write-LogMessage "  - $LogsRoot/archive/          # Archived logs by month"
Write-LogMessage "  - $BackendLoggingDir/         # Main logging configuration"
Write-LogMessage "  - $ScriptsDir/  # Log maintenance scripts"

# Final instructions
Write-LogMessage "---------------------------------------------------------"
Write-LogMessage "To complete setup:"
Write-LogMessage "1. Update any imports in your code to use 'backend.logging' instead of 'logging'"
Write-LogMessage "2. Uncomment the scheduled task section in this script if you want to automate log maintenance"
Write-LogMessage "3. Run the log maintenance script to verify it works: python $MaintenanceScriptPath"
Write-LogMessage "---------------------------------------------------------"

# Add at the end of your script
if ($RestartApp) {
    Write-LogMessage "Restarting application..."
    # Start your application
    Start-Process -FilePath "python" -ArgumentList "-m uvicorn app:app --host 0.0.0.0 --port 8000"
}