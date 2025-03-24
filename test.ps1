# Final verification script for automation scripts structure

$ProjectRoot = "K:\anita\poc"
$ScriptsRoot = Join-Path $ProjectRoot "automation_scripts"

# Test each critical script
$criticalScripts = @(
    "git\repo_manager.py",
    "setup\setup.py",
    "deployment\deploy.py",
    "diagnostics\scan.py",
    "launchers\launch_anita.ps1"
)

foreach ($script in $criticalScripts) {
    $scriptPath = Join-Path $ScriptsRoot $script
    if (Test-Path $scriptPath) {
        Write-Host "✅ $script exists" -ForegroundColor Green
    } else {
        Write-Host "❌ $script is missing!" -ForegroundColor Red
    }
}

# Test the master control script
$controlScript = Join-Path $ProjectRoot "anita_control.ps1"
if (Test-Path $controlScript) {
    Write-Host "✅ anita_control.ps1 exists" -ForegroundColor Green
} else {
    Write-Host "❌ anita_control.ps1 is missing!" -ForegroundColor Red
}

# Test help command
Write-Host "`nTesting help command..."
& $controlScript help