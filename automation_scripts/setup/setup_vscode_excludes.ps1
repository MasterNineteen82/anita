#######################################################
# VS Code Settings Exclusion Script
# This script configures VS Code to exclude specified folders 
# from problem reporting, making diagnostics cleaner
#######################################################

# Configuration
$settingsDir = ".vscode"
$settingsFile = Join-Path $settingsDir "settings.json"

# Define all exclusion patterns
$baseExclusions = @(
    "**/.archive/**"
)

$additionalExclusions = @(
    # Node.js related
    "**/node_modules/**",
    # Python related
    "**/__pycache__/**",
    "**/.pytest_cache/**",
    # Build outputs
    "**/build/**",
    "**/dist/**",
    # Version control
    "**/.git/**",
    # Virtual environments
    "**/.venv/**",
    "**/venv/**",
    "**/.env/**"
)

# Create .vscode directory if needed
if (-not (Test-Path $settingsDir)) {
    New-Item -Path $settingsDir -ItemType Directory -Force | Out-Null
    Write-Host "Created .vscode directory" -ForegroundColor Green
}

# Initialize or load settings
$settingsObject = @{}
if (Test-Path $settingsFile) {
    try {
        $content = Get-Content $settingsFile -Raw -ErrorAction Stop
        if ($content -and $content.Trim()) {
            $settingsObject = $content | ConvertFrom-Json -AsHashtable -ErrorAction Stop
            Write-Host "Loaded existing settings file" -ForegroundColor Green
        } else {
            Write-Host "Settings file exists but is empty" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "Error reading settings file. Creating new settings." -ForegroundColor Yellow
        Write-Host "Error details: $_" -ForegroundColor Red
    }
}

# Create or get the current exclusion patterns
$allPatterns = @()
if ($settingsObject.ContainsKey("problems.excludePatterns")) {
    $currentPatterns = $settingsObject["problems.excludePatterns"]
    
    # Convert to array if it's a string or other type
    if ($currentPatterns -is [string]) {
        $allPatterns = @($currentPatterns)
    } elseif ($currentPatterns -is [array]) {
        $allPatterns = $currentPatterns
    }
}

# Always add base exclusions
foreach ($pattern in $baseExclusions) {
    if ($allPatterns -notcontains $pattern) {
        $allPatterns += $pattern
        Write-Host "Adding base exclusion: $pattern" -ForegroundColor Green
    } else {
        Write-Host "Base exclusion already present: $pattern" -ForegroundColor Cyan
    }
}

# Ask about additional exclusions
Write-Host "`nWould you like to add these additional common exclusions?" -ForegroundColor Yellow
foreach ($pattern in $additionalExclusions) {
    Write-Host "  - $pattern" -ForegroundColor DarkGray
}
$addMore = Read-Host "(y/n)"

if ($addMore.ToLower() -eq "y") {
    foreach ($pattern in $additionalExclusions) {
        if ($allPatterns -notcontains $pattern) {
            $allPatterns += $pattern
            Write-Host "Added exclusion: $pattern" -ForegroundColor Green
        } else {
            Write-Host "Exclusion already present: $pattern" -ForegroundColor Cyan
        }
    }
}

# Set the final patterns in the settings object
$settingsObject["problems.excludePatterns"] = $allPatterns

# Write the updated settings with nice formatting
try {
    $formattedJson = $settingsObject | ConvertTo-Json -Depth 10
    $formattedJson | Set-Content -Path $settingsFile -ErrorAction Stop
    Write-Host "`nSuccessfully saved settings file" -ForegroundColor Green
    
    # Verify the file was written correctly
    $verifyContent = Get-Content -Path $settingsFile -Raw -ErrorAction Stop
    $verifySettings = $verifyContent | ConvertFrom-Json -AsHashtable -ErrorAction Stop
    
    if ($verifySettings.ContainsKey("problems.excludePatterns") -and 
        $verifySettings["problems.excludePatterns"].Count -eq $allPatterns.Count) {
        Write-Host "Verification successful: All patterns were properly saved" -ForegroundColor Green
    } else {
        Write-Host "Warning: Some patterns may not have been saved correctly" -ForegroundColor Yellow
        Write-Host "Expected: $($allPatterns.Count) patterns, Found: $($verifySettings["problems.excludePatterns"].Count) patterns" -ForegroundColor Yellow
    }
} catch {
    Write-Host "Error saving or verifying settings file" -ForegroundColor Red
    Write-Host "Error details: $_" -ForegroundColor Red
    
    # Emergency fallback - write directly with string manipulation
    try {
        Write-Host "Attempting direct file write..." -ForegroundColor Yellow
        $directJson = @"
{
    "problems.excludePatterns": [
        "$($allPatterns -join '",
        "')"
    ]
}
"@
        $directJson | Set-Content -Path $settingsFile -ErrorAction Stop
        Write-Host "Direct file write successful" -ForegroundColor Green
    } catch {
        Write-Host "All attempts to write settings failed" -ForegroundColor Red
    }
}

# Display final summary
Write-Host "`n=== VS Code Settings Updated ===`n" -ForegroundColor Cyan
Write-Host "VS Code will now ignore problems in these folders:" -ForegroundColor White
foreach ($pattern in $allPatterns) {
    Write-Host "  - $pattern" -ForegroundColor Green
}

Write-Host "`nTo apply these changes:" -ForegroundColor Yellow
Write-Host "  1. Close and reopen VS Code" -ForegroundColor Yellow
Write-Host "  2. Or use the 'Developer: Reload Window' command" -ForegroundColor Yellow
Write-Host "`nYour Problems panel should now be much cleaner!" -ForegroundColor Green